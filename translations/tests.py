"""Tests for the translation cache.

/api/translations/ is the only caller of the aggregate rebuild, and it is the
endpoint that went down when the cache moved to Redis. The rebuild reads the
translated table directly instead of touching parler's descriptors, and caches one
entry per language rather than a single ~15MB blob, so both properties are pinned
here.
"""

from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase, override_settings
from parler import appsettings as parler_appsettings
from rest_framework.permissions import AllowAny
from rest_framework.test import APIRequestFactory

from benefits.tests.cache_override import LOCAL_CACHE
from translations import models as translation_models
from translations.models import (
    _TRANSLATION_CACHE_TIMEOUT,
    Translation,
    _all_langs,
    _build_translation_data,
    _get_translation_data,
    _invalidate_translation_cache,
    _translation_cache_key,
    _translation_cache_timeout,
)
from translations.views import TranslationView
from authentication.models import User
from integrations.clients.google_translate import TranslationIntegrityError

DEFAULT_LANG = settings.LANGUAGE_CODE


@override_settings(CACHES=LOCAL_CACHE)
class TestTranslationCache(TestCase):
    def setUp(self):
        cache.clear()

    def _make(self, label, texts, active=True):
        """Create a Translation with `texts` as {lang_code: text}."""
        parent = Translation.objects.create(label=label, active=active)
        for lang, text in texts.items():
            parent.create_translation(lang, text=text, edited=True)
        _invalidate_translation_cache()
        return parent

    def test_returns_text_for_each_requested_language(self):
        self._make("greeting", {DEFAULT_LANG: "Hello", "es": "Hola"})

        data = _get_translation_data([DEFAULT_LANG, "es"])

        self.assertEqual(data[DEFAULT_LANG]["greeting"], "Hello")
        self.assertEqual(data["es"]["greeting"], "Hola")

    def test_returns_only_requested_languages(self):
        self._make("greeting", {DEFAULT_LANG: "Hello", "es": "Hola"})

        self.assertEqual(list(_get_translation_data(["es"])), ["es"])

    def test_falls_back_to_default_language_when_row_missing(self):
        """Matches parler's use_fallback=True behaviour."""
        self._make("only_english", {DEFAULT_LANG: "Hello"})

        self.assertEqual(_get_translation_data(["es"])["es"]["only_english"], "Hello")

    def test_inactive_labels_are_excluded(self):
        self._make("retired", {DEFAULT_LANG: "Old"}, active=False)

        self.assertNotIn("retired", _get_translation_data([DEFAULT_LANG])[DEFAULT_LANG])

    def test_label_with_no_translation_rows_is_present_but_empty(self):
        Translation.objects.create(label="bare", active=True)
        _invalidate_translation_cache()

        data = _get_translation_data([DEFAULT_LANG])

        self.assertIn("bare", data[DEFAULT_LANG])
        self.assertIsNone(data[DEFAULT_LANG]["bare"])

    def test_caches_one_key_per_language_not_one_blob(self):
        """A single combined key is ~15MB against a 25MB Redis; per-language is ~0.4MB."""
        self._make("greeting", {DEFAULT_LANG: "Hello", "es": "Hola"})

        _get_translation_data([DEFAULT_LANG])

        # Requesting one language still warms them all -- the query fetches every
        # language anyway -- but each lands under its own key.
        self.assertIsNotNone(cache.get(_translation_cache_key(DEFAULT_LANG)))
        self.assertIsNotNone(cache.get(_translation_cache_key("es")))
        self.assertIsNone(cache.get("translation_data"))

    def test_language_ttls_are_staggered(self):
        """Identical TTLs would make every language lapse at once, once a day.

        All 18 keys are written by the same rebuild, so a shared timeout guarantees a
        daily window where they are all cold and concurrent requests all rebuild.
        """
        timeouts = {lang: _translation_cache_timeout(lang) for lang in _all_langs()}

        self.assertGreater(len(set(timeouts.values())), 1, f"TTLs not staggered: {timeouts}")
        self.assertTrue(all(t >= _TRANSLATION_CACHE_TIMEOUT for t in timeouts.values()))

    def test_language_ttl_is_stable_across_processes(self):
        """Must not use builtin hash(), which is salted per process.

        Dynos would otherwise disagree about when a language expires.
        """
        self.assertEqual(_translation_cache_timeout("es"), _translation_cache_timeout("es"))

    def test_cache_key_is_versioned(self):
        """A format change must not be read back as the old shape."""
        self.assertIn("v2", _translation_cache_key(DEFAULT_LANG))
        self.assertIn(DEFAULT_LANG, _translation_cache_key(DEFAULT_LANG))

    def test_served_from_cache_without_further_queries(self):
        self._make("greeting", {DEFAULT_LANG: "Hello"})
        _get_translation_data([DEFAULT_LANG])

        with self.assertNumQueries(0):
            _get_translation_data([DEFAULT_LANG])

    def test_rebuild_uses_a_single_query(self):
        """Guards against reintroducing parler's per-row descriptor access."""
        self._make("greeting", {DEFAULT_LANG: "Hello", "es": "Hola"})

        with self.assertNumQueries(1):
            _build_translation_data()

    def test_invalidation_clears_every_language(self):
        self._make("greeting", {DEFAULT_LANG: "Hello", "es": "Hola"})
        _get_translation_data()

        _invalidate_translation_cache()

        for lang in (DEFAULT_LANG, "es"):
            with self.subTest(lang=lang):
                self.assertIsNone(cache.get(_translation_cache_key(lang)))

    def test_edit_translation_is_reflected_after_invalidation(self):
        self._make("greeting", {DEFAULT_LANG: "Hello"})
        self.assertEqual(_get_translation_data([DEFAULT_LANG])[DEFAULT_LANG]["greeting"], "Hello")

        Translation.objects.edit_translation("greeting", DEFAULT_LANG, "Howdy")

        self.assertEqual(_get_translation_data([DEFAULT_LANG])[DEFAULT_LANG]["greeting"], "Howdy")

    def test_all_translations_matches_get_translation_data(self):
        self._make("greeting", {DEFAULT_LANG: "Hello", "es": "Hola"})

        self.assertEqual(
            Translation.objects.all_translations([DEFAULT_LANG, "es"]),
            _get_translation_data([DEFAULT_LANG, "es"]),
        )

    def test_parler_caching_is_disabled_in_parler_itself(self):
        """Guard the setting that made a cold rebuild serveable.

        parler.appsettings reads PARLER_ENABLE_CACHING once at import into a module
        constant, so override_settings cannot reach it -- this has to assert against
        appsettings, not django.conf.settings, or it passes no matter what
        settings.py says.
        """
        self.assertFalse(parler_appsettings.PARLER_ENABLE_CACHING)

    def test_rebuild_avoids_the_per_row_caching_the_old_walk_triggered(self):
        """The rebuild must not touch parler's descriptors.

        Each `translation.text` access routes through _cache_translation(), which at
        ~8.6k labels x 18 languages is ~156k calls per rebuild -- the thing that made
        a cold rebuild unserveable. The old-walk half is a control: without it, a
        rebuild that stopped touching parler for an unrelated reason would make the
        zero-assertion vacuous.

        Patched at parler.models, not parler.cache: models.py imports
        _cache_translation by name, so patching the cache module would miss the call
        site. Counting cache.set would instead count this module's own per-language
        writes, since parler shares the default cache object.
        """
        self._make("greeting", {DEFAULT_LANG: "Hello", "es": "Hola"})
        langs = [DEFAULT_LANG, "es"]

        with patch("parler.models._cache_translation") as new_path:
            data = _get_translation_data(langs)

        with patch("parler.models._cache_translation") as old_path:
            for translation in Translation.objects.prefetch_related("translations"):
                for lang in langs:
                    translation.set_current_language(lang)
                    translation.text

        self.assertEqual(data[DEFAULT_LANG]["greeting"], "Hello")
        self.assertEqual(data["es"]["greeting"], "Hola")
        self.assertEqual(new_path.call_count, 0)
        self.assertGreater(old_path.call_count, 0)


@override_settings(CACHES=LOCAL_CACHE)
class TestTranslationViewErrorPath(TestCase):
    """The failure path must not make a bad situation worse.

    Two amplifiers have lived here. Retrying the build inline doubled the cost of an
    already failing request, which is how this endpoint crossed the 30s router
    timeout. Invalidating on failure was the replacement: a failed rebuild writes
    nothing, so there is no bad entry to clear, and the likeliest exception source is
    the rebuild itself -- clearing threw away every still-warm language and forced the
    next request into a full rebuild against the same sick dependency.
    """

    def setUp(self):
        cache.clear()
        parent = Translation.objects.create(label="greeting", active=True)
        for lang in (DEFAULT_LANG, "es"):
            parent.create_translation(lang, text=f"Hello-{lang}", edited=True)
        _invalidate_translation_cache()

    def _get(self, lang):
        view = TranslationView.as_view(permission_classes=[AllowAny])
        return view(APIRequestFactory().get("/api/translations/", {"lang": lang}))

    def _warm_language_count(self):
        return sum(1 for lang in _all_langs() if cache.get(_translation_cache_key(lang)) is not None)

    def test_serves_translations_normally(self):
        response = self._get(DEFAULT_LANG)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[DEFAULT_LANG]["greeting"], f"Hello-{DEFAULT_LANG}")

    def test_failed_rebuild_leaves_other_languages_warm(self):
        _get_translation_data()  # warm every language
        cache.delete(_translation_cache_key("es"))  # simulate one LRU eviction
        warm_before = self._warm_language_count()

        with patch.object(translation_models, "_build_translation_data", side_effect=Exception("statement timeout")):
            response = self._get("es")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(self._warm_language_count(), warm_before)

    def test_failed_rebuild_caches_nothing(self):
        """Why invalidating buys nothing: there is no partial write to clean up."""
        with patch.object(translation_models, "_build_translation_data", side_effect=Exception("statement timeout")):
            self._get(DEFAULT_LANG)

        self.assertEqual(self._warm_language_count(), 0)

    def test_error_response_does_not_leak_exception_text(self):
        secret = "FATAL: password authentication failed for user 'benefits'"

        with patch.object(translation_models, "_build_translation_data", side_effect=Exception(secret)):
            response = self._get(DEFAULT_LANG)

        self.assertEqual(response.status_code, 503)
        self.assertNotIn("message", response.data)
        self.assertNotIn(secret, str(response.data))

    @override_settings(DEBUG=False)
    def test_no_traceback_outside_debug(self):
        with patch.object(translation_models, "_build_translation_data", side_effect=Exception("boom")):
            response = self._get(DEFAULT_LANG)

        self.assertNotIn("traceback", response.data)


class TestAdminAutoTranslateFailurePaths(TestCase):
    """
    The translation integrity guard raises where it used to silently write corrupted
    text. These admin views had no exception handling, so an unprotected guard turned
    a silent corruption into a 500 for the admin -- and in the create case the label
    row is committed before the translation call, so a 500 would strand a new label
    behind an error page with no explanation.
    """

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_superuser(email_or_cell="admin@example.com", password="pw")
        self.client.force_login(self.user)

    def _make_label(self, label, english):
        parent = Translation.objects.create(label=label, active=True)
        parent.create_translation(DEFAULT_LANG, text=english, edited=True)
        _invalidate_translation_cache()
        return parent

    @patch("translations.views.Translate")
    def test_create_with_icu_plural_does_not_500_and_still_creates_the_label(self, mock_translate):
        """An ICU string is refused by the guard; the label must still be created."""
        response = self.client.post(
            "/api/translations/admin",
            {"label": "test.plural", "default_message": "{count, plural, one {item} other {items}}"},
        )

        self.assertNotEqual(response.status_code, 500)
        self.assertTrue(Translation.objects.filter(label="test.plural").exists())
        # Refused before any API call, so the client is never even constructed.
        mock_translate.return_value.bulk_translate.assert_not_called()

    @patch("translations.views.Translate")
    def test_create_survives_an_integrity_error_from_the_client(self, mock_translate):
        mock_translate.return_value.bulk_translate.side_effect = TranslationIntegrityError("mangled")

        response = self.client.post(
            "/api/translations/admin",
            {"label": "test.placeholder", "default_message": "Are {subject} employed?"},
        )

        self.assertNotEqual(response.status_code, 500)
        self.assertTrue(Translation.objects.filter(label="test.placeholder").exists())

    @patch("translations.views.Translate")
    def test_edit_skips_only_the_failing_language(self, mock_translate):
        """A placeholder failure in one language must not cost the others, or 500."""
        parent = self._make_label("test.subject", "Are {subject} employed?")
        mock_translate.return_value.bulk_translate.return_value = {
            "Are {subject} changed?": {"es": "es-text"}  # note: 'fr' absent -> integrity failure
        }
        mock_translate.languages = ["es", "fr"]

        response = self.client.post(
            f"/api/translations/admin/{parent.id}/en-us",
            {"text": "Are {subject} changed?", "auto_translate_check": "on"},
        )

        self.assertNotEqual(response.status_code, 500)
        parent.refresh_from_db()
        parent.set_current_language("es")
        self.assertEqual(parent.text, "es-text")
        # fr was omitted by the guard, so no row should have been written for it.
        self.assertFalse(parent.has_translation("fr"))


class TestTranslationSaveDoesNotReportExpectedMisses(TestCase):
    """`Translation.save()` diffs each configured language against its pre-save text
    to fill in the latest history row's `affected_language`/`original_text` fields.

    A brand-new Translation has no prior text for any language, so there is nothing
    to diff. The languages must be skipped before the descriptor read that would
    raise for them -- otherwise every save reports a swallowed DoesNotExist per
    language to Sentry, which both floods the error budget and dominates the cost of
    creating a Translation.
    """

    def test_creating_a_translation_reports_nothing_to_sentry(self):
        with patch.object(translation_models, "capture_exception") as capture:
            Translation.objects.add_translation("test.save_reports_nothing", default_message="hello")

        self.assertEqual(
            capture.call_args_list,
            [],
            "creating a Translation should not funnel expected missing-language reads to Sentry",
        )

    def test_editing_a_translation_still_records_the_language_it_changed(self):
        translation = Translation.objects.add_translation("test.save_records_diff", default_message="before")

        with patch.object(translation_models, "capture_exception") as capture:
            Translation.objects.edit_translation("test.save_records_diff", DEFAULT_LANG, "after")

        self.assertEqual(capture.call_args_list, [])

        latest = Translation.objects.get(pk=translation.pk).history.first()
        self.assertEqual(latest.affected_language, DEFAULT_LANG)
        self.assertEqual(latest.original_text, "before")
        self.assertEqual(latest.changed_text, "after")

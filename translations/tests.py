"""Tests for the translation cache.

/api/translations/ is the only caller of the aggregate rebuild, and it is the
endpoint that went down when the cache moved to Redis. The rebuild reads the
translated table directly instead of touching parler's descriptors, and caches one
entry per language rather than a single ~15MB blob, so both properties are pinned
here.
"""

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase, override_settings

from translations.models import (
    Translation,
    _build_translation_data,
    _get_translation_data,
    _invalidate_translation_cache,
    _translation_cache_key,
)

# Pinned so these tests do not depend on whether the ambient REDIS_URL points at a
# reachable server; IGNORE_EXCEPTIONS would otherwise turn every set into a no-op
# and the assertions below would fail confusingly.
LOCAL_CACHE = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "translation-cache-tests",
    }
}

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

    @override_settings(PARLER_ENABLE_CACHING=False)
    def test_rebuild_works_with_parler_caching_disabled(self):
        """Parler's per-row entries are ~156k writes per rebuild and nothing reads them."""
        self._make("greeting", {DEFAULT_LANG: "Hello"})

        self.assertEqual(_get_translation_data([DEFAULT_LANG])[DEFAULT_LANG]["greeting"], "Hello")

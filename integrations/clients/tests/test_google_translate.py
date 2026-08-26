"""
Unit tests for placeholder protection in the Google Translate client.

These mock the Google API client directly rather than `bulk_translate`, because
the behaviour under test lives inside `bulk_translate` itself. The fake client
mimics the specific ways Google mangles `react-intl` placeholders, all observed
against the real API while diagnosing MFB-1733:

  - renames them   {subject} -> {sujeto} (es), {субъект} (ru), {주제} (ko)
  - drops them     French paraphrases the subject away entirely
  - localises ICU  plural -> pluriel (fr), 复数 with a fullwidth comma (zh-hans)
"""

from unittest.mock import patch

from django.test import TestCase

from integrations.clients.google_translate import (
    Translate,
    TranslationIntegrityError,
    is_auto_translatable,
    unsupported_reason,
)


def _fake_google(transform):
    """
    Build a stand-in for google.cloud.translate_v2.Client.

    `transform` receives each paragraph and returns the "translated" string, so a
    test can simulate a specific corruption. The shape of the return value matches
    what the real client produces: a list of dicts carrying input and translatedText.
    """

    class FakeClient:
        def translate(self, values, target_language=None, source_language=None):
            return [{"input": value, "translatedText": transform(value, target_language)} for value in values]

    return FakeClient()


class TranslateClientTestBase(TestCase):
    """Builds a Translate instance without touching credentials or the network."""

    def make_translator(self, transform) -> Translate:
        with patch.object(Translate, "__init__", lambda self: None):
            translator = Translate()
        translator.client = _fake_google(transform)
        return translator


class PlaceholderProtectionTests(TranslateClientTestBase):
    def test_placeholder_survives_a_translator_that_would_rename_it(self):
        """The whole point: a renaming translator must not be able to break the message."""

        def rename_braced_content(text, lang):
            # Stands in for Google turning {subject} into {sujeto}. It only fires on
            # literal braces, so protected sentinels pass through untouched.
            return text.replace("{subject}", "{sujeto}")

        translator = self.make_translator(rename_braced_content)
        result = translator.bulk_translate(["es"], ["Are {subject} employed?"])

        self.assertEqual(result["Are {subject} employed?"]["es"], "Are {subject} employed?")

    def test_multiple_placeholders_are_restored_in_the_right_order(self):
        source = "Tell us about your {relationship}, age {age}"

        translator = self.make_translator(lambda text, lang: text)
        self.assertEqual(translator.bulk_translate(["es"], [source])[source]["es"], source)

    def test_reordered_sentinels_each_resolve_to_their_own_placeholder(self):
        """
        Word order legitimately changes between languages, so the sentinels can come
        back in a different order. Each must still map to the placeholder it replaced
        rather than to its new position.
        """
        source = "Tell us about your {relationship}, age {age}"
        reversing = self.make_translator(lambda text, lang: "__PH1__ then __PH0__")

        result = reversing.bulk_translate(["ko"], [source])[source]["ko"]

        self.assertEqual(result, "{age} then {relationship}")

    def test_sentinel_is_not_left_in_the_output(self):
        translator = self.make_translator(lambda text, lang: text)
        source = "Step {step} of {total}"
        result = translator.bulk_translate(["fr"], [source])[source]["fr"]
        self.assertNotIn("__PH", result)
        self.assertEqual(result, source)

    def test_text_without_placeholders_is_unaffected(self):
        translator = self.make_translator(lambda text, lang: f"[{lang}] {text}")
        source = "Help finding shelter"
        result = translator.bulk_translate(["es"], [source])[source]["es"]
        self.assertEqual(result, "[es] Help finding shelter")

    def test_paragraph_structure_is_preserved_alongside_placeholders(self):
        source = "First line about {subject}\nSecond line about {other}"
        translator = self.make_translator(lambda text, lang: text)
        result = translator.bulk_translate(["ru"], [source])[source]["ru"]
        self.assertEqual(result, source)
        self.assertEqual(result.count("\n"), 1)


class IntegrityGuardTests(TranslateClientTestBase):
    def test_dropped_placeholder_is_rejected(self):
        """French paraphrased the subject away; that must fail rather than be stored."""

        def drop_the_sentinel(text, lang):
            return "Les personnes suivantes sont-elles employees?"

        translator = self.make_translator(drop_the_sentinel)
        with self.assertRaises(TranslationIntegrityError) as ctx:
            translator.bulk_translate(["fr"], ["Are {subject} employed?"])
        self.assertIn("{subject}", str(ctx.exception))

    def test_invented_sentinel_index_is_rejected(self):
        def invent_a_sentinel(text, lang):
            return f"{text} __PH7__"

        translator = self.make_translator(invent_a_sentinel)
        with self.assertRaises(TranslationIntegrityError):
            translator.bulk_translate(["es"], ["Are {subject} employed?"])

    def test_repeated_placeholder_must_come_back_the_same_number_of_times(self):
        """Multiset comparison: a dropped repeat changes meaning silently."""
        source = "{count} of {count}"
        translator = self.make_translator(lambda text, lang: text.replace("__PH1__", "").strip())
        with self.assertRaises(TranslationIntegrityError):
            translator.bulk_translate(["pl"], [source])

    def test_error_names_the_language_and_the_offending_text(self):
        translator = self.make_translator(lambda text, lang: "nothing here")
        with self.assertRaises(TranslationIntegrityError) as ctx:
            translator.bulk_translate(["ko"], ["Are {subject} employed?"])
        message = str(ctx.exception)
        self.assertIn("ko", message)
        self.assertIn("Are {subject} employed?", message)


class IcuRefusalTests(TranslateClientTestBase):
    ICU = "{count, plural, one {program} other {programs}}"

    def test_icu_plural_is_refused(self):
        translator = self.make_translator(lambda text, lang: text)
        with self.assertRaises(TranslationIntegrityError) as ctx:
            translator.bulk_translate(["fr"], [self.ICU])
        self.assertIn("plural", str(ctx.exception))

    def test_icu_select_is_refused(self):
        translator = self.make_translator(lambda text, lang: text)
        with self.assertRaises(TranslationIntegrityError):
            translator.bulk_translate(["fr"], ["{gender, select, male {he} other {they}}"])

    def test_batch_is_refused_before_any_api_call(self):
        """A bad string must not let its neighbours through half-translated."""
        calls = []

        def record(text, lang):
            calls.append(text)
            return text

        translator = self.make_translator(record)
        with self.assertRaises(TranslationIntegrityError):
            translator.bulk_translate(["es"], ["Fine {subject} string", self.ICU])
        self.assertEqual(calls, [], "no paragraph should be sent when the batch contains a refused string")

    def test_is_auto_translatable_classifies_correctly(self):
        self.assertTrue(is_auto_translatable("Are {subject} employed?"))
        self.assertTrue(is_auto_translatable("Help finding shelter"))
        self.assertFalse(is_auto_translatable(self.ICU))
        self.assertFalse(is_auto_translatable("already has __PH0__ in it"))

    def test_unsupported_reason_explains_the_plural_problem(self):
        reason = unsupported_reason(self.ICU)
        self.assertIsNotNone(reason)
        self.assertIn("Plural categories differ by language", reason)
        self.assertIsNone(unsupported_reason("Are {subject} employed?"))


class PerLanguageFailureTests(TranslateClientTestBase):
    """
    A placeholder failure in one language must not cost us the others. Observed
    live: zh-hans duplicated a sentinel for "Step {step} of {total}" while the
    other sixteen languages were clean.
    """

    SOURCE = "Step {step} of {total}"

    def _duplicating_in(self, bad_lang):
        def transform(text, lang):
            # google_lang codes are the mapped ones, so compare on the prefix
            return f"{text} (__PH0__)" if lang == bad_lang else text

        return transform

    def test_strict_by_default_so_nothing_degrades_silently(self):
        translator = self.make_translator(self._duplicating_in("es"))
        with self.assertRaises(TranslationIntegrityError):
            translator.bulk_translate(["es", "fr"], [self.SOURCE])

    def test_non_strict_keeps_the_good_languages(self):
        translator = self.make_translator(self._duplicating_in("es"))

        result = translator.bulk_translate(["es", "fr"], [self.SOURCE], strict=False)

        self.assertNotIn("es", result[self.SOURCE], "the mangled language must not be written")
        self.assertEqual(result[self.SOURCE]["fr"], self.SOURCE)

    def test_non_strict_records_the_failure_for_reporting(self):
        translator = self.make_translator(self._duplicating_in("es"))

        translator.bulk_translate(["es", "fr"], [self.SOURCE], strict=False)

        self.assertEqual(len(translator.last_integrity_failures), 1)
        text, lang, detail = translator.last_integrity_failures[0]
        self.assertEqual((text, lang), (self.SOURCE, "es"))
        self.assertIn("{step}", detail)

    def test_failures_reset_between_calls(self):
        translator = self.make_translator(self._duplicating_in("es"))
        translator.bulk_translate(["es"], [self.SOURCE], strict=False)
        self.assertEqual(len(translator.last_integrity_failures), 1)

        translator.bulk_translate(["fr"], [self.SOURCE], strict=False)
        self.assertEqual(translator.last_integrity_failures, [])


class FailureLogLifecycleTests(TranslateClientTestBase):
    """
    The failure log must always describe the most recent call. bulk_translate.py
    reuses one Translate across batches, so a stale log would misattribute a
    previous batch's failures to the current one.
    """

    ICU = "{count, plural, one {program} other {programs}}"

    def test_refusal_clears_the_previous_calls_failures(self):
        translator = self.make_translator(
            lambda text, lang: f"{text} (__PH0__)" if "__PH0__" in text else text,
        )

        translator.bulk_translate(["es"], ["Are {subject} employed?"], strict=False)
        self.assertEqual(len(translator.last_integrity_failures), 1)

        # A refused string raises before any translating happens; the log must still
        # have been reset, so a caller catching this does not read the stale entry.
        with self.assertRaises(TranslationIntegrityError):
            translator.bulk_translate(["es"], [self.ICU])

        self.assertEqual(translator.last_integrity_failures, [])

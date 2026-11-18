"""The text of the fixed replies the inbound webhook sends (MFB-2439)."""

from django.test import TestCase, override_settings

from integrations.services.communications import benji_sms_replies as replies
from translations.models import BLANK_TRANSLATION_PLACEHOLDER, Translation

LOGGER = "integrations.services.communications.benji_sms_replies"
ALL_REPLIES = [
    replies.STRANGER,
    replies.SHARED,
    replies.REENTRY,
    replies.STOP,
    replies.HELP,
    replies.START_RESUMED,
    replies.START_REENTRY,
    replies.PICTURE,
]


def add_translation(label: str, english: str, **others: str) -> Translation:
    translation = Translation.objects.add_translation(label, english)
    for language_code, text in others.items():
        translation.set_current_language(language_code)
        translation.text = text
        translation.save()
    return translation


@override_settings(FRONTEND_DOMAIN="https://screener.example.test/")
class ReplyTextTest(TestCase):
    def test_without_a_row_the_default_is_used_and_the_gap_is_logged(self) -> None:
        with self.assertLogs(LOGGER, level="WARNING") as logs:
            text = replies.reply_text(replies.REENTRY, "es")

        self.assertEqual(text, replies.REENTRY.default)
        self.assertIn(replies.REENTRY.label, logs.output[0])

    def test_the_conversations_language_is_used_when_translated(self) -> None:
        add_translation(replies.PICTURE.label, "English picture", es="Foto en español")

        self.assertEqual(replies.reply_text(replies.PICTURE, "es"), "Foto en español")
        self.assertEqual(replies.reply_text(replies.PICTURE, "ES"), "Foto en español")

    def test_an_untranslated_language_falls_back_to_english(self) -> None:
        """Rows for other languages start blank, or as a placeholder."""
        translation = add_translation(replies.PICTURE.label, "English picture")
        self.assertEqual(replies.reply_text(replies.PICTURE, "vi"), "English picture")

        translation.set_current_language("vi")
        translation.text = BLANK_TRANSLATION_PLACEHOLDER
        translation.save()
        self.assertEqual(replies.reply_text(replies.PICTURE, "vi"), "English picture")

    def test_an_unknown_or_missing_locale_falls_back_to_english(self) -> None:
        add_translation(replies.PICTURE.label, "English picture")
        for locale in (None, "", "xx", "en-US"):
            with self.subTest(locale=locale):
                self.assertEqual(replies.reply_text(replies.PICTURE, locale), "English picture")

    def test_a_placeholder_english_row_falls_back_to_the_default(self) -> None:
        add_translation(replies.STOP.label, BLANK_TRANSLATION_PLACEHOLDER)
        with self.assertLogs(LOGGER, level="WARNING"):
            self.assertEqual(replies.reply_text(replies.STOP), replies.STOP.default)

    def test_the_link_is_filled_in_for_defaults_and_translations(self) -> None:
        with self.assertLogs(LOGGER, level="WARNING"):
            default = replies.reply_text(replies.HELP)
        self.assertIn("https://screener.example.test for help", default)
        self.assertNotIn("{link}", default)

        add_translation(replies.HELP.label, "Go to {link} now")
        self.assertEqual(replies.reply_text(replies.HELP), "Go to https://screener.example.test now")

    def test_the_stranger_default_is_bilingual_with_the_link_in_both_halves(self) -> None:
        with self.assertLogs(LOGGER, level="WARNING"):
            text = replies.reply_text(replies.STRANGER)
        self.assertEqual(text.count("https://screener.example.test"), 2)
        self.assertIn("Reply STOP", text)
        self.assertIn("Responda STOP", text)

    def test_labels_are_distinct_and_every_default_fits_a_few_segments(self) -> None:
        self.assertEqual(len({reply.label for reply in ALL_REPLIES}), len(ALL_REPLIES))
        for reply in ALL_REPLIES:
            with self.subTest(label=reply.label):
                self.assertTrue(reply.label.startswith("benji.sms."))
                # The model's replies are capped at 450 characters; fixed ones stay under it.
                self.assertLessEqual(len(reply.default), 450)

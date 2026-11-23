from collections import Counter
from sentry_sdk import capture_exception
from django.conf import settings
from decouple import config
import json
import re
from google.oauth2 import service_account
from google.cloud import translate_v2 as translate
import html

# Matches a simple ICU argument such as {subject} or {count}. Deliberately
# excludes nested braces so it can never half-match a plural/select message.
_PLACEHOLDER_RE = re.compile(r"\{[^{}]*\}")

# Matches the opening of an ICU plural/select/selectordinal message.
_ICU_RE = re.compile(r"\{\s*\w+\s*,\s*(?:plural|select|selectordinal)\b")

# Sentinel substituted for each placeholder before the text is sent to Google.
# The double underscores are load-bearing: a bare token gets semantically
# reinterpreted (Google read "PH0" as pH and returned "acidity level" in
# Arabic), and control-character delimiters are stripped outright.
_SENTINEL = "__PH{}__"
_SENTINEL_RE = re.compile(r"__PH(\d+)__")


class TranslationIntegrityError(Exception):
    """
    Raised when a string cannot be auto-translated safely, either because it is
    a kind we refuse to machine-translate or because the translation came back
    with its placeholders altered.
    """


def unsupported_reason(text: str) -> str | None:
    """
    Return why `text` cannot be safely auto-translated, or None if it can be.

    Deliberately a module-level function rather than a method: classification is a
    pure property of the string, needing no credentials, client or network. That
    lets callers filter a batch without constructing a Translate, and keeps tests
    that mock the API client from accidentally stubbing out this logic too.
    """
    if _ICU_RE.search(text):
        return (
            "contains an ICU plural/select message. Plural categories differ by language "
            "(English has 2, Russian and Polish 3-4, Arabic 6), so machine translation "
            "cannot produce the forms the source does not have. Needs a human translation, "
            "or rephrase the English so it does not need a plural at all."
        )
    if _SENTINEL_RE.search(text):
        return "contains the reserved placeholder-protection token __PHn__"
    return None


def is_auto_translatable(text: str) -> bool:
    """True when `text` can be machine-translated without corrupting it."""
    return unsupported_reason(text) is None


class Translate:
    """
    Google Translate integration for the benefits API.

    This class preserves paragraph structure by splitting input text into paragraphs before translation
    and joining them after translation. This ensures that multi-paragraph texts retain their original
    formatting when translated. All translation entry points (single and bulk) use this logic.

    It also protects `react-intl` placeholders. Sent unprotected, Google translates
    the contents of {...} along with everything else: {subject} comes back as
    {sujeto} in Spanish and {субъект} in Russian, and French drops it entirely by
    paraphrasing it away. The frontend then passes values={{ subject }} against a
    message that no longer references `subject`, so the value never renders. Every
    placeholder is therefore swapped for a sentinel before the API call, restored
    after, and the result is verified before it is handed back.
    """

    main_language: str = settings.LANGUAGE_CODE
    languages: list[str] = [
        lang["code"] for lang in settings.PARLER_LANGUAGES[None] if lang["code"] != settings.LANGUAGE_CODE
    ]

    @staticmethod
    def split_paragraphs(text):
        """
        Splits text into paragraphs using two or more consecutive newlines as delimiters.
        Preserves empty paragraphs and leading/trailing whitespace.
        """
        # Normalize newlines
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        # Split on two or more newlines
        paragraphs = normalized.split("\n")
        return paragraphs

    @staticmethod
    def join_paragraphs(paragraphs):
        """
        Joins paragraphs with two newlines to preserve paragraph breaks.
        """
        return "\n".join(paragraphs)

    def __init__(self):
        info = json.loads(config("GOOGLE_APPLICATION_CREDENTIALS"))
        creds = service_account.Credentials.from_service_account_info(info)
        self.client = translate.Client(credentials=creds)
        # Per-call log of (text, lang, detail) for placeholder failures tolerated
        # under strict=False. Reset at the start of every bulk_translate.
        self.last_integrity_failures: list[tuple[str, str, str]] = []

    LANGUAGE_CODE_MAPPING = {
        "pt-br": "pt",  # Map pt-br to pt for Google Translate
        "en-us": "en",
    }

    def _map_language_code(self, lang_code):
        return self.LANGUAGE_CODE_MAPPING.get(lang_code, lang_code)

    @staticmethod
    def _protect_placeholders(text: str) -> tuple[str, list[str]]:
        """
        Swap every {placeholder} for an opaque sentinel, returning the protected
        text and the placeholders in the order they were replaced.
        """
        found: list[str] = []

        def _replace(match: re.Match) -> str:
            found.append(match.group(0))
            return _SENTINEL.format(len(found) - 1)

        return _PLACEHOLDER_RE.sub(_replace, text), found

    @staticmethod
    def _restore_placeholders(text: str, placeholders: list[str]) -> str:
        """Put the original placeholders back where their sentinels ended up."""

        def _replace(match: re.Match) -> str:
            index = int(match.group(1))
            # An out-of-range index means the model invented a sentinel; leave it
            # alone so the integrity check below reports the discrepancy.
            return placeholders[index] if index < len(placeholders) else match.group(0)

        return _SENTINEL_RE.sub(_replace, text)

    @staticmethod
    def _assert_placeholders_intact(source: str, translated: str, lang: str) -> None:
        """
        Refuse a translation whose placeholders do not match the source exactly.

        Compares multisets rather than sets: a source that uses {count} twice must
        come back with it twice, since a dropped repeat silently changes meaning.
        Also rejects any protection sentinel left behind, which the multiset check
        alone would miss. Failing loudly here is the point - a silent corruption is
        what let 18 keys reach production with unresolvable placeholders.
        """
        # A sentinel left in the output means the model invented an index we never
        # issued. The placeholder multiset can still match in that case, so this is
        # checked separately - otherwise a literal "__PH7__" renders to the user.
        leftover = _SENTINEL_RE.findall(translated)
        if leftover:
            raise TranslationIntegrityError(
                f"Translation to {lang} left unresolved protection tokens "
                f"{sorted(set(leftover))} in {translated!r} (source {source!r})"
            )

        expected = Counter(_PLACEHOLDER_RE.findall(source))
        actual = Counter(_PLACEHOLDER_RE.findall(translated))
        if expected == actual:
            return

        lost = sorted((expected - actual).elements())
        gained = sorted((actual - expected).elements())
        raise TranslationIntegrityError(
            f"Translation to {lang} altered the placeholders of {source!r}: "
            f"got {translated!r} (missing {lost}, unexpected {gained})"
        )

    def translate(self, lang: str, text: str):
        """
        Translates the text from the default language to the lang param language, preserving paragraph structure.
        """
        if lang not in Translate.languages:
            raise Exception(f"{lang} is not configured in settings, or is the default language")

        # Short-circuit for empty string
        if text == "":
            return ""

        # Delegate to bulk_translate for consistency and DRYness
        result = self.bulk_translate([lang], [text])
        return result[text][lang]

    def bulk_translate(self, langs: list[str], texts: list[str], strict: bool = True):
        """
        Translates all of the texts to the target langs, preserving paragraph structure for each text.
        Include __all__ in langs to translate to all languages.

        Raises TranslationIntegrityError for a string we refuse to machine-translate
        (see the module-level `unsupported_reason`) or one whose placeholders did not survive the
        round trip. Filter with `is_auto_translatable` first if a batch should skip
        such strings rather than abort.

        Placeholder failures are per-language, not per-string: Google can mangle a
        placeholder in one language and handle the other sixteen perfectly. Observed
        live - "Step {step} of {total}" came back from zh-hans as
        "步骤 {step}（{total} 的 {step}）", duplicating a sentinel, while every other
        language was clean.

        With strict=True (the default) any such failure raises, so no caller degrades
        silently. With strict=False the offending language is omitted from that text's
        result and recorded in `last_integrity_failures`, letting a caller keep the
        languages that worked and report the ones that did not. An omitted row is the
        right degradation: with no row at all the API falls back to English, whereas a
        blank row would render as empty text.
        """
        if "__all__" in langs:
            langs = Translate.languages

        # Reset before the refusal check, not after: a caller that catches the refusal
        # and then reads last_integrity_failures must not see the previous call's
        # failures attributed to this batch.
        self.last_integrity_failures = []

        for text in texts:
            reason = unsupported_reason(text)
            if reason is not None:
                raise TranslationIntegrityError(f"Refusing to auto-translate {text!r}: it {reason}")

        translations = {text: {} for text in texts}
        for lang in langs:
            if lang not in Translate.languages:
                raise Exception(f"{lang} is not configured in settings, or is the default language")

            # Use mapped code for Google Translate
            google_lang = self._map_language_code(lang)
            google_source = self._map_language_code(Translate.main_language)

            # For each text, protect placeholders, split into paragraphs, translate, and rejoin
            for text in texts:
                protected, placeholders = self._protect_placeholders(text)
                paragraphs = self.split_paragraphs(protected)

                try:
                    results = self.client.translate(
                        paragraphs,
                        target_language=google_lang,
                        source_language=google_source,
                    )
                except Exception as e:
                    capture_exception(e, level="error")
                    raise
                if isinstance(results, dict):
                    translated_paragraphs = [self.format_text(results)]
                else:
                    translated_paragraphs = [self.format_text(res) for res in results]

                restored = self._restore_placeholders(self.join_paragraphs(translated_paragraphs), placeholders)
                try:
                    self._assert_placeholders_intact(text, restored, lang)
                except TranslationIntegrityError as e:
                    if strict:
                        raise
                    # Omit this language and carry on; the caller reports the gap.
                    self.last_integrity_failures.append((text, lang, str(e)))
                    continue
                translations[text][lang] = restored
        return translations

    def format_text(self, result):
        # If the input is whitespace-only, return it unchanged
        if result["input"].strip() == "":
            return result["input"]
        leading_spaces = len(result["input"]) - len(result["input"].lstrip(" "))
        trailing_spaces = len(result["input"]) - len(result["input"].rstrip(" "))
        return " " * leading_spaces + html.unescape(result["translatedText"]).strip() + " " * trailing_spaces

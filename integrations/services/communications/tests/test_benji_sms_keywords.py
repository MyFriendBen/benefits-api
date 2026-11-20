"""Which inbound texts are opt-out keywords, and whether Twilio or we answer them (MFB-2439)."""

from django.test import SimpleTestCase

from integrations.services.communications.benji_sms_keywords import (
    CARRIER_KEYWORDS,
    OUR_KEYWORDS,
    Keyword,
    KeywordMatch,
    _normalize,
    classify,
)


class ClassifyTest(SimpleTestCase):
    def test_twilios_own_words_are_carrier_keywords(self) -> None:
        for keyword, words in CARRIER_KEYWORDS.items():
            for word in words:
                with self.subTest(word=word):
                    match = classify(word)
                    assert match is not None
                    self.assertEqual((match.keyword, match.carrier), (keyword, True))

    def test_case_and_surrounding_space_do_not_matter(self) -> None:
        for body in ["STOP", "Stop", " stop ", "stop\n", "\tSTOP"]:
            with self.subTest(body=body):
                self.assertEqual(classify(body), KeywordMatch(Keyword.STOP, carrier=True))

    def test_a_carrier_word_with_anything_else_is_ours_to_answer(self) -> None:
        """Twilio acts only on the bare word. Guessing "ours" is the harmless direction."""
        for body in ["Stop.", "STOP!", "stop!!", '"stop"', "¡help!"]:
            with self.subTest(body=body):
                match = classify(body)
                assert match is not None
                self.assertFalse(match.carrier)

    def test_our_extended_wordings(self) -> None:
        cases = {
            "alto": Keyword.STOP,
            "ALTO": Keyword.STOP,
            "Alto.": Keyword.STOP,
            "no más": Keyword.STOP,
            "No mas": Keyword.STOP,
            "NO MÁS MENSAJES": Keyword.STOP,
            "please stop": Keyword.STOP,
            "Stop texting me!": Keyword.STOP,
            "opt out": Keyword.STOP,
            "opt-out": Keyword.STOP,
            "ayuda": Keyword.HELP,
            "¡Ayuda!": Keyword.HELP,
            "información": Keyword.HELP,
            "iniciar": Keyword.START,
            "start again": Keyword.START,
        }
        for body, keyword in cases.items():
            with self.subTest(body=body):
                self.assertEqual(classify(body), KeywordMatch(keyword, carrier=False))

    def test_only_a_whole_message_matches(self) -> None:
        for body in [
            "stop sending me to that website",
            "how do I stop my snap benefits",
            "can you help me apply",
            "I need help",
            "when does it start",
            "alto ahi",
            "help 申请福利",
            "stop 我的福利",
            "Stop отправлять",
            "yes 谢谢",
            "ayuda 도와주세요",
            "what is snap",
            "",
            "   ",
            "?",
        ]:
            with self.subTest(body=body):
                self.assertIsNone(classify(body))

    def test_emoji_and_symbols_around_a_keyword_still_match(self) -> None:
        for body in ["stop 🙏", "alto 🙏🙏", "ＳＴＯＰ", "stop_", "--alto--"]:
            with self.subTest(body=body):
                match = classify(body)
                assert match is not None
                self.assertEqual((match.keyword, match.carrier), (Keyword.STOP, False))

    def test_letters_in_every_script_are_kept(self) -> None:
        self.assertEqual(_normalize("Stop отправлять!"), "stop отправлять")
        self.assertEqual(_normalize("help 申请福利"), "help 申请福利")
        self.assertEqual(_normalize("¿Información?"), "informacion")

    def test_none_is_not_a_keyword(self) -> None:
        self.assertIsNone(classify(None))

    def test_yes_is_marked_as_also_an_ordinary_answer(self) -> None:
        self.assertEqual(classify("yes"), KeywordMatch(Keyword.START, carrier=True, also_plain_text=True))
        self.assertEqual(classify("Yes!"), KeywordMatch(Keyword.START, carrier=False, also_plain_text=True))
        for body in ["start", "unstop", "iniciar"]:
            match = classify(body)
            assert match is not None
            self.assertFalse(match.also_plain_text, body)

    def test_opt_out_type_from_twilio_wins_over_the_wording(self) -> None:
        self.assertEqual(classify("alto", "STOP"), KeywordMatch(Keyword.STOP, carrier=True))
        self.assertEqual(classify("anything at all", "HELP"), KeywordMatch(Keyword.HELP, carrier=True))
        self.assertEqual(classify("", "start"), KeywordMatch(Keyword.START, carrier=True))

    def test_a_declared_start_for_yes_is_also_plain_text(self) -> None:
        self.assertEqual(classify("Yes", "START"), KeywordMatch(Keyword.START, carrier=True, also_plain_text=True))
        self.assertEqual(classify("start", "START"), KeywordMatch(Keyword.START, carrier=True))

    def test_an_unknown_opt_out_type_falls_back_to_the_wording(self) -> None:
        self.assertEqual(classify("alto", "SOMETHING"), KeywordMatch(Keyword.STOP, carrier=False))
        self.assertIsNone(classify("what is snap", ""))

    def test_the_lists_are_already_normalized_and_do_not_overlap(self) -> None:
        """An entry `_normalize` would change could never match."""
        seen: dict[str, Keyword] = {}
        for table in (CARRIER_KEYWORDS, OUR_KEYWORDS):
            for keyword, words in table.items():
                for word in words:
                    self.assertEqual(_normalize(word), word)
                    self.assertNotIn(word, seen)
                    seen[word] = keyword

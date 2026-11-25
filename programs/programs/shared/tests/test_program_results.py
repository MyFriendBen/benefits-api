from unittest.mock import Mock

from django.test import SimpleTestCase

from programs.programs.shared.program_results import eligible_in_results, has_or_is_eligible_for


def result(code: str, eligible: bool) -> dict:
    return {"name_abbreviated": code, "eligible": eligible}


class TestEligibleInResults(SimpleTestCase):
    def test_true_when_the_program_is_eligible(self):
        self.assertTrue(eligible_in_results([result("tx_wic", False), result("tx_snap", True)], "tx_snap"))

    def test_false_when_the_program_is_ineligible(self):
        self.assertFalse(eligible_in_results([result("tx_snap", False)], "tx_snap"))

    def test_false_when_the_program_is_absent(self):
        self.assertFalse(eligible_in_results([result("tx_wic", True)], "tx_snap"))

    def test_no_results(self):
        self.assertFalse(eligible_in_results(None, "tx_snap"))
        self.assertFalse(eligible_in_results([], "tx_snap"))

    def test_skips_entries_that_are_not_dicts(self):
        self.assertTrue(eligible_in_results(["unexpected", result("tx_snap", True)], "tx_snap"))

    def test_returns_a_bool(self):
        self.assertIs(eligible_in_results([{"name_abbreviated": "tx_snap", "eligible": 1}], "tx_snap"), True)


class TestHasOrIsEligibleFor(SimpleTestCase):
    def screen(self, has_benefit: bool) -> Mock:
        screen = Mock()
        screen.has_benefit.return_value = has_benefit
        return screen

    def test_true_when_already_receiving(self):
        screen = self.screen(has_benefit=True)
        self.assertTrue(has_or_is_eligible_for(screen, [], "tx_snap"))
        screen.has_benefit.assert_called_once_with("tx_snap")

    def test_true_when_eligible_in_results(self):
        self.assertTrue(has_or_is_eligible_for(self.screen(has_benefit=False), [result("tx_snap", True)], "tx_snap"))

    def test_false_when_neither(self):
        self.assertFalse(has_or_is_eligible_for(self.screen(has_benefit=False), [result("tx_snap", False)], "tx_snap"))

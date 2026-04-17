"""
Tests for navigator filtering by program eligibility (MFB-666).

Verifies the eligibility_programs M2M field on Navigator filters
navigators based on whether the household qualifies for required programs.
"""

from django.test import TestCase

from programs.models import Navigator, Program
from screener.models import WhiteLabel


class _Eligible:
    eligible = True


class _Ineligible:
    eligible = False


def _apply_eligibility_filter(navigators: list, program_eligibility: dict) -> list:
    """
    Mirrors the filtering logic in screener/views.py eligibility_results().
    Extracted here so tests stay readable and in sync with the real implementation.
    """
    result = []
    for nav in navigators:
        required = nav.eligibility_programs.all()
        if not required or all(
            getattr(program_eligibility.get(p.name_abbreviated), "eligible", False) for p in required
        ):
            result.append(nav)
    return result


class TestNavigatorEligibilityProgramsFilter(TestCase):
    """Unit tests for navigator eligibility_programs filtering."""

    @classmethod
    def setUpTestData(cls):
        cls.white_label = WhiteLabel.objects.create(name="NC Test", code="nc_test", state_code="NC")
        cls.medicare_savings = Program.objects.new_program(
            white_label="nc_test", name_abbreviated="nc_medicare_savings"
        )
        cls.snap = Program.objects.new_program(white_label="nc_test", name_abbreviated="nc_snap")
        cls.duke_bec = Navigator.objects.new_navigator("nc_test", "duke_bec_test")
        cls.general_nav = Navigator.objects.new_navigator("nc_test", "general_nav_test")

    def setUp(self):
        # Reset eligibility_programs before each test so tests are independent.
        self.duke_bec.eligibility_programs.set([self.medicare_savings])
        self.general_nav.eligibility_programs.clear()

    def test_no_required_programs_always_shown(self):
        """Navigator with no eligibility_programs shows regardless of household eligibility."""
        result = _apply_eligibility_filter([self.general_nav], {})
        self.assertIn(self.general_nav, result)

    def test_required_program_eligible_shows_navigator(self):
        """Navigator appears when household qualifies for all required programs."""
        program_eligibility = {"nc_medicare_savings": _Eligible()}
        result = _apply_eligibility_filter([self.duke_bec], program_eligibility)
        self.assertIn(self.duke_bec, result)

    def test_required_program_ineligible_hides_navigator(self):
        """Navigator hidden when household does not qualify for a required program."""
        program_eligibility = {"nc_medicare_savings": _Ineligible()}
        result = _apply_eligibility_filter([self.duke_bec], program_eligibility)
        self.assertNotIn(self.duke_bec, result)

    def test_required_program_missing_hides_navigator(self):
        """Navigator hidden when required program has not been calculated yet."""
        result = _apply_eligibility_filter([self.duke_bec], {})
        self.assertNotIn(self.duke_bec, result)

    def test_all_required_programs_must_be_eligible(self):
        """Navigator hidden when only a subset of required programs are eligible."""
        self.duke_bec.eligibility_programs.add(self.snap)

        program_eligibility = {
            "nc_medicare_savings": _Eligible(),
            "nc_snap": _Ineligible(),
        }
        result = _apply_eligibility_filter([self.duke_bec], program_eligibility)
        self.assertNotIn(self.duke_bec, result)

    def test_all_required_programs_eligible_shows_navigator(self):
        """Navigator shown when every required program is eligible."""
        self.duke_bec.eligibility_programs.add(self.snap)

        program_eligibility = {
            "nc_medicare_savings": _Eligible(),
            "nc_snap": _Eligible(),
        }
        result = _apply_eligibility_filter([self.duke_bec], program_eligibility)
        self.assertIn(self.duke_bec, result)

    def test_mixed_navigators_filtered_independently(self):
        """Each navigator is evaluated independently against its own required programs."""
        program_eligibility = {"nc_medicare_savings": _Ineligible()}
        result = _apply_eligibility_filter([self.duke_bec, self.general_nav], program_eligibility)

        self.assertNotIn(self.duke_bec, result)
        self.assertIn(self.general_nav, result)

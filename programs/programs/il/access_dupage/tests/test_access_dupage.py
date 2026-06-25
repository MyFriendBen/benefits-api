"""
Unit tests for the IlAccessDuPage calculator.

Eligibility requirements (spec.md):
- Permanent DuPage County resident (county check)
- Household income at or below 250% FPL
- At least one household member age 19+ who reports being uninsured and has no
  disqualifying coverage (Medicaid, Medicare, employer, private)

Access DuPage is an in-kind program with no dollar benefit, so the calculated value
is always $0.

2026 FPL anchors used in these tests (100% FPL): HH1 = $15,960 -> 250% = $39,900.
"""

from django.test import TestCase
from unittest.mock import Mock

from programs.programs.il import il_calculators
from programs.programs.il.access_dupage.calculator import IlAccessDuPage
from programs.programs.calc import Eligibility, MemberEligibility, ProgramCalculator


def make_member(age=40, insurance="none"):
    """Create a mock household member.

    `insurance` is the member's single coverage state, one of:
    "none", "dont_know", "medicaid", "medicare", "employer", "private".
    """
    member = Mock()
    member.age = age

    def has_insurance_types(types, strict=True):
        wanted = set(types)
        if "none" in wanted:
            wanted.add("dont_know")
        return insurance in wanted

    member.has_insurance_types = Mock(side_effect=has_insurance_types)
    return member


def make_calculator(county="DuPage", household_income=0, household_size=1, fpl_limit=15_960, members=None):
    """Create an IlAccessDuPage calculator with a mocked screen and program."""
    mock_program = Mock()
    mock_program.year.get_limit.return_value = fpl_limit

    mock_screen = Mock()
    mock_screen.county = county
    mock_screen.household_size = household_size
    mock_screen.calc_gross_income = Mock(return_value=household_income)
    mock_screen.household_members.all = Mock(return_value=members if members is not None else [make_member()])

    mock_missing_deps = Mock()
    mock_missing_deps.has.return_value = False

    return IlAccessDuPage(mock_screen, mock_program, {}, mock_missing_deps)


def make_eligible_member_e(member):
    """A passing MemberEligibility, for household_eligible tests."""
    me = MemberEligibility(member)
    me.eligible = True
    return me


class TestIlAccessDuPageClassAttributes(TestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(IlAccessDuPage, ProgramCalculator))

    def test_is_registered_in_il_calculators(self):
        self.assertIn("il_access_dupage", il_calculators)
        self.assertEqual(il_calculators["il_access_dupage"], IlAccessDuPage)

    def test_fpl_percent_is_2_5(self):
        self.assertEqual(IlAccessDuPage.fpl_percent, 2.5)

    def test_min_age_is_19(self):
        self.assertEqual(IlAccessDuPage.min_age, 19)

    def test_eligible_counties(self):
        self.assertEqual(IlAccessDuPage.eligible_counties, ["DuPage"])

    def test_no_dollar_value(self):
        self.assertEqual(IlAccessDuPage.amount, 0)
        self.assertEqual(IlAccessDuPage.member_amount, 0)


class TestIlAccessDuPageMemberEligibility(TestCase):
    """Age and insurance gate in member_eligible."""

    def _run(self, member):
        calc = make_calculator()
        e = MemberEligibility(member)
        calc.member_eligible(e)
        return e.eligible

    def test_age_19_uninsured_is_eligible(self):
        self.assertTrue(self._run(make_member(age=19, insurance="none")))

    def test_age_18_is_ineligible(self):
        self.assertFalse(self._run(make_member(age=18, insurance="none")))

    def test_age_none_is_ineligible(self):
        self.assertFalse(self._run(make_member(age=None, insurance="none")))

    def test_age_64_uninsured_is_eligible(self):
        self.assertTrue(self._run(make_member(age=64, insurance="none")))

    def test_dont_know_insurance_is_treated_as_uninsured(self):
        # Data-gap default: a member who doesn't know their coverage is included.
        self.assertTrue(self._run(make_member(age=40, insurance="dont_know")))

    def test_medicaid_is_ineligible(self):
        self.assertFalse(self._run(make_member(age=40, insurance="medicaid")))

    def test_medicare_is_ineligible(self):
        self.assertFalse(self._run(make_member(age=40, insurance="medicare")))

    def test_employer_insurance_is_ineligible(self):
        self.assertFalse(self._run(make_member(age=40, insurance="employer")))

    def test_private_insurance_is_ineligible(self):
        self.assertFalse(self._run(make_member(age=40, insurance="private")))


class TestIlAccessDuPageHouseholdEligibility(TestCase):
    """County and income gates in household_eligible."""

    def _run(self, county="DuPage", household_income=0, household_size=1, fpl_limit=15_960):
        calc = make_calculator(
            county=county, household_income=household_income, household_size=household_size, fpl_limit=fpl_limit
        )
        e = Eligibility()
        e.add_member_eligibility(make_eligible_member_e(make_member(age=40)))
        calc.household_eligible(e)
        return e.eligible

    def test_dupage_resident_low_income_is_eligible(self):
        self.assertTrue(self._run(county="DuPage", household_income=20_000))

    def test_non_dupage_resident_is_ineligible(self):
        self.assertFalse(self._run(county="Cook", household_income=20_000))

    def test_income_exactly_at_250_fpl_is_eligible(self):
        # 250% of $15,960 = $39,900
        self.assertTrue(self._run(household_income=39_900))

    def test_income_one_dollar_over_250_fpl_is_ineligible(self):
        self.assertFalse(self._run(household_income=39_901))

    def test_income_scales_with_household_size(self):
        # HH3 100% FPL = $27,320 -> 250% = $68,300
        self.assertTrue(self._run(household_income=68_300, household_size=3, fpl_limit=27_320))
        calc_ineligible = self._run(household_income=68_301, household_size=3, fpl_limit=27_320)
        self.assertFalse(calc_ineligible)


class TestIlAccessDuPageIntegration(TestCase):
    """End-to-end calc() covering the spec's representative scenarios."""

    def _eligible(self, **kwargs):
        return make_calculator(**kwargs).calc().eligible

    def test_scenario_1_eligible_uninsured_adult(self):
        members = [make_member(age=40, insurance="none")]
        self.assertTrue(self._eligible(county="DuPage", household_income=21_600, members=members))

    def test_scenario_5_non_dupage_is_ineligible(self):
        members = [make_member(age=40, insurance="none")]
        self.assertFalse(self._eligible(county="Cook", household_income=21_600, members=members))

    def test_scenario_4_income_over_limit_is_ineligible(self):
        members = [make_member(age=40, insurance="none")]
        self.assertFalse(self._eligible(county="DuPage", household_income=39_912, members=members))

    def test_scenario_7_age_18_is_ineligible(self):
        members = [make_member(age=18, insurance="none")]
        self.assertFalse(self._eligible(county="DuPage", household_income=14_400, members=members))

    def test_scenario_8_medicaid_enrolled_is_ineligible(self):
        members = [make_member(age=40, insurance="medicaid")]
        self.assertFalse(self._eligible(county="DuPage", household_income=14_400, members=members))

    def test_scenario_10_mixed_household_one_eligible_adult(self):
        # Eligible uninsured adult + insured spouse + insured child + Medicare parent.
        members = [
            make_member(age=38, insurance="none"),
            make_member(age=35, insurance="employer"),
            make_member(age=10, insurance="employer"),
            make_member(age=67, insurance="medicare"),
        ]
        self.assertTrue(
            self._eligible(
                county="DuPage", household_income=61_320, household_size=4, fpl_limit=33_000, members=members
            )
        )

    def test_value_is_zero_for_eligible_household(self):
        members = [make_member(age=40, insurance="none")]
        eligibility = make_calculator(county="DuPage", household_income=21_600, members=members).calc()
        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 0)

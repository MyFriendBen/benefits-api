"""
Unit tests for the CoHeadStart (co_head_start) calculator.

Eligibility requirements:
  1. Household is in a county flagged as participating in the Head Start counties sheet
  2. Monthly gross household income below 100% FPL / 12 (130% in Adams County)
  3. Member is aged 3 to 5

Notes:
  - The participating-county list comes from a Google Sheet. `GoogleSheetsCache.get_data()`
    swallows fetch errors and falls back to the last known-good value, or `{}` when none is
    cached, so a sheet outage silently makes every Colorado household ineligible rather than
    raising. That behaviour is pinned below so a future change to the cache doesn't slip past.
  - The county lookup `break`s on the first county present in the sheet, so a county
    explicitly flagged FALSE is a rejection, not a "keep looking".
  - Both income limits are truncated with `int()` and compared with a strict `<`.
  - FPL figures are imported from `programs.models._FPL_DEFAULTS` rather than copied, so
    they cannot drift from the table production reads. That constant is a plain offline
    literal that `FederalPoveryLimit.as_dict()` reads directly, so importing it costs no
    database or network access.
"""

from unittest.mock import Mock, patch

from django.test import TestCase

from programs.models import _FPL_DEFAULTS
from programs.framework.base import Eligibility, MemberEligibility, ProgramCalculator
from programs.programs.cross_white_label.head_start.co import CoHeadStart
from programs.util import Dependencies, DependencyError
from programs.framework.pe_dependencies import member

FPL_2025 = _FPL_DEFAULTS["2025"]

PARTICIPATING_COUNTIES = {
    "Denver County": True,
    "Adams County": True,
    "Jefferson County": False,
}


def make_member(age=4):
    member = Mock()
    member.age = age
    return member


def make_calculator(
    county="Denver County",
    zipcode="80205",
    household_size=2,
    household_income=0,
    members=None,
    missing_dependencies=None,
):
    mock_program = Mock()
    mock_program.year.as_dict.return_value = FPL_2025

    mock_screen = Mock()
    mock_screen.county = county
    mock_screen.zipcode = zipcode
    mock_screen.household_size = household_size
    mock_screen.calc_gross_income = Mock(return_value=household_income)
    mock_screen.household_members.all.return_value = [make_member()] if members is None else members

    return CoHeadStart(
        mock_screen,
        mock_program,
        {},
        Dependencies() if missing_dependencies is None else missing_dependencies,
    )


class CountySheetTestCase(TestCase):
    """Patches the shared Google Sheets cache instance on the calculator class."""

    counties = PARTICIPATING_COUNTIES

    def setUp(self):
        patcher = patch.object(CoHeadStart.counties, "get_data", return_value=dict(self.counties))
        self.mock_counties_get_data = patcher.start()
        self.addCleanup(patcher.stop)


class TestCoHeadStartClassAttributes(TestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(CoHeadStart, ProgramCalculator))

    def test_member_amount_is_10655(self):
        self.assertEqual(CoHeadStart.member_amount, 10_655)

    def test_no_household_amount(self):
        self.assertEqual(CoHeadStart.amount, 0)

    def test_min_age_is_3(self):
        self.assertEqual(CoHeadStart.min_age, 3)

    def test_max_age_is_5(self):
        self.assertEqual(CoHeadStart.max_age, 5)

    def test_adams_county_uses_130_percent_fpl(self):
        self.assertEqual(CoHeadStart.adams_percent_of_fpl, 1.3)

    def test_adams_county_name(self):
        self.assertEqual(CoHeadStart.adams_county, "Adams County")

    def test_dependencies(self):
        self.assertEqual(
            CoHeadStart.dependencies,
            ["age", "household_size", "income_frequency", "income_amount", "zipcode"],
        )

    def test_county_cache_falls_back_to_empty(self):
        self.assertEqual(CoHeadStart.counties._empty_fallback(), {})


class TestCoHeadStartLocation(CountySheetTestCase):
    """County must be present in the sheet AND flagged TRUE."""

    def _run(self, county, zipcode="80205"):
        calc = make_calculator(county=county, zipcode=zipcode, household_income=0)
        e = Eligibility()
        calc.household_eligible(e)
        return e

    def test_participating_county_is_eligible(self):
        self.assertTrue(self._run("Denver County").eligible)

    def test_county_flagged_false_is_ineligible(self):
        self.assertFalse(self._run("Jefferson County").eligible)

    def test_county_absent_from_the_sheet_is_ineligible(self):
        self.assertFalse(self._run("Pueblo County").eligible)

    def test_county_is_resolved_from_zipcode_when_unset(self):
        self.assertTrue(self._run(None, zipcode="80205").eligible)

    def test_ineligible_county_gets_a_fail_message(self):
        # income passes at $0, so the only failure is location
        e = self._run("Pueblo County")
        self.assertEqual(len(e.fail_messages), 1)


class TestCoHeadStartMultiCountyZip(CountySheetTestCase):
    """
    Most CO zipcodes span several counties, so when `screen.county` is unset the county
    loop really does iterate. It `break`s on the first county the sheet knows about, so a
    leading FALSE county rejects the household even when a later one is flagged TRUE.
    """

    counties = {"Adams County": False, "Denver County": True}

    def test_first_county_flagged_false_rejects_even_though_a_later_one_is_true(self):
        # 80022 resolves to ["Adams County", "Denver County"]; the loop stops at Adams
        calc = make_calculator(county=None, zipcode="80022", household_size=1, household_income=0)
        e = Eligibility()
        calc.household_eligible(e)
        self.assertFalse(e.eligible)

    def test_leading_true_county_is_eligible_on_the_same_zipcode(self):
        with patch.object(
            CoHeadStart.counties, "get_data", return_value={"Adams County": True, "Denver County": False}
        ):
            calc = make_calculator(county=None, zipcode="80022", household_size=1, household_income=0)
            e = Eligibility()
            calc.household_eligible(e)
            self.assertTrue(e.eligible)

    def test_a_county_absent_from_the_sheet_does_not_stop_the_loop(self):
        # Adams is missing from the sheet, so the loop keeps looking and finds Denver
        with patch.object(CoHeadStart.counties, "get_data", return_value={"Denver County": True}):
            calc = make_calculator(county=None, zipcode="80022", household_size=1, household_income=0)
            e = Eligibility()
            calc.household_eligible(e)
            self.assertTrue(e.eligible)


class TestCoHeadStartEmptyCountySheet(TestCase):
    """A failed sheet fetch degrades to `{}`, which makes everyone ineligible."""

    def test_empty_sheet_makes_a_participating_county_ineligible(self):
        with patch.object(CoHeadStart.counties, "get_data", return_value={}):
            calc = make_calculator(county="Denver County", household_income=0)
            e = Eligibility()
            calc.household_eligible(e)
            self.assertFalse(e.eligible)


class TestCoHeadStartIncomeEligibility(CountySheetTestCase):
    """Monthly income must be strictly below 100% FPL / 12 outside Adams County."""

    def _run(self, household_size, household_income, county="Denver County"):
        calc = make_calculator(county=county, household_size=household_size, household_income=household_income)
        e = Eligibility()
        calc.household_eligible(e)
        return e.eligible

    def test_income_well_below_the_limit_is_eligible(self):
        self.assertTrue(self._run(1, 100))

    def test_income_one_dollar_below_the_limit_is_eligible(self):
        # int(15,650 / 12) == 1,304
        self.assertTrue(self._run(1, 1_303))

    def test_income_exactly_at_the_limit_is_ineligible(self):
        # the comparison is strict `<`
        self.assertFalse(self._run(1, 1_304))

    def test_limit_scales_with_household_size(self):
        # int(32,150 / 12) == 2,679
        self.assertTrue(self._run(4, 2_678))
        self.assertFalse(self._run(4, 2_679))

    def test_zero_income_is_eligible(self):
        self.assertTrue(self._run(1, 0))

    def test_income_is_read_as_monthly_gross_of_all_types(self):
        calc = make_calculator(household_income=100)
        calc.household_eligible(Eligibility())
        calc.screen.calc_gross_income.assert_called_once_with("monthly", ["all"], exclude=["nurturingFutures"])


class TestCoHeadStartAdamsCounty(CountySheetTestCase):
    """Adams County households are measured against 130% FPL instead of 100%."""

    def _run(self, household_income, county="Adams County", household_size=1):
        calc = make_calculator(county=county, household_size=household_size, household_income=household_income)
        e = Eligibility()
        calc.household_eligible(e)
        return e.eligible

    def test_adams_income_one_dollar_below_the_raised_limit_is_eligible(self):
        # int(15,650 / 12 * 1.3) == 1,695
        self.assertTrue(self._run(1_694))

    def test_adams_income_exactly_at_the_raised_limit_is_ineligible(self):
        self.assertFalse(self._run(1_695))

    def test_income_between_the_two_limits_only_passes_in_adams(self):
        income = 1_500
        self.assertTrue(self._run(income, county="Adams County"))
        self.assertFalse(self._run(income, county="Denver County"))


class TestCoHeadStartMemberEligibility(CountySheetTestCase):
    """Ages 3 through 5."""

    def _run(self, age):
        calc = make_calculator()
        e = MemberEligibility(make_member(age=age))
        calc.member_eligible(e)
        return e.eligible

    def test_age_2_is_ineligible(self):
        self.assertFalse(self._run(2))

    def test_age_3_is_eligible(self):
        self.assertTrue(self._run(3))

    def test_age_4_is_eligible(self):
        self.assertTrue(self._run(4))

    def test_age_5_is_eligible(self):
        self.assertTrue(self._run(5))

    def test_age_6_is_ineligible(self):
        self.assertFalse(self._run(6))

    def test_adult_is_ineligible(self):
        self.assertFalse(self._run(30))


class TestCoHeadStartEligible(CountySheetTestCase):
    def test_qualifying_household_is_eligible(self):
        members = [make_member(age=30), make_member(age=4)]
        calc = make_calculator(household_size=2, household_income=500, members=members)
        self.assertTrue(calc.eligible().eligible)

    def test_household_without_a_preschooler_is_ineligible(self):
        members = [make_member(age=30), make_member(age=8)]
        calc = make_calculator(household_size=2, household_income=500, members=members)
        self.assertFalse(calc.eligible().eligible)

    def test_over_income_household_is_ineligible(self):
        members = [make_member(age=30), make_member(age=4)]
        calc = make_calculator(household_size=2, household_income=99_999, members=members)
        self.assertFalse(calc.eligible().eligible)

    def test_non_participating_county_is_ineligible(self):
        members = [make_member(age=30), make_member(age=4)]
        calc = make_calculator(county="Jefferson County", household_size=2, household_income=500, members=members)
        self.assertFalse(calc.eligible().eligible)

    def test_household_with_no_members_is_ineligible(self):
        calc = make_calculator(household_size=1, household_income=500, members=[])
        self.assertFalse(calc.eligible().eligible)


class TestCoHeadStartValue(CountySheetTestCase):
    def test_one_preschooler_is_worth_one_member_amount(self):
        members = [make_member(age=30), make_member(age=4)]
        calc = make_calculator(household_size=2, household_income=500, members=members)
        self.assertEqual(calc.calc().value, CoHeadStart.member_amount)

    def test_value_scales_with_preschoolers(self):
        members = [make_member(age=3), make_member(age=5)]
        calc = make_calculator(household_size=2, household_income=500, members=members)
        self.assertEqual(calc.calc().value, 2 * CoHeadStart.member_amount)

    def test_ineligible_members_add_no_value(self):
        members = [make_member(age=4), make_member(age=30)]
        calc = make_calculator(household_size=2, household_income=500, members=members)
        self.assertEqual(calc.calc().value, CoHeadStart.member_amount)

    def test_ineligible_household_is_worth_nothing(self):
        members = [make_member(age=4)]
        calc = make_calculator(household_size=1, household_income=99_999, members=members)
        self.assertEqual(calc.calc().value, 0)


class TestCoHeadStartCanCalc(TestCase):
    def test_can_calc_with_no_missing_dependencies(self):
        self.assertTrue(make_calculator().can_calc())

    def test_cannot_calc_without_age(self):
        self.assertFalse(make_calculator(missing_dependencies=Dependencies(["age"])).can_calc())

    def test_cannot_calc_without_zipcode(self):
        self.assertFalse(make_calculator(missing_dependencies=Dependencies(["zipcode"])).can_calc())

    def test_cannot_calc_without_income_amount(self):
        self.assertFalse(make_calculator(missing_dependencies=Dependencies(["income_amount"])).can_calc())

    def test_can_calc_with_an_unrelated_missing_dependency(self):
        self.assertTrue(make_calculator(missing_dependencies=Dependencies(["insurance"])).can_calc())

    def test_calc_raises_when_a_dependency_is_missing(self):
        calc = make_calculator(missing_dependencies=Dependencies(["age"]))
        with self.assertRaises(DependencyError):
            calc.calc()

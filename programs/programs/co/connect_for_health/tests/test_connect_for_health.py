"""
Unit tests for the ConnectForHealth (cfhc) calculator.

Eligibility requirements:
  1. Household is NOT Medicaid eligible
  2. Yearly gross household income (excluding cash assistance) below 400% FPL
  3. Member is not CHP+ eligible
  4. Member has no insurance or private insurance, and does not have VA insurance

Notes:
  - The member value is the county's average monthly premium tax credit from a Google
    Sheet, annualised. `GoogleSheetsCache.get_data()` degrades to `{}` when the sheet
    fetch fails and no stale value is cached, so a county the sheet doesn't cover is
    worth 0 and is reported to Sentry rather than raising.
  - CHP+ eligibility is read out of the sibling program's `Eligibility` in `data`, so
    members are matched by id.
  - FPL figures are imported from `FplCache.default` rather than copied, so they cannot
    drift from the table production reads. That attribute is a plain offline literal —
    `FplCache.update()` short-circuits with `return self.default` — so importing it costs
    no database or network access.
"""

from unittest.mock import Mock, patch

from django.test import SimpleTestCase, TestCase

from programs.models import FplCache
from programs.programs.calc import Eligibility, MemberEligibility, ProgramCalculator
from programs.programs.co import co_calculators
from programs.programs.co.connect_for_health.calculator import CfhCountyValuesCache, ConnectForHealth
from programs.util import Dependencies, DependencyError
from screener.models import Insurance

FPL_2025 = FplCache.default["2025"]

COUNTY_PREMIUM_TAX_CREDITS = {"Denver County": 500.0, "Jefferson County": 250.0}


def make_member(member_id=1, **insurance_flags):
    member = Mock()
    member.id = member_id
    member.insurance = Insurance(**{"none": False, **insurance_flags})
    return member


def make_data(medicaid_eligible=False, chp=None):
    data = {}

    if medicaid_eligible is not None:
        medicaid = Eligibility()
        medicaid.eligible = medicaid_eligible
        data["co_medicaid"] = medicaid

    if chp is not None:
        data["chp"] = chp

    return data


def make_chp_eligibility(member_eligibility_by_member):
    """Build the sibling CHP+ `Eligibility` that cfhc reads member results out of."""
    chp = Eligibility()
    for member, eligible in member_eligibility_by_member:
        me = MemberEligibility(member)
        me.eligible = eligible
        chp.add_member_eligibility(me)
    return chp


def make_calculator(
    household_size=1,
    household_income=0,
    medicaid_eligible=False,
    chp=None,
    county="Denver County",
    zipcode="80205",
    members=None,
    missing_dependencies=None,
):
    mock_program = Mock()
    mock_program.year.as_dict.return_value = FPL_2025

    mock_screen = Mock()
    mock_screen.household_size = household_size
    mock_screen.county = county
    mock_screen.zipcode = zipcode
    mock_screen.calc_gross_income = Mock(return_value=household_income)
    mock_screen.household_members.all.return_value = [make_member(none=True)] if members is None else members

    return ConnectForHealth(
        mock_screen,
        mock_program,
        make_data(medicaid_eligible, chp),
        Dependencies() if missing_dependencies is None else missing_dependencies,
    )


class TestConnectForHealthClassAttributes(TestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(ConnectForHealth, ProgramCalculator))

    def test_is_registered_in_co_calculators(self):
        self.assertIn("cfhc", co_calculators)
        self.assertEqual(co_calculators["cfhc"], ConnectForHealth)

    def test_percent_of_fpl_is_400_percent(self):
        self.assertEqual(ConnectForHealth.percent_of_fpl, 4)

    def test_eligible_insurance_types(self):
        self.assertEqual(ConnectForHealth.eligible_insurance_types, ["none", "private"])

    def test_ineligible_insurance_types(self):
        self.assertEqual(ConnectForHealth.ineligible_insurance_types, ["va"])

    def test_dependencies(self):
        self.assertEqual(
            ConnectForHealth.dependencies,
            ["insurance", "income_amount", "income_frequency", "zipcode", "household_size"],
        )

    def test_county_value_cache_falls_back_to_empty(self):
        self.assertEqual(ConnectForHealth.county_values._empty_fallback(), {})


class TestConnectForHealthMedicaidExclusion(TestCase):
    """Medicaid-eligible households are excluded."""

    def _run(self, medicaid_eligible):
        calc = make_calculator(medicaid_eligible=medicaid_eligible, household_income=10_000)
        e = Eligibility()
        calc.household_eligible(e)
        return e

    def test_medicaid_eligible_household_is_ineligible(self):
        self.assertFalse(self._run(True).eligible)

    def test_non_medicaid_household_is_eligible(self):
        self.assertTrue(self._run(False).eligible)

    def test_household_is_eligible_when_medicaid_was_not_calculated(self):
        self.assertTrue(self._run(None).eligible)

    def test_medicaid_eligible_household_gets_a_fail_message(self):
        e = self._run(True)
        self.assertEqual(len(e.fail_messages), 1)


class TestConnectForHealthIncomeEligibility(TestCase):
    """Yearly income must be strictly below 400% FPL, excluding cash assistance."""

    def _run(self, household_size, household_income):
        calc = make_calculator(household_size=household_size, household_income=household_income)
        e = Eligibility()
        calc.household_eligible(e)
        return e.eligible

    def test_income_well_below_the_band_is_eligible(self):
        self.assertTrue(self._run(1, 20_000))

    def test_income_one_dollar_below_the_band_is_eligible(self):
        # 15,650 * 4 == 62,600
        self.assertTrue(self._run(1, 62_599))

    def test_income_exactly_at_the_band_is_ineligible(self):
        # the comparison is strict `<`
        self.assertFalse(self._run(1, 62_600))

    def test_band_scales_with_household_size(self):
        # 32,150 * 4 == 128,600
        self.assertTrue(self._run(4, 128_599))
        self.assertFalse(self._run(4, 128_600))

    def test_zero_income_is_eligible(self):
        self.assertTrue(self._run(1, 0))

    def test_cash_assistance_is_excluded_from_income(self):
        calc = make_calculator(household_income=1_000)
        calc.household_eligible(Eligibility())
        calc.screen.calc_gross_income.assert_called_once_with("yearly", ["all"], exclude=["cashAssistance"])


class TestConnectForHealthMemberInsurance(TestCase):
    """No insurance or private insurance qualifies; VA insurance disqualifies."""

    def _run(self, **insurance_flags):
        calc = make_calculator()
        e = MemberEligibility(make_member(**insurance_flags))
        calc.member_eligible(e)
        return e.eligible

    def test_uninsured_member_is_eligible(self):
        self.assertTrue(self._run(none=True))

    def test_member_with_private_insurance_is_eligible(self):
        self.assertTrue(self._run(private=True))

    def test_member_who_does_not_know_their_insurance_is_eligible(self):
        self.assertTrue(self._run(dont_know=True))

    def test_member_with_medicaid_is_ineligible(self):
        self.assertFalse(self._run(medicaid=True))

    def test_member_with_employer_insurance_is_ineligible(self):
        self.assertFalse(self._run(employer=True))

    def test_member_with_medicare_is_ineligible(self):
        self.assertFalse(self._run(medicare=True))

    def test_member_with_va_insurance_is_ineligible(self):
        self.assertFalse(self._run(va=True))

    def test_va_insurance_overrides_an_otherwise_qualifying_type(self):
        self.assertFalse(self._run(private=True, va=True))


class TestConnectForHealthChpExclusion(TestCase):
    """Members the CHP+ calculator found eligible are excluded."""

    def _run(self, member, chp):
        calc = make_calculator(chp=chp)
        e = MemberEligibility(member)
        calc.member_eligible(e)
        return e.eligible

    def test_chp_eligible_member_is_excluded(self):
        member = make_member(member_id=1, none=True)
        chp = make_chp_eligibility([(member, True)])
        self.assertFalse(self._run(member, chp))

    def test_chp_ineligible_member_is_not_excluded(self):
        member = make_member(member_id=1, none=True)
        chp = make_chp_eligibility([(member, False)])
        self.assertTrue(self._run(member, chp))

    def test_a_different_members_chp_eligibility_is_ignored(self):
        member = make_member(member_id=1, none=True)
        sibling = make_member(member_id=2, none=True)
        chp = make_chp_eligibility([(sibling, True)])
        self.assertTrue(self._run(member, chp))

    def test_member_is_not_excluded_when_chp_was_not_calculated(self):
        member = make_member(member_id=1, none=True)
        self.assertTrue(self._run(member, None))


class TestConnectForHealthEligible(TestCase):
    def test_qualifying_household_is_eligible(self):
        calc = make_calculator(household_size=1, household_income=20_000, members=[make_member(none=True)])
        self.assertTrue(calc.eligible().eligible)

    def test_medicaid_eligible_household_is_ineligible(self):
        calc = make_calculator(
            household_size=1, household_income=20_000, medicaid_eligible=True, members=[make_member(none=True)]
        )
        self.assertFalse(calc.eligible().eligible)

    def test_over_income_household_is_ineligible(self):
        calc = make_calculator(household_size=1, household_income=999_999, members=[make_member(none=True)])
        self.assertFalse(calc.eligible().eligible)

    def test_fully_medicaid_insured_household_is_ineligible(self):
        calc = make_calculator(household_size=1, household_income=20_000, members=[make_member(medicaid=True)])
        self.assertFalse(calc.eligible().eligible)

    def test_one_qualifying_member_qualifies_the_household(self):
        members = [make_member(member_id=1, va=True), make_member(member_id=2, none=True)]
        calc = make_calculator(household_size=2, household_income=20_000, members=members)
        self.assertTrue(calc.eligible().eligible)

    def test_household_with_no_members_is_ineligible(self):
        calc = make_calculator(household_size=1, household_income=20_000, members=[])
        self.assertFalse(calc.eligible().eligible)


class TestConnectForHealthValue(TestCase):
    """Member value is the county's average monthly premium tax credit, annualised."""

    def setUp(self):
        patcher = patch.object(ConnectForHealth.county_values, "get_data", return_value=dict(COUNTY_PREMIUM_TAX_CREDITS))
        self.mock_county_values = patcher.start()
        self.addCleanup(patcher.stop)

    def test_member_value_is_the_county_credit_times_twelve(self):
        calc = make_calculator(county="Denver County")
        self.assertEqual(calc.member_value(make_member(none=True)), 6_000)

    def test_member_value_varies_by_county(self):
        calc = make_calculator(county="Jefferson County")
        self.assertEqual(calc.member_value(make_member(none=True)), 3_000)

    def test_eligible_household_value_is_per_member(self):
        members = [make_member(member_id=1, none=True), make_member(member_id=2, private=True)]
        calc = make_calculator(household_size=2, household_income=20_000, members=members)
        self.assertEqual(calc.calc().value, 12_000)

    def test_ineligible_members_add_no_value(self):
        members = [make_member(member_id=1, none=True), make_member(member_id=2, medicaid=True)]
        calc = make_calculator(household_size=2, household_income=20_000, members=members)
        self.assertEqual(calc.calc().value, 6_000)

    def test_ineligible_household_is_worth_nothing(self):
        calc = make_calculator(household_size=1, household_income=999_999, members=[make_member(none=True)])
        self.assertEqual(calc.calc().value, 0)

    @patch("programs.programs.co.connect_for_health.calculator.capture_message")
    def test_county_missing_from_the_sheet_is_worth_nothing(self, _capture):
        calc = make_calculator(county="Pueblo County")
        self.assertEqual(calc.member_value(make_member(none=True)), 0)

    @patch("programs.programs.co.connect_for_health.calculator.capture_message")
    def test_county_missing_from_the_sheet_is_reported(self, capture):
        # a $0 value is dropped by the frontend's `value > 0` check, so the program
        # silently vanishes from results unless the miss is reported
        calc = make_calculator(county="Pueblo County")
        calc.member_value(make_member(none=True))

        capture.assert_called_once()
        self.assertIn("Pueblo County", capture.call_args.args[0])

    @patch("programs.programs.co.connect_for_health.calculator.capture_message")
    def test_a_covered_county_reports_nothing(self, capture):
        calc = make_calculator(county="Denver County")
        calc.member_value(make_member(none=True))

        self.assertFalse(capture.called)


class TestConnectForHealthEmptyCountyValueSheet(TestCase):
    """A failed sheet fetch with no stale value degrades to `{}`, so every county misses."""

    def setUp(self):
        patcher = patch.object(ConnectForHealth.county_values, "get_data", return_value={})
        patcher.start()
        self.addCleanup(patcher.stop)

    @patch("programs.programs.co.connect_for_health.calculator.capture_message")
    def test_empty_sheet_makes_member_value_zero(self, _capture):
        calc = make_calculator(county="Denver County")
        self.assertEqual(calc.member_value(make_member(none=True)), 0)

    @patch("programs.programs.co.connect_for_health.calculator.capture_message")
    def test_empty_sheet_is_reported(self, capture):
        calc = make_calculator(county="Denver County")
        calc.member_value(make_member(none=True))

        capture.assert_called_once()


class TestCfhCountyValuesCacheProcess(SimpleTestCase):
    """Row parsing: the county key gains a " County" suffix and bad rows are skipped."""

    def setUp(self):
        self.cache = CfhCountyValuesCache()

    def _row(self, county, average):
        return {
            CfhCountyValuesCache._COUNTY_COLUMN: county,
            CfhCountyValuesCache._AVERAGE_COLUMN: average,
        }

    def test_parses_county_rows(self):
        self.assertEqual(self.cache._process([self._row("Denver", "123.45")]), {"Denver County": 123.45})

    def test_skips_unparseable_values(self):
        self.assertEqual(self.cache._process([self._row("Denver", "n/a")]), {})

    def test_keeps_good_rows_alongside_bad(self):
        rows = [self._row("Denver", "n/a"), self._row("Boulder", "50")]

        self.assertEqual(self.cache._process(rows), {"Boulder County": 50.0})


class TestConnectForHealthCanCalc(TestCase):
    def test_can_calc_with_no_missing_dependencies(self):
        self.assertTrue(make_calculator().can_calc())

    def test_cannot_calc_without_insurance(self):
        self.assertFalse(make_calculator(missing_dependencies=Dependencies(["insurance"])).can_calc())

    def test_cannot_calc_without_zipcode(self):
        self.assertFalse(make_calculator(missing_dependencies=Dependencies(["zipcode"])).can_calc())

    def test_can_calc_with_an_unrelated_missing_dependency(self):
        self.assertTrue(make_calculator(missing_dependencies=Dependencies(["age"])).can_calc())

    def test_calc_raises_when_a_dependency_is_missing(self):
        calc = make_calculator(missing_dependencies=Dependencies(["insurance"]))
        with self.assertRaises(DependencyError):
            calc.calc()

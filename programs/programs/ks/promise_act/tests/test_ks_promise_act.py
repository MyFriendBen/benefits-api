"""
Unit tests for KsPromiseAct calculator.

Eligibility (only screenable criterion):
- Household gross income at or below a size-tiered limit (K.S.A. 74-32,274):
    * family of 1-2: $100,000
    * family of 3:   $150,000
    * family of 4+:  $150,000 + $4,800 per member beyond 3
- Kansas residency, US citizenship, qualifying educational history, and eligible
  institution enrollment are NOT tested here (white-label routing, config-level
  legal_status_required, and inclusivity assumptions for the two data gaps).

Benefit value:
- Fixed $3,960/year estimated benefit for every eligible household.

Test scenarios mirror the spec's Acceptance Criteria / Test Scenarios (1-7).
"""

from django.test import TestCase
from unittest.mock import Mock

from programs.programs.ks import ks_calculators
from programs.programs.ks.promise_act.calculator import KsPromiseAct
from programs.programs.calc import ProgramCalculator, Eligibility


def make_calculator(income=45_000, household_size=1, members=None):
    if members is None:
        members = [Mock()]

    mock_screen = Mock()
    mock_screen.calc_gross_income = Mock(return_value=income)
    mock_screen.household_size = household_size
    mock_screen.household_members.all = Mock(return_value=members)

    mock_program = Mock()
    mock_missing_deps = Mock()
    mock_missing_deps.has.return_value = False

    return KsPromiseAct(mock_screen, mock_program, {}, mock_missing_deps)


def run_household_eligible(calc):
    e = Eligibility()
    calc.household_eligible(e)
    return e.eligible


class TestKsPromiseActClassAttributes(TestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(KsPromiseAct, ProgramCalculator))

    def test_is_registered_in_ks_calculators(self):
        self.assertIn("ks_promise_act", ks_calculators)
        self.assertEqual(ks_calculators["ks_promise_act"], KsPromiseAct)

    def test_amount_is_3960(self):
        self.assertEqual(KsPromiseAct.amount, 3_960)

    def test_income_limit_constants(self):
        self.assertEqual(KsPromiseAct.small_household_limit, 100_000)
        self.assertEqual(KsPromiseAct.base_household_limit, 150_000)
        self.assertEqual(KsPromiseAct.per_member_addition, 4_800)

    def test_income_fields_in_dependencies(self):
        self.assertIn("income_amount", KsPromiseAct.dependencies)
        self.assertIn("income_frequency", KsPromiseAct.dependencies)
        self.assertIn("household_size", KsPromiseAct.dependencies)


class TestKsPromiseActIncomeLimit(TestCase):
    def test_size_1_limit_is_100k(self):
        self.assertEqual(make_calculator(household_size=1)._income_limit(), 100_000)

    def test_size_2_limit_is_100k(self):
        self.assertEqual(make_calculator(household_size=2)._income_limit(), 100_000)

    def test_size_3_limit_is_150k(self):
        self.assertEqual(make_calculator(household_size=3)._income_limit(), 150_000)

    def test_size_4_limit_is_154800(self):
        self.assertEqual(make_calculator(household_size=4)._income_limit(), 154_800)

    def test_size_5_limit_is_159600(self):
        self.assertEqual(make_calculator(household_size=5)._income_limit(), 159_600)

    def test_none_household_size_defaults_to_smallest_limit(self):
        self.assertEqual(make_calculator(household_size=None)._income_limit(), 100_000)


class TestKsPromiseActEligibility(TestCase):
    # Scenario 1: Clearly eligible golden path.
    def test_scenario_1_single_low_income_eligible(self):
        calc = make_calculator(income=45_000, household_size=1)
        self.assertTrue(run_household_eligible(calc))

    # Scenario 2: 1-person household at the $100,000 limit (inclusive boundary).
    def test_scenario_2_single_at_limit_eligible(self):
        calc = make_calculator(income=99_996, household_size=1)
        self.assertTrue(run_household_eligible(calc))

    def test_single_exactly_at_100k_eligible(self):
        calc = make_calculator(income=100_000, household_size=1)
        self.assertTrue(run_household_eligible(calc))

    # Scenario 3: 1-person household just over the $100,000 limit.
    def test_scenario_3_single_over_limit_ineligible(self):
        calc = make_calculator(income=100_008, household_size=1)
        self.assertFalse(run_household_eligible(calc))

    def test_single_one_dollar_over_100k_ineligible(self):
        calc = make_calculator(income=100_001, household_size=1)
        self.assertFalse(run_household_eligible(calc))

    # Scenario 4: 3-person household at the $150,000 limit.
    def test_scenario_4_three_person_at_limit_eligible(self):
        calc = make_calculator(income=149_988, household_size=3)
        self.assertTrue(run_household_eligible(calc))

    def test_three_person_exactly_at_150k_eligible(self):
        calc = make_calculator(income=150_000, household_size=3)
        self.assertTrue(run_household_eligible(calc))

    # Scenario 5: 3-person household just over the $150,000 limit.
    def test_scenario_5_three_person_over_limit_ineligible(self):
        calc = make_calculator(income=150_012, household_size=3)
        self.assertFalse(run_household_eligible(calc))

    # Scenario 6: 4-person household at the extended formula limit ($154,800).
    def test_scenario_6_four_person_at_extended_limit_eligible(self):
        calc = make_calculator(income=154_788, household_size=4)
        self.assertTrue(run_household_eligible(calc))

    def test_four_person_exactly_at_154800_eligible(self):
        calc = make_calculator(income=154_800, household_size=4)
        self.assertTrue(run_household_eligible(calc))

    # Scenario 7: 4-person household just over the extended formula limit.
    def test_scenario_7_four_person_over_extended_limit_ineligible(self):
        calc = make_calculator(income=154_812, household_size=4)
        self.assertFalse(run_household_eligible(calc))

    def test_three_person_at_100k_still_eligible(self):
        # A developer who hardcodes $100k as a flat cap would wrongly fail this.
        calc = make_calculator(income=120_000, household_size=3)
        self.assertTrue(run_household_eligible(calc))


class TestKsPromiseActValue(TestCase):
    def test_household_value_is_3960(self):
        self.assertEqual(make_calculator().household_value(), 3_960)


class TestKsPromiseActCalc(TestCase):
    def test_calc_eligible_returns_3960(self):
        calc = make_calculator(income=45_000, household_size=1)
        e = calc.calc()
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 3_960)

    def test_calc_ineligible_over_income(self):
        calc = make_calculator(income=100_008, household_size=1)
        e = calc.calc()
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)

    def test_calc_eligible_three_person_at_limit(self):
        members = [Mock(), Mock(), Mock()]
        calc = make_calculator(income=150_000, household_size=3, members=members)
        e = calc.calc()
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 3_960)

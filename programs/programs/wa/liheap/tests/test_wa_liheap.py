from django.test import TestCase
from unittest.mock import Mock

from programs.programs.wa import wa_calculators
from programs.programs.wa.liheap.calculator import WaLiheap
from programs.programs.calc import ProgramCalculator, Eligibility


def make_calculator(household_income=0, household_size=1, fpl_limit=15650, heating_expense=0):
    mock_program = Mock()
    mock_program.year.get_limit.return_value = fpl_limit

    mock_screen = Mock()
    mock_screen.household_size = household_size
    mock_screen.calc_gross_income = Mock(return_value=household_income)
    mock_screen.calc_expenses = Mock(return_value=heating_expense)
    mock_screen.household_members.all.return_value = [Mock(age=40)]

    mock_missing_deps = Mock()
    mock_missing_deps.has.return_value = False

    return WaLiheap(mock_screen, mock_program, {}, mock_missing_deps)


class TestWaLiheapClassAttributes(TestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(WaLiheap, ProgramCalculator))

    def test_is_registered_in_wa_calculators(self):
        self.assertIn("wa_liheap", wa_calculators)
        self.assertEqual(wa_calculators["wa_liheap"], WaLiheap)

    def test_fpl_percent_is_150(self):
        self.assertEqual(WaLiheap.fpl_percent, 1.5)

    def test_min_benefit_is_250(self):
        self.assertEqual(WaLiheap.min_benefit, 250)

    def test_max_benefit_is_1250(self):
        self.assertEqual(WaLiheap.max_benefit, 1_250)


class TestWaLiheapHouseholdEligibility(TestCase):
    def _run(self, household_income, fpl_limit=15650, household_size=1):
        calc = make_calculator(household_income=household_income, fpl_limit=fpl_limit, household_size=household_size)
        e = Eligibility()
        calc.household_eligible(e)
        return e.eligible

    def test_income_below_150_fpl_is_eligible(self):
        # 150% of 15650 = 23475; income 20000 < 23475
        self.assertTrue(self._run(household_income=20000, fpl_limit=15650))

    def test_income_exactly_at_150_fpl_is_eligible(self):
        # 150% of 15650 = 23475
        self.assertTrue(self._run(household_income=23475, fpl_limit=15650))

    def test_income_above_150_fpl_is_ineligible(self):
        self.assertFalse(self._run(household_income=23476, fpl_limit=15650))

    def test_zero_income_is_eligible(self):
        self.assertTrue(self._run(household_income=0))

    def test_income_message_included(self):
        calc = make_calculator(household_income=20000, fpl_limit=15650)
        e = Eligibility()
        calc.household_eligible(e)
        self.assertTrue(len(e.pass_messages) > 0)

    def test_income_fail_message_included(self):
        calc = make_calculator(household_income=30000, fpl_limit=15650)
        e = Eligibility()
        calc.household_eligible(e)
        self.assertTrue(len(e.fail_messages) > 0)


class TestWaLiheapNoCategoricalEligibility(TestCase):
    """WA LIHEAP does not implement categorical eligibility — income test always applies."""

    def test_high_income_is_ineligible_regardless(self):
        calc = make_calculator(household_income=99999, fpl_limit=15650)
        e = Eligibility()
        calc.household_eligible(e)
        self.assertFalse(e.eligible)


class TestWaLiheapBenefitValue(TestCase):
    def test_scenario_1_elderly_couple(self):
        # Income $19,200/yr, FPL for HH2 = $21,150, heating $1,800/yr
        # income_pct_fpl = (19200/21150)*100 = 90.78
        # benefit_pct = 0.90 - (90.78/125)*0.40 = 0.6095
        # benefit = 0.6095 * 1800 = 1097
        calc = make_calculator(
            household_income=19200,
            household_size=2,
            fpl_limit=21150,
            heating_expense=1800,
        )
        self.assertEqual(calc.household_value(), 1097)

    def test_scenario_3_large_household_capped_at_max(self):
        # Income $44,316/yr, FPL for HH6 = $43,150, heating $2,400/yr
        # income_pct_fpl = (44316/43150)*100 = 102.70
        # benefit_pct = 0.90 - (102.70/125)*0.40 = 0.5714
        # benefit = 0.5714 * 2400 = 1371, capped at 1250
        calc = make_calculator(
            household_income=44316,
            household_size=6,
            fpl_limit=43150,
            heating_expense=2400,
        )
        self.assertEqual(calc.household_value(), 1250)

    def test_zero_income_gets_90_percent_of_heat_cost(self):
        # At 0% FPL: benefit_pct = 0.90, benefit = 0.90 * 1000 = 900
        calc = make_calculator(
            household_income=0,
            fpl_limit=15650,
            heating_expense=1000,
        )
        self.assertEqual(calc.household_value(), 900)

    def test_benefit_clamped_to_minimum_250(self):
        # Very low heat cost: benefit would be below $250 → clamped to $250
        calc = make_calculator(
            household_income=10000,
            fpl_limit=15650,
            heating_expense=100,
        )
        self.assertEqual(calc.household_value(), 250)

    def test_benefit_clamped_to_maximum_1250(self):
        # Very high heat cost: benefit would exceed $1,250 → clamped to $1,250
        calc = make_calculator(
            household_income=0,
            fpl_limit=15650,
            heating_expense=5000,
        )
        # 0.90 * 5000 = 4500, clamped to 1250
        self.assertEqual(calc.household_value(), 1250)

    def test_no_heating_expense_gets_minimum(self):
        calc = make_calculator(
            household_income=10000,
            fpl_limit=15650,
            heating_expense=0,
        )
        self.assertEqual(calc.household_value(), 250)

    def test_income_at_125_pct_fpl_gets_50_percent(self):
        # At exactly 125% FPL: benefit_pct = 0.90 - (125/125)*0.40 = 0.50
        fpl = 15650
        income = int(fpl * 1.25)  # 19562
        calc = make_calculator(
            household_income=income,
            fpl_limit=fpl,
            heating_expense=2000,
        )
        # 0.50 * 2000 = 1000
        self.assertEqual(calc.household_value(), 1000)


class TestWaLiheapEndToEnd(TestCase):
    def test_eligible_household_gets_value(self):
        calc = make_calculator(
            household_income=19200,
            household_size=2,
            fpl_limit=21150,
            heating_expense=1800,
        )
        result = calc.calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 1097)

    def test_ineligible_household_gets_zero(self):
        calc = make_calculator(
            household_income=30000,
            fpl_limit=15650,
        )
        result = calc.calc()
        self.assertFalse(result.eligible)
        self.assertEqual(result.value, 0)

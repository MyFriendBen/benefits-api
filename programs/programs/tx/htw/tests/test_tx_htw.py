"""
Unit tests for TxHtw calculator class.

Eligibility requirements:
- Age 15-44
- Not pregnant
- Not enrolled in Medicaid or CHIP
- No other health insurance (Medicare, employer, private, or VA)
- Household income <= 204.2% FPL
"""

from django.test import TestCase
from unittest.mock import Mock

from programs.programs.tx import tx_calculators
from programs.programs.tx.htw.calculator import TxHtw
from programs.programs.calc import ProgramCalculator, Eligibility, MemberEligibility


def make_member(
    age=28,
    pregnant=False,
    has_medicaid=False,
    has_chp=False,
    has_medicare=False,
    has_employer=False,
    has_private=False,
    has_va=False,
):
    """Create a mock household member."""
    member = Mock()
    member.age = age
    member.pregnant = pregnant

    insurance_map = {
        "medicaid": has_medicaid,
        "chp": has_chp,
        "medicare": has_medicare,
        "employer": has_employer,
        "private": has_private,
        "va": has_va,
    }

    def has_insurance_types(types, strict=True):
        return any(insurance_map.get(t, False) for t in types)

    member.insurance = Mock()
    member.insurance.has_insurance_types = Mock(side_effect=has_insurance_types)
    return member


def make_calculator(household_income=0, household_size=1, fpl_limit=15_000):
    """Create a TxHtw calculator with a mocked screen and program."""
    mock_program = Mock()
    mock_program.year.get_limit.return_value = fpl_limit

    mock_screen = Mock()
    mock_screen.household_size = household_size
    mock_screen.calc_gross_income = Mock(return_value=household_income)
    mock_screen.household_members.all = Mock(return_value=[])

    mock_missing_deps = Mock()
    mock_missing_deps.has.return_value = False

    return TxHtw(mock_screen, mock_program, {}, mock_missing_deps)


class TestTxHtwClassAttributes(TestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(TxHtw, ProgramCalculator))

    def test_is_registered_in_tx_calculators(self):
        self.assertIn("tx_htw", tx_calculators)
        self.assertEqual(tx_calculators["tx_htw"], TxHtw)

    def test_fpl_percent_is_2042(self):
        self.assertEqual(TxHtw.fpl_percent, 2.042)

    def test_min_age_is_15(self):
        self.assertEqual(TxHtw.min_age, 15)

    def test_max_age_is_44(self):
        self.assertEqual(TxHtw.max_age, 44)

    def test_amount_defaults_to_zero(self):
        self.assertEqual(TxHtw.amount, 0)


class TestTxHtwMemberAgeEligibility(TestCase):
    """Age must be 15-44."""

    def _run(self, age):
        calc = make_calculator()
        e = MemberEligibility(make_member(age=age))
        calc.member_eligible(e)
        return e.eligible

    def test_age_28_is_eligible(self):
        self.assertTrue(self._run(28))

    def test_age_15_is_eligible(self):
        self.assertTrue(self._run(15))

    def test_age_44_is_eligible(self):
        self.assertTrue(self._run(44))

    def test_age_14_is_ineligible(self):
        self.assertFalse(self._run(14))

    def test_age_45_is_ineligible(self):
        self.assertFalse(self._run(45))

    def test_age_none_is_ineligible(self):
        self.assertFalse(self._run(None))


class TestTxHtwMemberPregnancyEligibility(TestCase):
    """Pregnant members are excluded from HTW."""

    def _run(self, pregnant):
        calc = make_calculator()
        e = MemberEligibility(make_member(pregnant=pregnant))
        calc.member_eligible(e)
        return e.eligible

    def test_not_pregnant_is_eligible(self):
        self.assertTrue(self._run(False))

    def test_pregnant_is_ineligible(self):
        self.assertFalse(self._run(True))


class TestTxHtwMemberInsuranceEligibility(TestCase):
    """Members with Medicaid, CHIP, Medicare, employer, private, or VA insurance are excluded."""

    def _run(self, **kwargs):
        calc = make_calculator()
        e = MemberEligibility(make_member(**kwargs))
        calc.member_eligible(e)
        return e.eligible

    def test_no_insurance_is_eligible(self):
        self.assertTrue(self._run())

    def test_medicaid_is_ineligible(self):
        self.assertFalse(self._run(has_medicaid=True))

    def test_chp_is_ineligible(self):
        self.assertFalse(self._run(has_chp=True))

    def test_medicare_is_ineligible(self):
        self.assertFalse(self._run(has_medicare=True))

    def test_employer_insurance_is_ineligible(self):
        self.assertFalse(self._run(has_employer=True))

    def test_private_insurance_is_ineligible(self):
        self.assertFalse(self._run(has_private=True))

    def test_va_coverage_is_ineligible(self):
        self.assertFalse(self._run(has_va=True))


class TestTxHtwHouseholdIncomeEligibility(TestCase):
    """Household income must be at or below 204.2% FPL."""

    def _run(self, household_income, fpl_limit=15_000):
        # fpl_percent=2.042, so income_limit = 2.042 * fpl_limit
        calc = make_calculator(household_income=household_income, fpl_limit=fpl_limit)
        e = Eligibility()
        calc.household_eligible(e)
        return e.eligible

    def test_income_below_fpl_limit_is_eligible(self):
        # limit = 2.042 * 15_000 = 30_630; income = 20_000 < 30_630
        self.assertTrue(self._run(household_income=20_000, fpl_limit=15_000))

    def test_income_exactly_at_fpl_limit_is_eligible(self):
        fpl_limit = 15_000
        income_limit = int(TxHtw.fpl_percent * fpl_limit)
        self.assertTrue(self._run(household_income=income_limit, fpl_limit=fpl_limit))

    def test_income_above_fpl_limit_is_ineligible(self):
        # limit = 2.042 * 15_000 = 30_630; income = 30_631 > 30_630
        self.assertFalse(self._run(household_income=30_631, fpl_limit=15_000))

    def test_zero_income_is_eligible(self):
        self.assertTrue(self._run(household_income=0))


class TestTxHtwCalcIntegration(TestCase):
    """End-to-end calc() tests using the full eligible() + value() flow."""

    def _make_calc_with_members(self, members, household_income=20_000, fpl_limit=15_000):
        calc = make_calculator(household_income=household_income, fpl_limit=fpl_limit)
        calc.screen.household_members.all = Mock(return_value=members)
        return calc

    def test_eligible_single_member(self):
        member = make_member(age=28)
        calc = self._make_calc_with_members([member])
        result = calc.calc()
        self.assertTrue(result.eligible)

    def test_ineligible_due_to_age(self):
        member = make_member(age=14)
        calc = self._make_calc_with_members([member])
        result = calc.calc()
        self.assertFalse(result.eligible)

    def test_ineligible_due_to_income(self):
        # income = 50_000, limit = 2.042 * 15_000 = 30_630
        member = make_member(age=28)
        calc = self._make_calc_with_members([member], household_income=50_000)
        result = calc.calc()
        self.assertFalse(result.eligible)

    def test_ineligible_due_to_medicaid(self):
        member = make_member(age=28, has_medicaid=True)
        calc = self._make_calc_with_members([member])
        result = calc.calc()
        self.assertFalse(result.eligible)

    def test_ineligible_due_to_pregnancy(self):
        member = make_member(age=28, pregnant=True)
        calc = self._make_calc_with_members([member])
        result = calc.calc()
        self.assertFalse(result.eligible)

    def test_mixed_household_eligible_member_present(self):
        """Eligible adult + child (age 6) below minimum age — household is still eligible."""
        adult = make_member(age=32)
        child = make_member(age=6)
        calc = self._make_calc_with_members([adult, child], household_income=32_400)
        # fpl_limit for size=1 in make_calculator; override manually
        calc.screen.household_size = 3
        calc.program.year.get_limit.return_value = 27_300  # ~$4,649/mo * 12 / 2.042 ≈ 27,300
        result = calc.calc()
        self.assertTrue(result.eligible)

    def test_value_is_zero(self):
        member = make_member(age=28)
        calc = self._make_calc_with_members([member])
        result = calc.calc()
        self.assertEqual(result.value, 0)

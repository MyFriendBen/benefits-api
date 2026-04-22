"""
Unit tests for TxHse calculator.

Eligibility:
- Household must have a mortgage expense
- Texas residency is handled by the TX white label (not tested here)

Benefit value:
- $600 if any household member is age 65+ or has a disability
- $400 otherwise
"""

from django.test import TestCase
from unittest.mock import Mock

from programs.programs.tx import tx_calculators
from programs.programs.tx.hse.calculator import TxHse
from programs.programs.calc import ProgramCalculator, Eligibility


def make_member(age: int | None = 40, disabled=False, visually_impaired=False, long_term_disability=False):
    member = Mock()
    member.age = age
    member.disabled = disabled
    member.visually_impaired = visually_impaired
    member.long_term_disability = long_term_disability
    member.has_disability = Mock(return_value=(disabled or visually_impaired or long_term_disability))
    return member


def make_calculator(has_mortgage=True, members=None):
    if members is None:
        members = [make_member()]

    mock_screen = Mock()
    mock_screen.has_expense = Mock(return_value=has_mortgage)
    mock_screen.household_members.all = Mock(return_value=members)

    mock_program = Mock()
    mock_missing_deps = Mock()
    mock_missing_deps.has.return_value = False

    return TxHse(mock_screen, mock_program, {}, mock_missing_deps)


def run_household_eligible(calc):
    e = Eligibility()
    calc.household_eligible(e)
    return e.eligible


class TestTxHseClassAttributes(TestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(TxHse, ProgramCalculator))

    def test_is_registered_in_tx_calculators(self):
        self.assertIn("tx_hse", tx_calculators)
        self.assertEqual(tx_calculators["tx_hse"], TxHse)

    def test_base_amount_is_400(self):
        self.assertEqual(TxHse.amount, 400)

    def test_senior_disabled_amount_is_600(self):
        self.assertEqual(TxHse.senior_disabled_amount, 600)

    def test_senior_age_is_65(self):
        self.assertEqual(TxHse.senior_age, 65)

    def test_age_in_dependencies(self):
        self.assertIn("age", TxHse.dependencies)


class TestTxHseEligibility(TestCase):
    def test_homeowner_with_mortgage_is_eligible(self):
        calc = make_calculator(has_mortgage=True)
        self.assertTrue(run_household_eligible(calc))

    def test_no_mortgage_is_ineligible(self):
        calc = make_calculator(has_mortgage=False)
        self.assertFalse(run_household_eligible(calc))


class TestTxHseValue(TestCase):
    def test_non_senior_non_disabled_gets_400(self):
        members = [make_member(age=40)]
        calc = make_calculator(members=members)
        self.assertEqual(calc.household_value(), 400)

    def test_member_age_65_gets_600(self):
        members = [make_member(age=65)]
        calc = make_calculator(members=members)
        self.assertEqual(calc.household_value(), 600)

    def test_member_age_80_gets_600(self):
        members = [make_member(age=80)]
        calc = make_calculator(members=members)
        self.assertEqual(calc.household_value(), 600)

    def test_member_age_64_gets_400(self):
        members = [make_member(age=64)]
        calc = make_calculator(members=members)
        self.assertEqual(calc.household_value(), 400)

    def test_disabled_member_gets_600(self):
        members = [make_member(age=40, disabled=True)]
        calc = make_calculator(members=members)
        self.assertEqual(calc.household_value(), 600)

    def test_visually_impaired_member_gets_600(self):
        members = [make_member(age=40, visually_impaired=True)]
        calc = make_calculator(members=members)
        self.assertEqual(calc.household_value(), 600)

    def test_long_term_disability_gets_600(self):
        members = [make_member(age=40, long_term_disability=True)]
        calc = make_calculator(members=members)
        self.assertEqual(calc.household_value(), 600)

    def test_mixed_household_with_senior_gets_600(self):
        members = [make_member(age=40), make_member(age=70)]
        calc = make_calculator(members=members)
        self.assertEqual(calc.household_value(), 600)

    def test_mixed_household_no_senior_no_disability_gets_400(self):
        members = [make_member(age=30), make_member(age=50)]
        calc = make_calculator(members=members)
        self.assertEqual(calc.household_value(), 400)

    def test_zero_member_household_gets_400(self):
        calc = make_calculator(members=[])
        self.assertEqual(calc.household_value(), 400)

    def test_member_with_none_age_does_not_raise(self):
        members = [make_member(age=None)]
        calc = make_calculator(members=members)
        self.assertEqual(calc.household_value(), 400)

    def test_senior_and_disabled_member_gets_600(self):
        members = [make_member(age=70, disabled=True)]
        calc = make_calculator(members=members)
        self.assertEqual(calc.household_value(), 600)


class TestTxHseCalc(TestCase):
    def test_calc_eligible_with_mortgage(self):
        calc = make_calculator(has_mortgage=True, members=[make_member(age=40)])
        e = calc.calc()
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 400)

    def test_calc_ineligible_without_mortgage(self):
        calc = make_calculator(has_mortgage=False, members=[make_member(age=40)])
        e = calc.calc()
        self.assertFalse(e.eligible)

    def test_calc_eligible_senior_gets_600(self):
        calc = make_calculator(has_mortgage=True, members=[make_member(age=65)])
        e = calc.calc()
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 600)

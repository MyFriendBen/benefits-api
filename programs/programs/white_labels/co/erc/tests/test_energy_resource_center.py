"""
Unit tests for the EnergyResourceCenter (erc) calculator.

Eligibility requirements:
  1. Monthly gross household income at or below a fixed band for the household size

Notes:
  - There is no member-level gate, so every member passes `member_eligible`. A household
    still needs at least one member for `eligible()` to succeed.
  - The benefit is a flat household amount, not a per-member amount.
"""

from unittest.mock import Mock

from django.test import TestCase

from programs.framework.base import Eligibility, MemberEligibility, ProgramCalculator
from programs.programs.white_labels.co.erc.calculator import EnergyResourceCenter
from programs.util import Dependencies, DependencyError
from programs.framework.pe_dependencies import member


def make_member(age=30):
    member = Mock()
    member.age = age
    return member


def make_calculator(household_size=1, household_income=0, members=None, missing_dependencies=None):
    mock_screen = Mock()
    mock_screen.household_size = household_size
    mock_screen.calc_gross_income = Mock(return_value=household_income)
    mock_screen.household_members.all.return_value = [make_member()] if members is None else members

    return EnergyResourceCenter(
        mock_screen,
        Mock(),
        {},
        Dependencies() if missing_dependencies is None else missing_dependencies,
    )


class TestEnergyResourceCenterClassAttributes(TestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(EnergyResourceCenter, ProgramCalculator))

    def test_amount_is_4000(self):
        self.assertEqual(EnergyResourceCenter.amount, 4000)

    def test_no_member_amount(self):
        self.assertEqual(EnergyResourceCenter.member_amount, 0)

    def test_income_bands(self):
        self.assertEqual(
            EnergyResourceCenter.income_bands,
            {1: 2880, 2: 3766, 3: 4652, 4: 5539, 5: 6425, 6: 7311, 7: 7477, 8: 7644},
        )

    def test_dependencies(self):
        self.assertEqual(
            EnergyResourceCenter.dependencies,
            ["household_size", "income_amount", "income_frequency"],
        )


class TestEnergyResourceCenterIncomeEligibility(TestCase):
    """Monthly income must be at or below the band for the household size."""

    def _run(self, household_size, household_income):
        calc = make_calculator(household_size=household_size, household_income=household_income)
        e = Eligibility()
        calc.household_eligible(e)
        return e.eligible

    def test_income_below_band_is_eligible_size_1(self):
        self.assertTrue(self._run(household_size=1, household_income=2000))

    def test_income_exactly_at_band_is_eligible_size_1(self):
        self.assertTrue(self._run(household_size=1, household_income=2880))

    def test_income_one_dollar_above_band_is_ineligible_size_1(self):
        self.assertFalse(self._run(household_size=1, household_income=2881))

    def test_income_exactly_at_band_is_eligible_size_4(self):
        self.assertTrue(self._run(household_size=4, household_income=5539))

    def test_income_one_dollar_above_band_is_ineligible_size_4(self):
        self.assertFalse(self._run(household_size=4, household_income=5540))

    def test_income_exactly_at_band_is_eligible_size_8(self):
        self.assertTrue(self._run(household_size=8, household_income=7644))

    def test_income_one_dollar_above_band_is_ineligible_size_8(self):
        self.assertFalse(self._run(household_size=8, household_income=7645))

    def test_zero_income_is_eligible(self):
        self.assertTrue(self._run(household_size=1, household_income=0))

    def test_income_is_read_as_monthly_gross_of_all_types(self):
        calc = make_calculator(household_size=1, household_income=1000)
        calc.household_eligible(Eligibility())
        calc.screen.calc_gross_income.assert_called_once_with("monthly", ["all"])

    def test_failing_income_adds_a_fail_message(self):
        calc = make_calculator(household_size=1, household_income=5000)
        e = Eligibility()
        calc.household_eligible(e)
        self.assertEqual(len(e.fail_messages), 1)
        self.assertEqual(len(e.pass_messages), 0)


class TestEnergyResourceCenterMemberEligibility(TestCase):
    """There is no member-level gate: every member passes."""

    def _run(self, member):
        calc = make_calculator()
        e = MemberEligibility(member)
        calc.member_eligible(e)
        return e.eligible

    def test_child_is_eligible(self):
        self.assertTrue(self._run(make_member(age=2)))

    def test_adult_is_eligible(self):
        self.assertTrue(self._run(make_member(age=40)))

    def test_senior_is_eligible(self):
        self.assertTrue(self._run(make_member(age=80)))


class TestEnergyResourceCenterEligible(TestCase):
    """`eligible()` combines the member loop with the household income test."""

    def test_household_with_one_member_and_qualifying_income_is_eligible(self):
        calc = make_calculator(household_size=1, household_income=1000, members=[make_member()])
        self.assertTrue(calc.eligible().eligible)

    def test_household_with_no_members_is_ineligible(self):
        calc = make_calculator(household_size=1, household_income=1000, members=[])
        self.assertFalse(calc.eligible().eligible)

    def test_household_over_income_is_ineligible(self):
        calc = make_calculator(household_size=1, household_income=9999, members=[make_member()])
        self.assertFalse(calc.eligible().eligible)

    def test_every_member_is_recorded_on_the_eligibility(self):
        members = [make_member(age=30), make_member(age=5)]
        calc = make_calculator(household_size=2, household_income=1000, members=members)
        self.assertEqual(len(calc.eligible().eligible_members), 2)


class TestEnergyResourceCenterValue(TestCase):
    def test_eligible_household_is_worth_4000(self):
        calc = make_calculator(household_size=1, household_income=1000)
        e = calc.calc()
        self.assertEqual(e.household_value, 4000)
        self.assertEqual(e.value, 4000)

    def test_members_carry_no_value(self):
        members = [make_member(age=30), make_member(age=5)]
        calc = make_calculator(household_size=2, household_income=1000, members=members)
        e = calc.calc()
        self.assertTrue(all(me.value == 0 for me in e.eligible_members))

    def test_ineligible_household_is_worth_nothing(self):
        calc = make_calculator(household_size=1, household_income=9999)
        e = calc.calc()
        self.assertEqual(e.value, 0)


class TestEnergyResourceCenterCanCalc(TestCase):
    def test_can_calc_with_no_missing_dependencies(self):
        self.assertTrue(make_calculator().can_calc())

    def test_cannot_calc_without_income_amount(self):
        calc = make_calculator(missing_dependencies=Dependencies(["income_amount"]))
        self.assertFalse(calc.can_calc())

    def test_cannot_calc_without_household_size(self):
        calc = make_calculator(missing_dependencies=Dependencies(["household_size"]))
        self.assertFalse(calc.can_calc())

    def test_can_calc_with_an_unrelated_missing_dependency(self):
        calc = make_calculator(missing_dependencies=Dependencies(["zipcode"]))
        self.assertTrue(calc.can_calc())

    def test_calc_raises_when_a_dependency_is_missing(self):
        calc = make_calculator(missing_dependencies=Dependencies(["income_amount"]))
        with self.assertRaises(DependencyError):
            calc.calc()

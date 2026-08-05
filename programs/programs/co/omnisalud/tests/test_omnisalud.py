"""
Unit tests for the OmniSalud calculator.

Eligibility requirements:
  1. Yearly gross household income at or below 150% FPL
  2. Member has no health insurance

Notes:
  - "age" is declared as a dependency but there is no age gate in `member_eligible`;
    that is asserted below so a future age rule doesn't land silently.
  - FPL figures used here are the real 2025 guidelines from `FplCache.default`.
"""

from unittest.mock import Mock

from django.test import TestCase

from programs.programs.calc import Eligibility, MemberEligibility, ProgramCalculator
from programs.programs.co import co_calculators
from programs.programs.co.omnisalud.calculator import OmniSalud
from programs.util import Dependencies, DependencyError
from screener.models import Insurance

FPL_2025 = {1: 15_650, 2: 21_150, 3: 26_650, 4: 32_150, 5: 37_650, 6: 43_150, 7: 48_650, 8: 54_150}


def make_member(**insurance_flags):
    member = Mock()
    member.insurance = Insurance(**{"none": False, **insurance_flags})
    return member


def make_calculator(household_size=1, household_income=0, members=None, missing_dependencies=None):
    mock_program = Mock()
    mock_program.year.as_dict.return_value = FPL_2025

    mock_screen = Mock()
    mock_screen.household_size = household_size
    mock_screen.calc_gross_income = Mock(return_value=household_income)
    mock_screen.household_members.all.return_value = [make_member(none=True)] if members is None else members

    return OmniSalud(
        mock_screen,
        mock_program,
        {},
        Dependencies() if missing_dependencies is None else missing_dependencies,
    )


class TestOmniSaludClassAttributes(TestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(OmniSalud, ProgramCalculator))

    def test_is_registered_in_co_calculators(self):
        self.assertIn("omnisalud", co_calculators)
        self.assertEqual(co_calculators["omnisalud"], OmniSalud)

    def test_member_amount_is_610_a_month(self):
        self.assertEqual(OmniSalud.member_amount, 610 * 12)

    def test_no_household_amount(self):
        self.assertEqual(OmniSalud.amount, 0)

    def test_income_percent_is_150_percent_fpl(self):
        self.assertEqual(OmniSalud.income_percent, 1.5)

    def test_eligible_insurance_is_none_only(self):
        self.assertEqual(OmniSalud.insurance, ["none"])

    def test_dependencies(self):
        self.assertEqual(
            OmniSalud.dependencies,
            ["income_amount", "income_frequency", "household_size", "age", "insurance"],
        )


class TestOmniSaludIncomeEligibility(TestCase):
    """Yearly income must be at or below 150% FPL for the household size."""

    def _run(self, household_size, household_income):
        calc = make_calculator(household_size=household_size, household_income=household_income)
        e = Eligibility()
        calc.household_eligible(e)
        return e

    def test_income_well_below_the_limit_is_eligible(self):
        self.assertTrue(self._run(1, 10_000).eligible)

    def test_income_exactly_at_150_percent_fpl_is_eligible(self):
        self.assertTrue(self._run(1, 23_475).eligible)  # 15,650 * 1.5

    def test_income_one_dollar_above_the_limit_is_ineligible(self):
        self.assertFalse(self._run(1, 23_476).eligible)

    def test_limit_scales_with_household_size(self):
        self.assertTrue(self._run(4, 48_225).eligible)  # 32,150 * 1.5
        self.assertFalse(self._run(4, 48_226).eligible)

    def test_zero_income_is_eligible(self):
        self.assertTrue(self._run(1, 0).eligible)

    def test_income_is_read_as_yearly_gross_of_all_types(self):
        calc = make_calculator(household_income=1_000)
        calc.household_eligible(Eligibility())
        calc.screen.calc_gross_income.assert_called_once_with("yearly", ["all"])

    def test_over_income_household_gets_a_fail_message(self):
        e = self._run(1, 99_999)
        self.assertEqual(len(e.fail_messages), 1)
        self.assertEqual(len(e.pass_messages), 0)


class TestOmniSaludMemberEligibility(TestCase):
    """Only uninsured members qualify."""

    def _run(self, member):
        calc = make_calculator()
        e = MemberEligibility(member)
        calc.member_eligible(e)
        return e.eligible

    def test_uninsured_member_is_eligible(self):
        self.assertTrue(self._run(make_member(none=True)))

    def test_member_who_does_not_know_their_insurance_is_eligible(self):
        self.assertTrue(self._run(make_member(dont_know=True)))

    def test_member_with_medicaid_is_ineligible(self):
        self.assertFalse(self._run(make_member(medicaid=True)))

    def test_member_with_private_insurance_is_ineligible(self):
        self.assertFalse(self._run(make_member(private=True)))

    def test_member_with_employer_insurance_is_ineligible(self):
        self.assertFalse(self._run(make_member(employer=True)))

    def test_age_is_not_a_member_gate(self):
        # "age" is a declared dependency but no age condition is applied
        for age in (0, 17, 18, 64, 65, 90):
            member = make_member(none=True)
            member.age = age
            self.assertTrue(self._run(member), f"age {age} should not be gated")


class TestOmniSaludEligible(TestCase):
    def test_low_income_uninsured_household_is_eligible(self):
        calc = make_calculator(household_size=1, household_income=10_000, members=[make_member(none=True)])
        self.assertTrue(calc.eligible().eligible)

    def test_over_income_household_is_ineligible(self):
        calc = make_calculator(household_size=1, household_income=99_999, members=[make_member(none=True)])
        self.assertFalse(calc.eligible().eligible)

    def test_fully_insured_household_is_ineligible(self):
        calc = make_calculator(household_size=1, household_income=10_000, members=[make_member(private=True)])
        self.assertFalse(calc.eligible().eligible)

    def test_one_uninsured_member_qualifies_the_household(self):
        members = [make_member(private=True), make_member(none=True)]
        calc = make_calculator(household_size=2, household_income=10_000, members=members)
        self.assertTrue(calc.eligible().eligible)

    def test_household_with_no_members_is_ineligible(self):
        calc = make_calculator(household_size=1, household_income=10_000, members=[])
        self.assertFalse(calc.eligible().eligible)


class TestOmniSaludValue(TestCase):
    def test_one_uninsured_member_is_worth_one_member_amount(self):
        calc = make_calculator(household_size=1, household_income=10_000, members=[make_member(none=True)])
        self.assertEqual(calc.calc().value, OmniSalud.member_amount)

    def test_value_scales_with_uninsured_members(self):
        members = [make_member(none=True), make_member(none=True)]
        calc = make_calculator(household_size=2, household_income=10_000, members=members)
        self.assertEqual(calc.calc().value, 2 * OmniSalud.member_amount)

    def test_insured_members_add_no_value(self):
        members = [make_member(none=True), make_member(private=True)]
        calc = make_calculator(household_size=2, household_income=10_000, members=members)
        self.assertEqual(calc.calc().value, OmniSalud.member_amount)

    def test_ineligible_household_is_worth_nothing(self):
        calc = make_calculator(household_size=1, household_income=99_999, members=[make_member(none=True)])
        self.assertEqual(calc.calc().value, 0)


class TestOmniSaludCanCalc(TestCase):
    def test_can_calc_with_no_missing_dependencies(self):
        self.assertTrue(make_calculator().can_calc())

    def test_cannot_calc_without_insurance(self):
        self.assertFalse(make_calculator(missing_dependencies=Dependencies(["insurance"])).can_calc())

    def test_cannot_calc_without_income_amount(self):
        self.assertFalse(make_calculator(missing_dependencies=Dependencies(["income_amount"])).can_calc())

    def test_can_calc_with_an_unrelated_missing_dependency(self):
        self.assertTrue(make_calculator(missing_dependencies=Dependencies(["zipcode"])).can_calc())

    def test_calc_raises_when_a_dependency_is_missing(self):
        calc = make_calculator(missing_dependencies=Dependencies(["insurance"]))
        with self.assertRaises(DependencyError):
            calc.calc()

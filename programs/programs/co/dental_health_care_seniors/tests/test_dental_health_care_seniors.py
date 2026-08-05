"""
Unit tests for the DentalHealthCareSeniors (cdhcs) calculator.

Eligibility requirements:
  1. Monthly gross household income at or below 250% FPL / 12
  2. Member is 60 or older
  3. Member does not have Medicaid or private insurance

Notes:
  - The income band is truncated with `int()`, so the boundary sits on the floored dollar.
  - Medicare does NOT disqualify a member, which matters for a 60+ program; that is
    asserted explicitly below.
  - FPL figures used here are the real 2025 guidelines from `FplCache.default`.
"""

from unittest.mock import Mock

from django.test import TestCase

from programs.programs.calc import Eligibility, MemberEligibility, ProgramCalculator
from programs.programs.co import co_calculators
from programs.programs.co.dental_health_care_seniors.calculator import DentalHealthCareSeniors
from programs.util import Dependencies, DependencyError
from screener.models import Insurance

FPL_2025 = {1: 15_650, 2: 21_150, 3: 26_650, 4: 32_150, 5: 37_650, 6: 43_150, 7: 48_650, 8: 54_150}


def make_member(age=65, **insurance_flags):
    member = Mock()
    member.age = age
    member.insurance = Insurance(**{"none": False, **insurance_flags})
    return member


def make_calculator(household_size=1, household_income=0, members=None, missing_dependencies=None):
    mock_program = Mock()
    mock_program.year.as_dict.return_value = FPL_2025

    mock_screen = Mock()
    mock_screen.household_size = household_size
    mock_screen.calc_gross_income = Mock(return_value=household_income)
    mock_screen.household_members.all.return_value = [make_member(age=65, none=True)] if members is None else members

    return DentalHealthCareSeniors(
        mock_screen,
        mock_program,
        {},
        Dependencies() if missing_dependencies is None else missing_dependencies,
    )


class TestDentalHealthCareSeniorsClassAttributes(TestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(DentalHealthCareSeniors, ProgramCalculator))

    def test_is_registered_in_co_calculators(self):
        self.assertIn("cdhcs", co_calculators)
        self.assertEqual(co_calculators["cdhcs"], DentalHealthCareSeniors)

    def test_member_amount_is_80_a_month(self):
        self.assertEqual(DentalHealthCareSeniors.member_amount, 80 * 12)

    def test_no_household_amount(self):
        self.assertEqual(DentalHealthCareSeniors.amount, 0)

    def test_min_age_is_60(self):
        self.assertEqual(DentalHealthCareSeniors.min_age, 60)

    def test_percent_of_fpl_is_250_percent(self):
        self.assertEqual(DentalHealthCareSeniors.percent_of_fpl, 2.5)

    def test_ineligible_insurance(self):
        self.assertEqual(DentalHealthCareSeniors.ineligible_insurance, ["medicaid", "private"])

    def test_dependencies(self):
        self.assertEqual(
            DentalHealthCareSeniors.dependencies,
            ["age", "income_amount", "income_frequency", "insurance", "household_size"],
        )


class TestDentalHealthCareSeniorsIncomeEligibility(TestCase):
    """Monthly income must be at or below 250% FPL / 12."""

    def _run(self, household_size, household_income):
        calc = make_calculator(household_size=household_size, household_income=household_income)
        e = Eligibility()
        calc.household_eligible(e)
        return e

    def test_income_well_below_the_band_is_eligible(self):
        self.assertTrue(self._run(1, 1_000).eligible)

    def test_income_exactly_at_the_band_is_eligible(self):
        # int(2.5 * 15,650 / 12) == 3,260
        self.assertTrue(self._run(1, 3_260).eligible)

    def test_income_one_dollar_above_the_band_is_ineligible(self):
        self.assertFalse(self._run(1, 3_261).eligible)

    def test_band_scales_with_household_size(self):
        # int(2.5 * 32,150 / 12) == 6,697
        self.assertTrue(self._run(4, 6_697).eligible)
        self.assertFalse(self._run(4, 6_698).eligible)

    def test_zero_income_is_eligible(self):
        self.assertTrue(self._run(1, 0).eligible)

    def test_income_is_read_as_monthly_gross_of_all_types(self):
        calc = make_calculator(household_income=1_000)
        calc.household_eligible(Eligibility())
        calc.screen.calc_gross_income.assert_called_once_with("monthly", ["all"])

    def test_over_income_household_gets_a_fail_message(self):
        e = self._run(1, 99_999)
        self.assertEqual(len(e.fail_messages), 1)
        self.assertEqual(len(e.pass_messages), 0)


class TestDentalHealthCareSeniorsMemberAge(TestCase):
    """Members must be 60 or older."""

    def _run(self, age):
        calc = make_calculator()
        e = MemberEligibility(make_member(age=age, none=True))
        calc.member_eligible(e)
        return e.eligible

    def test_age_59_is_ineligible(self):
        self.assertFalse(self._run(59))

    def test_age_60_is_eligible(self):
        self.assertTrue(self._run(60))

    def test_age_61_is_eligible(self):
        self.assertTrue(self._run(61))

    def test_age_90_is_eligible(self):
        self.assertTrue(self._run(90))

    def test_child_is_ineligible(self):
        self.assertFalse(self._run(5))


class TestDentalHealthCareSeniorsMemberInsurance(TestCase):
    """Medicaid and private insurance disqualify a member; nothing else does."""

    def _run(self, **insurance_flags):
        calc = make_calculator()
        e = MemberEligibility(make_member(age=65, **insurance_flags))
        calc.member_eligible(e)
        return e.eligible

    def test_uninsured_member_is_eligible(self):
        self.assertTrue(self._run(none=True))

    def test_member_with_medicaid_is_ineligible(self):
        self.assertFalse(self._run(medicaid=True))

    def test_member_with_private_insurance_is_ineligible(self):
        self.assertFalse(self._run(private=True))

    def test_member_with_medicare_is_eligible(self):
        # Medicare is not in `ineligible_insurance`, which matters for a 60+ program
        self.assertTrue(self._run(medicare=True))

    def test_member_with_employer_insurance_is_eligible(self):
        self.assertTrue(self._run(employer=True))

    def test_member_with_va_insurance_is_eligible(self):
        self.assertTrue(self._run(va=True))


class TestDentalHealthCareSeniorsEligible(TestCase):
    def test_low_income_uninsured_senior_is_eligible(self):
        calc = make_calculator(household_size=1, household_income=1_000, members=[make_member(age=65, none=True)])
        self.assertTrue(calc.eligible().eligible)

    def test_over_income_household_is_ineligible(self):
        calc = make_calculator(household_size=1, household_income=99_999, members=[make_member(age=65, none=True)])
        self.assertFalse(calc.eligible().eligible)

    def test_household_with_no_seniors_is_ineligible(self):
        calc = make_calculator(household_size=2, household_income=1_000, members=[make_member(age=30, none=True)])
        self.assertFalse(calc.eligible().eligible)

    def test_one_qualifying_senior_qualifies_the_household(self):
        members = [make_member(age=30, none=True), make_member(age=70, none=True)]
        calc = make_calculator(household_size=2, household_income=1_000, members=members)
        self.assertTrue(calc.eligible().eligible)

    def test_household_with_no_members_is_ineligible(self):
        calc = make_calculator(household_size=1, household_income=1_000, members=[])
        self.assertFalse(calc.eligible().eligible)


class TestDentalHealthCareSeniorsValue(TestCase):
    def test_one_senior_is_worth_one_member_amount(self):
        calc = make_calculator(household_size=1, household_income=1_000, members=[make_member(age=65, none=True)])
        self.assertEqual(calc.calc().value, DentalHealthCareSeniors.member_amount)

    def test_value_scales_with_qualifying_seniors(self):
        members = [make_member(age=65, none=True), make_member(age=70, none=True)]
        calc = make_calculator(household_size=2, household_income=1_000, members=members)
        self.assertEqual(calc.calc().value, 2 * DentalHealthCareSeniors.member_amount)

    def test_non_seniors_add_no_value(self):
        members = [make_member(age=65, none=True), make_member(age=30, none=True)]
        calc = make_calculator(household_size=2, household_income=1_000, members=members)
        self.assertEqual(calc.calc().value, DentalHealthCareSeniors.member_amount)

    def test_ineligible_household_is_worth_nothing(self):
        calc = make_calculator(household_size=1, household_income=99_999, members=[make_member(age=65, none=True)])
        self.assertEqual(calc.calc().value, 0)


class TestDentalHealthCareSeniorsCanCalc(TestCase):
    def test_can_calc_with_no_missing_dependencies(self):
        self.assertTrue(make_calculator().can_calc())

    def test_cannot_calc_without_age(self):
        self.assertFalse(make_calculator(missing_dependencies=Dependencies(["age"])).can_calc())

    def test_cannot_calc_without_insurance(self):
        self.assertFalse(make_calculator(missing_dependencies=Dependencies(["insurance"])).can_calc())

    def test_can_calc_with_an_unrelated_missing_dependency(self):
        self.assertTrue(make_calculator(missing_dependencies=Dependencies(["zipcode"])).can_calc())

    def test_calc_raises_when_a_dependency_is_missing(self):
        calc = make_calculator(missing_dependencies=Dependencies(["age"]))
        with self.assertRaises(DependencyError):
            calc.calc()

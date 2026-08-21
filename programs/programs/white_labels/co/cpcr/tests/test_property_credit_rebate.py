"""
Unit tests for the PropertyCreditRebate (cpcr) calculator.

Eligibility requirements:
  1. Yearly gross household income at or below a flat limit that depends on whether
     anyone in the household is married
  2. Household has a rent or mortgage expense
  3. Member is 65+, or is over 18 with a disability (or is a surviving spouse, which
     the screener never asks about)

Notes:
  - The disability path uses a strict `>` against `disabled_min_age`, so an 18-year-old
    with a disability does not qualify but a 19-year-old does.
  - `_is_surviving_spouse` is hardcoded to False because the screener has no question
    for it; that is asserted so the stub doesn't get forgotten.
  - The income limits are flat dollar amounts on the calculator, not FPL-derived.
  - Members are real (unsaved) `HouseholdMember` instances rather than mocks so that
    `has_disability` is genuinely exercised across all three of its fields.
"""

from unittest.mock import Mock

from django.test import TestCase

from programs.framework.base import Eligibility, MemberEligibility, ProgramCalculator
from programs.programs.white_labels.co.cpcr.calculator import PropertyCreditRebate
from programs.util import Dependencies, DependencyError
from screener.models import HouseholdMember
from programs.framework.pe_dependencies import member


def make_member(age=70, disabled=False, visually_impaired=False, long_term_disability=False):
    """
    A real, unsaved `HouseholdMember` so that `has_disability` runs for real. Mocking its
    return value would collapse the three disability fields into one and hide a change to
    any of them.
    """
    return HouseholdMember(
        age=age,
        disabled=disabled,
        visually_impaired=visually_impaired,
        long_term_disability=long_term_disability,
    )


def make_calculator(
    household_income=0,
    married=False,
    has_expense=True,
    members=None,
    missing_dependencies=None,
):
    mock_screen = Mock()
    mock_screen.calc_gross_income = Mock(return_value=household_income)
    mock_screen.has_expense = Mock(return_value=has_expense)
    mock_screen.relationship_map = Mock(return_value={1: 2, 2: 1} if married else {1: None})
    mock_screen.household_members.all.return_value = [make_member()] if members is None else members

    return PropertyCreditRebate(
        mock_screen,
        Mock(),
        {},
        Dependencies() if missing_dependencies is None else missing_dependencies,
    )


class TestPropertyCreditRebateClassAttributes(TestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(PropertyCreditRebate, ProgramCalculator))

    def test_amount_is_1154(self):
        self.assertEqual(PropertyCreditRebate.amount, 1_154)

    def test_no_member_amount(self):
        self.assertEqual(PropertyCreditRebate.member_amount, 0)

    def test_min_age_is_65(self):
        self.assertEqual(PropertyCreditRebate.min_age, 65)

    def test_disabled_min_age_is_18(self):
        self.assertEqual(PropertyCreditRebate.disabled_min_age, 18)

    def test_qualifying_expenses(self):
        self.assertEqual(PropertyCreditRebate.expenses, ["rent", "mortgage"])

    def test_income_limits(self):
        self.assertEqual(PropertyCreditRebate.income_limit, {"single": 18_704, "married": 25_261})

    def test_dependencies(self):
        self.assertEqual(
            PropertyCreditRebate.dependencies,
            ["age", "income_frequency", "income_amount", "relationship"],
        )


class TestPropertyCreditRebateIncomeEligibility(TestCase):
    """A flat income limit that rises when the household contains a married pair."""

    def _run(self, household_income, married=False):
        calc = make_calculator(household_income=household_income, married=married)
        e = Eligibility()
        calc.household_eligible(e)
        return e

    def test_single_income_below_limit_is_eligible(self):
        self.assertTrue(self._run(10_000).eligible)

    def test_single_income_exactly_at_limit_is_eligible(self):
        self.assertTrue(self._run(18_704).eligible)

    def test_single_income_one_dollar_above_limit_is_ineligible(self):
        self.assertFalse(self._run(18_705).eligible)

    def test_married_income_exactly_at_limit_is_eligible(self):
        self.assertTrue(self._run(25_261, married=True).eligible)

    def test_married_income_one_dollar_above_limit_is_ineligible(self):
        self.assertFalse(self._run(25_262, married=True).eligible)

    def test_married_limit_is_higher_than_single_limit(self):
        income = 20_000
        self.assertFalse(self._run(income).eligible)
        self.assertTrue(self._run(income, married=True).eligible)

    def test_income_is_read_as_yearly_gross_of_all_types(self):
        calc = make_calculator(household_income=1_000)
        calc.household_eligible(Eligibility())
        calc.screen.calc_gross_income.assert_called_once_with("yearly", ["all"])

    def test_over_income_household_gets_a_fail_message(self):
        e = self._run(99_999)
        self.assertEqual(len(e.fail_messages), 1)


class TestPropertyCreditRebateExpenseRequirement(TestCase):
    """The household must report rent or a mortgage."""

    def _run(self, has_expense):
        calc = make_calculator(household_income=10_000, has_expense=has_expense)
        e = Eligibility()
        calc.household_eligible(e)
        return e.eligible

    def test_household_with_a_housing_expense_is_eligible(self):
        self.assertTrue(self._run(True))

    def test_household_without_a_housing_expense_is_ineligible(self):
        self.assertFalse(self._run(False))

    def test_expense_check_looks_for_rent_and_mortgage(self):
        calc = make_calculator(household_income=10_000)
        calc.household_eligible(Eligibility())
        calc.screen.has_expense.assert_called_once_with(["rent", "mortgage"])

    def test_missing_expense_does_not_add_a_message(self):
        # the expense condition is passed no message, so it fails silently
        calc = make_calculator(household_income=10_000, has_expense=False)
        e = Eligibility()
        calc.household_eligible(e)
        self.assertFalse(e.eligible)
        self.assertEqual(len(e.fail_messages), 0)


class TestPropertyCreditRebateMemberEligibility(TestCase):
    """Age 65+, or over 18 with a disability."""

    def _run(self, member):
        calc = make_calculator()
        e = MemberEligibility(member)
        calc.member_eligible(e)
        return e.eligible

    def test_age_64_without_disability_is_ineligible(self):
        self.assertFalse(self._run(make_member(age=64)))

    def test_age_65_is_eligible(self):
        self.assertTrue(self._run(make_member(age=65)))

    def test_age_66_is_eligible(self):
        self.assertTrue(self._run(make_member(age=66)))

    def test_disabled_adult_under_65_is_eligible(self):
        self.assertTrue(self._run(make_member(age=40, disabled=True)))

    def test_visually_impaired_adult_is_eligible(self):
        self.assertTrue(self._run(make_member(age=40, visually_impaired=True)))

    def test_member_with_long_term_disability_is_eligible(self):
        self.assertTrue(self._run(make_member(age=40, long_term_disability=True)))

    def test_disabled_18_year_old_is_ineligible(self):
        # `disabled_min_age` is compared with a strict `>`
        self.assertFalse(self._run(make_member(age=18, disabled=True)))

    def test_disabled_19_year_old_is_eligible(self):
        self.assertTrue(self._run(make_member(age=19, disabled=True)))

    def test_disabled_child_is_ineligible(self):
        self.assertFalse(self._run(make_member(age=10, disabled=True)))

    def test_surviving_spouse_path_is_always_false(self):
        # the screener has no surviving-spouse question, so the helper is stubbed out
        calc = make_calculator()
        self.assertFalse(calc._is_surviving_spouse(make_member(age=40)))


class TestPropertyCreditRebateEligible(TestCase):
    def test_low_income_senior_renter_is_eligible(self):
        calc = make_calculator(household_income=10_000, members=[make_member(age=70)])
        self.assertTrue(calc.eligible().eligible)

    def test_over_income_household_is_ineligible(self):
        calc = make_calculator(household_income=99_999, members=[make_member(age=70)])
        self.assertFalse(calc.eligible().eligible)

    def test_household_without_housing_expense_is_ineligible(self):
        calc = make_calculator(household_income=10_000, has_expense=False, members=[make_member(age=70)])
        self.assertFalse(calc.eligible().eligible)

    def test_household_with_no_qualifying_member_is_ineligible(self):
        calc = make_calculator(household_income=10_000, members=[make_member(age=40)])
        self.assertFalse(calc.eligible().eligible)

    def test_one_qualifying_member_qualifies_the_household(self):
        members = [make_member(age=40), make_member(age=70)]
        calc = make_calculator(household_income=10_000, members=members)
        self.assertTrue(calc.eligible().eligible)

    def test_household_with_no_members_is_ineligible(self):
        calc = make_calculator(household_income=10_000, members=[])
        self.assertFalse(calc.eligible().eligible)


class TestPropertyCreditRebateValue(TestCase):
    def test_eligible_household_is_worth_1154(self):
        calc = make_calculator(household_income=10_000, members=[make_member(age=70)])
        e = calc.calc()
        self.assertEqual(e.household_value, 1_154)
        self.assertEqual(e.value, 1_154)

    def test_value_does_not_scale_with_qualifying_members(self):
        members = [make_member(age=70), make_member(age=80)]
        calc = make_calculator(household_income=10_000, members=members)
        self.assertEqual(calc.calc().value, 1_154)

    def test_ineligible_household_is_worth_nothing(self):
        calc = make_calculator(household_income=99_999, members=[make_member(age=70)])
        self.assertEqual(calc.calc().value, 0)


class TestPropertyCreditRebateCanCalc(TestCase):
    def test_can_calc_with_no_missing_dependencies(self):
        self.assertTrue(make_calculator().can_calc())

    def test_cannot_calc_without_age(self):
        self.assertFalse(make_calculator(missing_dependencies=Dependencies(["age"])).can_calc())

    def test_cannot_calc_without_relationship(self):
        self.assertFalse(make_calculator(missing_dependencies=Dependencies(["relationship"])).can_calc())

    def test_can_calc_with_an_unrelated_missing_dependency(self):
        self.assertTrue(make_calculator(missing_dependencies=Dependencies(["insurance"])).can_calc())

    def test_calc_raises_when_a_dependency_is_missing(self):
        calc = make_calculator(missing_dependencies=Dependencies(["age"]))
        with self.assertRaises(DependencyError):
            calc.calc()

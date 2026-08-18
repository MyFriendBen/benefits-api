"""
Unit tests for the ReproductiveHealthCare (rhc) calculator.

Eligibility requirements:
  1. Household is Medicaid eligible (read from the `data` of the sibling Medicaid program)
  2. Member has no health insurance

Notes:
  - `rhc` is currently inactive, but the calculator is still registered in `co_calculators`
    and would run as soon as the program is switched on.
  - Insurance is exercised through real (unsaved) `Insurance` instances so that the
    `dont_know` aliasing inside `has_insurance_types` is covered rather than mocked away.
"""

from unittest.mock import Mock

from django.test import TestCase

from programs.framework.base import Eligibility, MemberEligibility, ProgramCalculator
from programs.programs.co.reproductive_health_care.calculator import ReproductiveHealthCare
from programs.util import Dependencies, DependencyError
from screener.models import Insurance


def make_member(**insurance_flags):
    """A member whose `insurance` is a real, unsaved Insurance row."""
    member = Mock()
    member.insurance = Insurance(**{"none": False, **insurance_flags})
    return member


def make_data(medicaid_eligible=None, key="co_medicaid"):
    """The `data` dict the screener passes between calculators."""
    if medicaid_eligible is None:
        return {}

    medicaid = Eligibility()
    medicaid.eligible = medicaid_eligible
    return {key: medicaid}


def make_calculator(medicaid_eligible=True, members=None, missing_dependencies=None, medicaid_key="co_medicaid"):
    mock_screen = Mock()
    mock_screen.household_members.all.return_value = [make_member(none=True)] if members is None else members

    return ReproductiveHealthCare(
        mock_screen,
        Mock(),
        make_data(medicaid_eligible, medicaid_key),
        Dependencies() if missing_dependencies is None else missing_dependencies,
    )


class TestReproductiveHealthCareClassAttributes(TestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(ReproductiveHealthCare, ProgramCalculator))

    def test_amount_is_268(self):
        self.assertEqual(ReproductiveHealthCare.amount, 268)

    def test_no_member_amount(self):
        self.assertEqual(ReproductiveHealthCare.member_amount, 0)

    def test_dependencies(self):
        self.assertEqual(ReproductiveHealthCare.dependencies, ["insurance"])


class TestReproductiveHealthCareHouseholdEligibility(TestCase):
    """The household must be Medicaid eligible."""

    def _run(self, medicaid_eligible, medicaid_key="co_medicaid"):
        calc = make_calculator(medicaid_eligible=medicaid_eligible, medicaid_key=medicaid_key)
        e = Eligibility()
        calc.household_eligible(e)
        return e

    def test_medicaid_eligible_household_is_eligible(self):
        self.assertTrue(self._run(True).eligible)

    def test_medicaid_ineligible_household_is_ineligible(self):
        self.assertFalse(self._run(False).eligible)

    def test_household_is_ineligible_when_medicaid_was_not_calculated(self):
        self.assertFalse(self._run(None).eligible)

    def test_eligible_household_gets_a_pass_message(self):
        e = self._run(True)
        self.assertEqual(len(e.pass_messages), 1)
        self.assertEqual(len(e.fail_messages), 0)

    def test_ineligible_household_gets_a_fail_message(self):
        e = self._run(False)
        self.assertEqual(len(e.fail_messages), 1)
        self.assertEqual(len(e.pass_messages), 0)


class TestReproductiveHealthCareMemberEligibility(TestCase):
    """Only members with no health insurance qualify."""

    def _run(self, member):
        calc = make_calculator()
        e = MemberEligibility(member)
        calc.member_eligible(e)
        return e.eligible

    def test_uninsured_member_is_eligible(self):
        self.assertTrue(self._run(make_member(none=True)))

    def test_member_who_does_not_know_their_insurance_is_eligible(self):
        # `has_insurance_types` treats "none" as also matching "dont_know"
        self.assertTrue(self._run(make_member(dont_know=True)))

    def test_member_with_medicaid_is_ineligible(self):
        self.assertFalse(self._run(make_member(medicaid=True)))

    def test_member_with_private_insurance_is_ineligible(self):
        self.assertFalse(self._run(make_member(private=True)))

    def test_member_with_employer_insurance_is_ineligible(self):
        self.assertFalse(self._run(make_member(employer=True)))

    def test_member_with_medicare_is_ineligible(self):
        self.assertFalse(self._run(make_member(medicare=True)))


class TestReproductiveHealthCareEligible(TestCase):
    def test_medicaid_eligible_household_with_an_uninsured_member_is_eligible(self):
        calc = make_calculator(medicaid_eligible=True, members=[make_member(none=True)])
        self.assertTrue(calc.eligible().eligible)

    def test_medicaid_ineligible_household_is_ineligible(self):
        calc = make_calculator(medicaid_eligible=False, members=[make_member(none=True)])
        self.assertFalse(calc.eligible().eligible)

    def test_household_where_everyone_is_insured_is_ineligible(self):
        calc = make_calculator(medicaid_eligible=True, members=[make_member(private=True)])
        self.assertFalse(calc.eligible().eligible)

    def test_one_uninsured_member_qualifies_the_household(self):
        members = [make_member(private=True), make_member(none=True)]
        calc = make_calculator(medicaid_eligible=True, members=members)
        self.assertTrue(calc.eligible().eligible)

    def test_household_with_no_members_is_ineligible(self):
        calc = make_calculator(medicaid_eligible=True, members=[])
        self.assertFalse(calc.eligible().eligible)


class TestReproductiveHealthCareValue(TestCase):
    def test_eligible_household_is_worth_268(self):
        calc = make_calculator(medicaid_eligible=True, members=[make_member(none=True)])
        e = calc.calc()
        self.assertEqual(e.household_value, 268)
        self.assertEqual(e.value, 268)

    def test_value_does_not_scale_with_uninsured_members(self):
        members = [make_member(none=True), make_member(none=True)]
        calc = make_calculator(medicaid_eligible=True, members=members)
        self.assertEqual(calc.calc().value, 268)

    def test_ineligible_household_is_worth_nothing(self):
        calc = make_calculator(medicaid_eligible=False, members=[make_member(none=True)])
        self.assertEqual(calc.calc().value, 0)


class TestReproductiveHealthCareCanCalc(TestCase):
    def test_can_calc_with_no_missing_dependencies(self):
        self.assertTrue(make_calculator().can_calc())

    def test_cannot_calc_without_insurance(self):
        calc = make_calculator(missing_dependencies=Dependencies(["insurance"]))
        self.assertFalse(calc.can_calc())

    def test_can_calc_with_an_unrelated_missing_dependency(self):
        calc = make_calculator(missing_dependencies=Dependencies(["income_amount"]))
        self.assertTrue(calc.can_calc())

    def test_calc_raises_when_insurance_is_missing(self):
        calc = make_calculator(missing_dependencies=Dependencies(["insurance"]))
        with self.assertRaises(DependencyError):
            calc.calc()

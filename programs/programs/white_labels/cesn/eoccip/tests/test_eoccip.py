"""Energy Outreach Colorado Crisis Intervention (cesn_eoccip) — first tests.

Three conditions, all required: LEAP eligibility, broken heating, and (for renters) some
reported energy expense. The LEAP gate is the reason this program existed as an example in
the coupling-removal work, so the tests that matter most here are the ones pinning that
LEAP eligibility is *necessary but not sufficient* — the shape the original ticket got
backwards — and that the rent/mortgage requirement CESN's LEAP overrides away does not
leak back in.

Households are hand-rolled on Mock screens, matching the sibling CESN calculators' tests.
`CustomCalculatorTestCase` would replace the boilerplate; it is still unmerged.
"""

from unittest.mock import Mock

from django.test import TestCase

from programs.framework.base import Eligibility, ProgramCalculator
from programs.programs.white_labels.cesn.eoccip.calculator import (
    EnergyCalculatorEnergyOutreachCrisisIntervention as Eoccip,
)
from programs.util import Dependencies, DependencyError, UpstreamAbsentError


def make_data(leap_eligible=None):
    """The `data` dict the eligibility loop threads between calculators."""
    if leap_eligible is None:
        return {}

    leap = Eligibility()
    leap.eligible = leap_eligible
    return {"cesn_leap": leap}


def make_calculator(
    leap_eligible=True,
    needs_hvac=True,
    path="homeowner",
    expenses=(),
    missing_dependencies=None,
):
    screen = Mock()
    screen.path = path
    screen.energy_calculator.needs_hvac = needs_hvac
    screen.has_expense.side_effect = lambda types: any(t in expenses for t in types)
    screen.household_members.all.return_value = [Mock()]

    return Eoccip(
        screen,
        Mock(),
        make_data(leap_eligible),
        Dependencies() if missing_dependencies is None else missing_dependencies,
    )


class TestRegistration(TestCase):
    def test_is_a_program_calculator(self):
        self.assertTrue(issubclass(Eoccip, ProgramCalculator))

    def test_program_code(self):
        self.assertEqual(Eoccip.program_code, "cesn_eoccip")

    def test_declares_its_leap_gate(self):
        self.assertEqual(Eoccip.gates_on, ("cesn_leap",))

    def test_declares_only_its_own_screener_fields(self):
        """LEAP's fields arrive through `all_dependencies`; restating them here is what the
        declaration replaced."""
        self.assertEqual(Eoccip.dependencies, ["energy_calculator"])


class TestLeapEligibilityIsNecessaryNotSufficient(TestCase):
    """The claim worth pinning: `program_eligible` is one of three ANDed conditions, so a
    LEAP-eligible household with a working furnace gets nothing."""

    def _eligible(self, **kwargs):
        e = Eligibility()
        make_calculator(**kwargs).household_eligible(e)
        return e.eligible

    def test_leap_eligible_with_broken_heating_is_eligible(self):
        self.assertTrue(self._eligible())

    def test_leap_eligible_with_working_heating_is_not_eligible(self):
        self.assertFalse(self._eligible(needs_hvac=False))

    def test_leap_ineligible_is_not_eligible_even_with_broken_heating(self):
        self.assertFalse(self._eligible(leap_eligible=False))


class TestTheLeapGateDoesNotGuess(TestCase):
    def test_uncalculated_leap_raises_rather_than_reading_as_not_eligible(self):
        """An absent key means "not calculated", a different answer from "calculated, and
        not eligible" — so the program drops out instead of being reported ineligible."""
        with self.assertRaises(DependencyError):
            make_calculator(leap_eligible=None).household_eligible(Eligibility())

    def test_the_raise_names_the_upstream(self):
        with self.assertRaises(UpstreamAbsentError) as caught:
            make_calculator(leap_eligible=None).household_eligible(Eligibility())

        self.assertEqual(caught.exception.program_code, "cesn_leap")


class TestRenterExpenses(TestCase):
    def test_a_renter_reporting_an_energy_expense_is_eligible(self):
        e = Eligibility()
        make_calculator(path="renter", expenses=("heating",)).household_eligible(e)
        self.assertTrue(e.eligible)

    def test_a_renter_reporting_no_energy_expense_is_not_eligible(self):
        e = Eligibility()
        make_calculator(path="renter", expenses=()).household_eligible(e)
        self.assertFalse(e.eligible)

    def test_a_homeowner_needs_no_reported_expense(self):
        e = Eligibility()
        make_calculator(path="homeowner", expenses=()).household_eligible(e)
        self.assertTrue(e.eligible)


class TestCesnLeapOverridesDoNotLeakBack(TestCase):
    def test_a_rent_or_mortgage_expense_is_irrelevant(self):
        """CESN's LEAP overrides `_has_expense` to `True`, so for CESN the whole of LEAP
        eligibility is the 60% SMI income test. A restatement that carried the base
        program's rent/mortgage requirement across would be wrong, and this is the
        regression guard for that."""
        without = Eligibility()
        make_calculator(expenses=()).household_eligible(without)

        with_expense = Eligibility()
        make_calculator(expenses=("rent",)).household_eligible(with_expense)

        self.assertTrue(without.eligible)
        self.assertEqual(without.eligible, with_expense.eligible)


class TestCanCalc(TestCase):
    def test_can_calc_with_nothing_missing(self):
        self.assertTrue(make_calculator().can_calc())

    def test_cannot_calc_without_its_own_field(self):
        self.assertFalse(make_calculator(missing_dependencies=Dependencies(["energy_calculator"])).can_calc())

    def test_cannot_calc_without_a_field_only_leap_reads(self):
        """`county` is LEAP's, not this program's. Requiring it is what stops this program
        being calculable on a screen where LEAP is not — which would make the gate raise
        and drop the program for a household it could have answered for."""
        self.assertNotIn("county", Eoccip.dependencies)
        self.assertFalse(make_calculator(missing_dependencies=Dependencies(["county"])).can_calc())

    def test_cannot_calc_without_leaps_income_fields(self):
        self.assertFalse(make_calculator(missing_dependencies=Dependencies(["income_amount"])).can_calc())

    def test_can_calc_with_a_field_neither_program_reads(self):
        self.assertTrue(make_calculator(missing_dependencies=Dependencies(["expense_amount"])).can_calc())


class TestValue(TestCase):
    def test_an_eligible_household_is_worth_the_sentinel_amount(self):
        """`amount = 1`: the program's real worth is not estimable, and the frontend hides a
        zero-value program, so a sentinel keeps it on the list."""
        self.assertEqual(make_calculator().calc().value, 1)

    def test_an_ineligible_household_is_worth_nothing(self):
        self.assertEqual(make_calculator(needs_hvac=False).calc().value, 0)

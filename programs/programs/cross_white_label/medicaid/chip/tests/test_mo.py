"""MO tests.

Wiring and value arithmetic for ``MoChip``. The end-to-end scenario suite lives in
``test_mo_scenarios.py``; nothing here talks to PolicyEngine.
"""

from decimal import Decimal

from django.test import TestCase

from integrations.clients.policyengine.engines import Sim
from programs.framework.pe_dependencies.constants import MAIN_TAX_UNIT, SECONDARY_TAX_UNIT
from programs.framework.pe_dependencies.household import MoStateCodeDependency
from programs.framework.pe_dependencies.member import ChipGross, ReceivesMedicaidDependency
from programs.framework.pe_dependencies.payload import pe_input
from programs.framework.pe_dependencies.tax import MoChipPremium
from programs.programs.cross_white_label.medicaid.chip.mo import MoChip
from programs.programs.testing_fixtures.pe_integration import (
    add_income,
    add_member,
    make_program,
    make_screen,
)
from programs.util import Dependencies
from screener.models import Insurance

YEAR = "2026"


class StubSim(Sim):
    """Returns the values it was handed, keyed the way PolicyEngine keys them.

    Lets the premium arithmetic be tested without a cassette: what is under test is how
    MoChip combines PolicyEngine's numbers, not what PolicyEngine's numbers are.
    """

    def __init__(self, gross_by_member, premium_by_tax_unit):
        super().__init__({})
        self.gross_by_member = gross_by_member
        self.premium_by_tax_unit = premium_by_tax_unit

    def value(self, unit, sub_unit, variable, period):
        if variable == "chip_gross":
            return self.gross_by_member[sub_unit]
        if variable == "mo_chip_premium":
            # PolicyEngine has no entry for a tax unit the payload omitted.
            return self.premium_by_tax_unit[sub_unit]
        raise AssertionError(f"unexpected variable {variable}")


class MoChipTestBase(TestCase):
    def build(self, household_size=3, **member_kwargs):
        screen = make_screen(
            1,
            white_label_code="mo",
            state_code="MO",
            household_size=household_size,
            zipcode="63101",
            county="St. Louis City",
        )
        self.program = make_program("mo", "mo_chip", YEAR)

        self.head = add_member(screen, 1, "headOfHousehold", 36)
        add_income(self.head, amount=4_000)
        self.spouse = add_member(screen, 2, "spouse", 33)
        self.child = add_member(screen, 3, "child", 8, **member_kwargs)

        return screen

    def calculator(self, screen):
        return MoChip(screen, self.program, Dependencies())

    def payload(self, screen):
        return pe_input(screen, [self.calculator(screen)])["household"]


class TestMoChipPeInput(MoChipTestBase):
    """What MoChip asks PolicyEngine for."""

    def test_sends_state_code_mo(self):
        """PolicyEngine's Missouri CHIP parameters are unreachable without it, and
        ``pe_input()`` never supplies state_code on its own."""
        self.assertIn(MoStateCodeDependency, MoChip.pe_inputs)

        household = self.payload(self.build())["households"]["household"]
        self.assertEqual(household["state_code"][YEAR], "MO")

    def test_sends_receives_medicaid(self):
        """42 CFR 457.350(d) is applied by PolicyEngine, from this input."""
        self.assertIn(ReceivesMedicaidDependency, MoChip.pe_inputs)

        people = self.payload(self.build())["people"]
        self.assertIs(people["3"]["receives_medicaid"][YEAR], False)

    def test_receives_medicaid_true_for_a_child_on_medicaid(self):
        screen = self.build()
        Insurance.objects.create(household_member=self.child, none=False, medicaid=True)

        people = self.payload(screen)["people"]
        self.assertIs(people["3"]["receives_medicaid"][YEAR], True)

    def test_reads_chip_gross_not_chip(self):
        """``chip`` is net of PolicyEngine's cost-sharing offsets; netting Missouri's
        premium against it too would count cost-sharing twice."""
        self.assertEqual(MoChip.pe_name, "chip_gross")
        self.assertIn(ChipGross, MoChip.pe_outputs)

        people = self.payload(self.build())["people"]
        self.assertIn("chip_gross", people["3"])
        self.assertNotIn("chip", people["3"])

    def test_chip_gross_requested_at_the_annual_period(self):
        people = self.payload(self.build())["people"]
        self.assertEqual(list(people["3"]["chip_gross"].keys()), [YEAR])

    def test_premium_requested_at_a_july_month_period(self):
        """The whole reason MoChip needs a per-variable period.

        ``mo_chip_premium`` is monthly (PolicyEngine 1.790.2) so Appendix E's July 1
        turnover takes effect. Asked for at the annual period it returns the twelve months
        summed — six of each schedule — and matches neither.
        """
        self.assertIn(MoChipPremium, MoChip.pe_monthly_outputs)

        tax_unit = self.payload(self.build())["tax_units"][MAIN_TAX_UNIT]
        self.assertEqual(list(tax_unit["mo_chip_premium"].keys()), [f"{YEAR}-07"])

    def test_premium_dependency_is_a_tax_unit_variable(self):
        self.assertEqual(MoChipPremium.field, "mo_chip_premium")
        self.assertEqual(MoChipPremium.unit, "tax_units")


class TestMoChipDoesNotGateOnInsurance(MoChipTestBase):
    """specs/mo.md Criterion 3: the coarse private/employer answers stay inclusive.

    The other state CHIP calculators beside this file zero the value for any child whose
    insurance is not exactly ``none``. Missouri does not, because the screener cannot tell
    comprehensive coverage from Missouri's own "still uninsured" exceptions.
    """

    def _value(self, screen):
        calculator = self.calculator(screen)
        calculator.set_engine(
            StubSim(
                gross_by_member={"1": 0.0, "2": 0.0, "3": 2_911.851},
                premium_by_tax_unit={MAIN_TAX_UNIT: 32.0},
            )
        )
        return calculator.member_value(self.child)

    def test_private_insurance_keeps_the_gross_value(self):
        screen = self.build()
        Insurance.objects.create(household_member=self.child, none=False, private=True)
        self.assertEqual(self._value(screen), 2_911.851)

    def test_employer_insurance_keeps_the_gross_value(self):
        screen = self.build()
        Insurance.objects.create(household_member=self.child, none=False, employer=True)
        self.assertEqual(self._value(screen), 2_911.851)


class TestMoChipValue(MoChipTestBase):
    """How the household premium is netted against PolicyEngine's per-child gross."""

    def _eligibility(self, screen, gross_by_member, premium_by_tax_unit):
        calculator = self.calculator(screen)
        calculator.set_engine(StubSim(gross_by_member, premium_by_tax_unit))
        return calculator.calc()

    def test_premium_is_subtracted_once_for_one_child(self):
        e = self._eligibility(
            self.build(),
            {"1": 0.0, "2": 0.0, "3": 2_911.851},
            {MAIN_TAX_UNIT: 32.0},
        )
        self.assertTrue(e.eligible)
        self.assertAlmostEqual(e.value, 2_911.851 - 384, places=3)

    def test_premium_is_subtracted_once_for_three_children(self):
        """A household charge, not a per-child one."""
        screen = self.build(household_size=5)
        add_member(screen, 4, "child", 11)
        add_member(screen, 5, "child", 5)

        e = self._eligibility(
            screen,
            {"1": 0.0, "2": 0.0, "3": 2_911.851, "4": 2_911.851, "5": 2_911.851},
            {MAIN_TAX_UNIT: 363.0},
        )
        self.assertAlmostEqual(e.value, 3 * 2_911.851 - 4_356, places=3)

    def test_gross_is_summed_unrounded(self):
        """Six children at $2,911.851 come to $17,471.106. Rounding each child first gives
        $17,471.10 — a cent short. specs/mo.md Scenario 17."""
        screen = self.build(household_size=8)
        for member_id in range(4, 9):
            add_member(screen, member_id, "child", member_id)

        gross = {str(i): 2_911.851 for i in range(3, 9)}
        gross.update({"1": 0.0, "2": 0.0})

        e = self._eligibility(screen, gross, {MAIN_TAX_UNIT: 214.0})
        self.assertEqual(int(e.value * 100), 1_490_310)  # $14,903.106

    def test_value_floors_at_one_dollar_rather_than_zero(self):
        """specs/mo.md Scenario 10, with the sentinel the platform requires.

        The premium exceeds the gross value, so the arithmetic is negative. The child is
        still CHIP-eligible and would get coverage, but `eligible = value > 0` and the
        frontend's own `programValue(program) > 0` filter would both drop a $0 program,
        hiding it from exactly the families it applies to.
        """
        e = self._eligibility(
            self.build(),
            {"1": 0.0, "2": 0.0, "3": 2_911.851},
            {MAIN_TAX_UNIT: 256.0},  # 256 x 12 = 3,072 > 2,911.851
        )
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, MoChip.min_value)

    def test_no_eligible_child_is_not_eligible_and_charges_no_premium(self):
        """The floor must not turn a household with no CHIP-eligible child into a $1 hit."""
        e = self._eligibility(
            self.build(),
            {"1": 0.0, "2": 0.0, "3": 0.0},
            {MAIN_TAX_UNIT: 0.0},
        )
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)

    def test_premium_sums_across_tax_units(self):
        """``mo_chip_premium`` is per tax unit, and a household can split into two — an
        adult sibling is neither head, spouse, nor a dependent. Both units' premiums are
        charged, rather than only the main one's."""
        screen = self.build(household_size=4)
        add_member(screen, 4, "sibling", 30)
        add_income(screen.household_members.get(id=4), amount=Decimal("3000"))

        calculator = self.calculator(screen)
        calculator.set_engine(
            StubSim(
                gross_by_member={"1": 0.0, "2": 0.0, "3": 2_911.851, "4": 0.0},
                premium_by_tax_unit={MAIN_TAX_UNIT: 32.0, SECONDARY_TAX_UNIT: 25.0},
            )
        )
        self.assertEqual(calculator.annual_premium(), (32 + 25) * 12)

    def test_missing_secondary_tax_unit_is_not_an_error(self):
        """pe_input deletes the secondary tax unit when it is empty, so PolicyEngine
        returns nothing for it."""
        screen = self.build()
        calculator = self.calculator(screen)
        calculator.set_engine(
            StubSim(
                gross_by_member={"1": 0.0, "2": 0.0, "3": 2_911.851},
                premium_by_tax_unit={MAIN_TAX_UNIT: 32.0},
            )
        )
        self.assertEqual(calculator.annual_premium(), 384)


class TestMoChipRegistration(TestCase):
    def test_backs_the_mo_chip_row(self):
        self.assertEqual(MoChip.program_code, "mo_chip")

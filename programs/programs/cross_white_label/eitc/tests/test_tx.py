"""TX tests."""

from programs.programs.cross_white_label.eitc.base import Eitc
from screener.models import HouseholdMember
from screener.models import IncomeStream
from programs.framework.pe_dependencies.constants import MAIN_TAX_UNIT
from screener.models import Screen
from integrations.clients.policyengine.policy_engine import pe_input
from programs.programs.testing.pe_input_test_base import TxPeInputTestBase
from django.test import TestCase
from programs.programs.cross_white_label.eitc.tx import TxEitc
from programs.framework.pe_dependencies import household


class TestTxEitcPeInput(TxPeInputTestBase):
    """Tests for the tx_eitc calculator's pe_input dependencies.

    tx_eitc is the shared federal ``Eitc`` class, so this exercises the federal
    calculator against a TX screen.
    """

    def test_includes_all_pe_input_fields(self):
        """Test that pe_input includes all Eitc pe_inputs dependencies."""
        result = pe_input(self.screen, [Eitc])
        household = result["household"]
        tax_units = household["tax_units"]
        people = household["people"]

        # Tax unit exists
        self.assertIn(MAIN_TAX_UNIT, tax_units)

        # Member-level dependencies
        head_id = str(self.head.id)
        spouse_id = str(self.spouse.id)
        child_id = str(self.child.id)

        self.assertIn("age", people[head_id])
        self.assertIn("is_tax_unit_spouse", people[spouse_id])
        self.assertIn("is_tax_unit_dependent", people[child_id])

        # Income dependencies
        income_fields = [
            "employment_income",
            "self_employment_income",
            "rental_income",
            "taxable_pension_income",
            "social_security",
        ]
        for field in income_fields:
            self.assertIn(field, people[head_id])

    def test_includes_pe_output_field(self):
        """Test that pe_input includes Eitc pe_outputs."""
        result = pe_input(self.screen, [Eitc])
        tax_units = result["household"]["tax_units"]

        self.assertIn(MAIN_TAX_UNIT, tax_units)
        self.assertIn("eitc", tax_units[MAIN_TAX_UNIT])

    def test_tax_unit_relationships_are_correct(self):
        """Test that tax unit relationships are correctly set."""
        result = pe_input(self.screen, [Eitc])
        people = result["household"]["people"]

        spouse_id = str(self.spouse.id)
        child_id = str(self.child.id)

        if people[spouse_id]["is_tax_unit_spouse"]:
            period_key = list(people[spouse_id]["is_tax_unit_spouse"].keys())[0]
            self.assertTrue(people[spouse_id]["is_tax_unit_spouse"][period_key])

        if people[child_id]["is_tax_unit_dependent"]:
            period_key = list(people[child_id]["is_tax_unit_dependent"].keys())[0]
            self.assertTrue(people[child_id]["is_tax_unit_dependent"][period_key])

    def test_with_single_parent(self):
        """Test that Eitc handles single parent households correctly."""
        single_parent_screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Travis County",
            household_size=2,
            completed=False,
        )
        single_parent = HouseholdMember.objects.create(
            screen=single_parent_screen,
            relationship="headOfHousehold",
            age=28,
        )
        IncomeStream.objects.create(
            screen=single_parent_screen,
            household_member=single_parent,
            type="wages",
            amount=25000,
            frequency="yearly",
        )
        child = HouseholdMember.objects.create(
            screen=single_parent_screen,
            relationship="child",
            age=3,
        )

        result = pe_input(single_parent_screen, [Eitc])
        tax_units = result["household"]["tax_units"]

        self.assertIn(MAIN_TAX_UNIT, tax_units)
        self.assertIn(str(single_parent.id), tax_units[MAIN_TAX_UNIT]["members"])
        self.assertIn(str(child.id), tax_units[MAIN_TAX_UNIT]["members"])


class TestTxEitc(TestCase):
    """tx_eitc registration against the shared federal Eitc calculator.

    The federal EITC has no Texas variance, so the slug maps to the shared class
    with no TX subclass. Its own properties are asserted once in
    ``programs/programs/federal/pe/tests/test_tax.py``.
    """

    def test_is_the_federal_calculator_with_nothing_added(self):
        """A thin subclass of the federal calculator: same PE variable, same inputs.

        TX has no state EITC, so ``tx_eitc`` must not diverge from the federal
        credit. It is its own class only so the registry maps one key to one
        calculator. Asserting it overrides nothing is stricter than asserting
        identity with ``Eitc`` was: a subclass that added an input would still be a
        subclass, but would fail here.
        """
        self.assertTrue(issubclass(TxEitc, Eitc))
        self.assertEqual(TxEitc.pe_name, Eitc.pe_name)
        self.assertEqual(list(TxEitc.pe_inputs), list(Eitc.pe_inputs))
        self.assertEqual(list(TxEitc.pe_outputs), list(Eitc.pe_outputs))

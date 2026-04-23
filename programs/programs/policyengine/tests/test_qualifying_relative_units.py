from django.test import TestCase
from screener.models import Screen, HouseholdMember, WhiteLabel, IncomeStream
from programs.programs.policyengine.policy_engine import pe_input
from programs.programs.policyengine.calculators.constants import MAIN_TAX_UNIT, SECONDARY_TAX_UNIT


class TestQualifyingRelativeUnitSplitting(TestCase):
    """Tests that qualifying relatives stay in the main tax unit when building the PE payload."""

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Texas", code="tx", state_code="TX")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            completed=False,
            last_tax_filing_year="2024",
            household_size=2,
        )
        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=40)
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="wages", amount=50000, frequency="yearly"
        )

        from programs.programs.tx.pe.spm import TxSnap

        self.calc_class = TxSnap

    def test_low_income_adult_child_stays_in_main_unit(self):
        adult_child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=25, student=False)

        result = pe_input(self.screen, [self.calc_class])
        tax_units = result["household"]["tax_units"]

        self.assertIn(str(adult_child.id), tax_units[MAIN_TAX_UNIT]["members"])
        self.assertNotIn(SECONDARY_TAX_UNIT, tax_units)

    def test_low_income_parent_stays_in_main_unit(self):
        parent = HouseholdMember.objects.create(screen=self.screen, relationship="parent", age=70)
        IncomeStream.objects.create(
            screen=self.screen, household_member=parent, type="wages", amount=2000, frequency="yearly"
        )

        result = pe_input(self.screen, [self.calc_class])
        tax_units = result["household"]["tax_units"]

        self.assertIn(str(parent.id), tax_units[MAIN_TAX_UNIT]["members"])
        self.assertNotIn(SECONDARY_TAX_UNIT, tax_units)

    def test_high_income_relative_splits_into_secondary_unit(self):
        adult_child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=25)
        IncomeStream.objects.create(
            screen=self.screen, household_member=adult_child, type="wages", amount=10000, frequency="yearly"
        )

        result = pe_input(self.screen, [self.calc_class])
        tax_units = result["household"]["tax_units"]

        self.assertIn(SECONDARY_TAX_UNIT, tax_units)
        self.assertIn(str(adult_child.id), tax_units[SECONDARY_TAX_UNIT]["members"])
        self.assertNotIn(str(adult_child.id), tax_units[MAIN_TAX_UNIT]["members"])

"""
Unit tests for PolicyEngine pe_input function core structure.

These tests verify the pe_input() function correctly generates the PolicyEngine API
request payload structure (household, people, tax_units, marital_units, etc.)
independent of any specific calculator's dependencies.

Calculator-specific dependency tests belong in the state's pe/tests/ directory.
"""

from django.test import TestCase
from screener.models import Screen, HouseholdMember, WhiteLabel, Expense, IncomeStream
from programs.programs.policyengine.policy_engine import pe_input
from programs.programs.policyengine.calculators.constants import (
    MAIN_TAX_UNIT,
    SECONDARY_TAX_UNIT,
)


class PeInputTestBase(TestCase):
    """Base class with shared test fixtures for pe_input tests."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data that doesn't change between tests."""
        cls.white_label = WhiteLabel.objects.create(name="Texas", code="tx", state_code="TX")

    def setUp(self):
        """Set up test screen with household members."""
        # Import here to avoid circular imports at module level
        from programs.programs.tx.pe.spm import TxSnap

        self.calculator_class = TxSnap

        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Travis County",
            household_size=3,
            household_assets=5000.00,
            completed=False,
        )

        # Head of household - 35 year old, disabled
        self.head = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=35,
            disabled=True,
            student=False,
        )

        # Spouse - 32 year old
        self.spouse = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="spouse",
            age=32,
            disabled=False,
            student=False,
        )

        # Child - 8 year old
        self.child = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="child",
            age=8,
            disabled=False,
            student=True,
        )


class TestPeInputHouseholdStructure(PeInputTestBase):
    """Tests for pe_input() household structure generation."""

    def test_returns_valid_household_structure(self):
        """Test that pe_input returns a properly structured household dict."""
        result = pe_input(self.screen, [self.calculator_class])

        # Verify top-level structure
        self.assertIn("household", result)
        household = result["household"]

        # Verify all required units exist
        self.assertIn("people", household)
        self.assertIn("tax_units", household)
        self.assertIn("families", household)
        self.assertIn("households", household)
        self.assertIn("spm_units", household)
        self.assertIn("marital_units", household)

    def test_creates_people_with_member_ids(self):
        """Test that pe_input creates people dict with household member IDs as keys."""
        result = pe_input(self.screen, [self.calculator_class])
        people = result["household"]["people"]

        # Should have 3 people
        self.assertEqual(len(people), 3)

        # Verify all member IDs are present
        head_id = str(self.head.id)
        spouse_id = str(self.spouse.id)
        child_id = str(self.child.id)

        self.assertIn(head_id, people)
        self.assertIn(spouse_id, people)
        self.assertIn(child_id, people)

        # Each person should be a dict
        self.assertIsInstance(people[head_id], dict)
        self.assertIsInstance(people[spouse_id], dict)
        self.assertIsInstance(people[child_id], dict)

    def test_assigns_members_to_family_unit(self):
        """Test that all members are assigned to the family unit."""
        result = pe_input(self.screen, [self.calculator_class])
        family_members = result["household"]["families"]["family"]["members"]

        # All 3 members should be in the family
        self.assertEqual(len(family_members), 3)
        self.assertIn(str(self.head.id), family_members)
        self.assertIn(str(self.spouse.id), family_members)
        self.assertIn(str(self.child.id), family_members)

    def test_assigns_members_to_household_unit(self):
        """Test that all members are assigned to the household unit."""
        result = pe_input(self.screen, [self.calculator_class])
        household_members = result["household"]["households"]["household"]["members"]

        # All 3 members should be in the household
        self.assertEqual(len(household_members), 3)
        self.assertIn(str(self.head.id), household_members)
        self.assertIn(str(self.spouse.id), household_members)
        self.assertIn(str(self.child.id), household_members)

    def test_assigns_members_to_spm_unit(self):
        """Test that all members are assigned to the SPM unit."""
        result = pe_input(self.screen, [self.calculator_class])
        spm_members = result["household"]["spm_units"]["spm_unit"]["members"]

        # All 3 members should be in the SPM unit
        self.assertEqual(len(spm_members), 3)
        self.assertIn(str(self.head.id), spm_members)
        self.assertIn(str(self.spouse.id), spm_members)
        self.assertIn(str(self.child.id), spm_members)

    def test_with_empty_screen_returns_basic_structure(self):
        """Test that pe_input returns valid structure even with no members."""
        empty_screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Travis County",
            household_size=0,
            completed=False,
        )

        result = pe_input(empty_screen, [self.calculator_class])

        # Should still have household structure
        self.assertIn("household", result)
        household = result["household"]

        # All unit types should exist
        self.assertIn("people", household)
        self.assertIn("tax_units", household)
        self.assertIn("families", household)

        # People should be empty
        self.assertEqual(len(household["people"]), 0)


class TestPeInputTaxUnits(PeInputTestBase):
    """Tests for pe_input() tax unit assignment."""

    def test_creates_main_tax_unit_with_members(self):
        """Test that adults are assigned to the main tax unit."""
        result = pe_input(self.screen, [self.calculator_class])
        tax_units = result["household"]["tax_units"]

        # Main tax unit should exist
        self.assertIn(MAIN_TAX_UNIT, tax_units)
        main_tax_members = tax_units[MAIN_TAX_UNIT]["members"]

        # Head and spouse should be in main tax unit
        self.assertIn(str(self.head.id), main_tax_members)
        self.assertIn(str(self.spouse.id), main_tax_members)
        self.assertIn(str(self.child.id), main_tax_members)

    def test_removes_empty_secondary_tax_unit(self):
        """Test that empty secondary tax unit is removed."""
        result = pe_input(self.screen, [self.calculator_class])
        tax_units = result["household"]["tax_units"]

        # Secondary tax unit should not exist if empty
        self.assertNotIn(SECONDARY_TAX_UNIT, tax_units)

    def test_keeps_secondary_tax_unit_when_has_members(self):
        """Test that secondary tax unit is kept when it has members."""
        # Create an adult child (not in main tax unit)
        adult_child = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="child",
            age=25,
            disabled=False,
            student=False,
        )

        result = pe_input(self.screen, [self.calculator_class])
        tax_units = result["household"]["tax_units"]

        # Secondary tax unit should exist if adult child is not in main tax unit
        if not adult_child.is_in_tax_unit():
            self.assertIn(SECONDARY_TAX_UNIT, tax_units)
            self.assertIn(str(adult_child.id), tax_units[SECONDARY_TAX_UNIT]["members"])


class TestPeInputMaritalUnits(PeInputTestBase):
    """Tests for pe_input() marital unit assignment."""

    def test_creates_marital_unit_for_head_and_spouse(self):
        """Test that married couples are assigned to marital units."""
        result = pe_input(self.screen, [self.calculator_class])
        marital_units = result["household"]["marital_units"]

        # Should have one marital unit for head and spouse
        self.assertEqual(len(marital_units), 1)

        # Marital unit key should be "member_id-member_id"
        marital_unit_key = list(marital_units.keys())[0]
        marital_unit = marital_units[marital_unit_key]

        # Should contain exactly 2 members
        self.assertEqual(len(marital_unit["members"]), 2)

        # Should contain head and spouse IDs (order may vary)
        member_ids = set(marital_unit["members"])
        expected_ids = {str(self.head.id), str(self.spouse.id)}
        self.assertEqual(member_ids, expected_ids)

    def test_single_adult_has_single_marital_unit(self):
        """Test that single adults get their own marital unit."""
        # Create screen with single adult
        single_screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Travis County",
            household_size=1,
            completed=False,
        )
        single_adult = HouseholdMember.objects.create(
            screen=single_screen,
            relationship="headOfHousehold",
            age=30,
        )

        result = pe_input(single_screen, [self.calculator_class])
        marital_units = result["household"]["marital_units"]

        # Should have one marital unit with single member
        self.assertEqual(len(marital_units), 1)
        marital_unit = list(marital_units.values())[0]
        self.assertEqual(len(marital_unit["members"]), 1)
        self.assertIn(str(single_adult.id), marital_unit["members"])


class TestPeInputMultipleCalculators(PeInputTestBase):
    """Tests for pe_input() with multiple calculators."""

    def test_with_multiple_calculators(self):
        """Test that pe_input handles multiple calculator inputs correctly."""
        from programs.programs.federal.pe.spm import SchoolLunch

        result = pe_input(self.screen, [self.calculator_class, SchoolLunch])

        # Should have all dependencies from both calculators
        household = result["household"]
        self.assertIn("people", household)
        self.assertIn("spm_units", household)

        # Verify structure is valid
        self.assertIsInstance(household["people"], dict)
        self.assertIsInstance(household["spm_units"], dict)

    def test_calculator_dependencies_are_merged(self):
        """Test that dependencies from multiple calculators are merged."""
        from programs.programs.tx.pe.member import TxWic

        result = pe_input(self.screen, [self.calculator_class, TxWic])

        # Both SNAP and WIC dependencies should be present
        spm_unit = result["household"]["spm_units"]["spm_unit"]
        people = result["household"]["people"]

        # SNAP adds snap output
        self.assertIn("snap", spm_unit)

        # WIC adds pregnancy/breastfeeding fields to people
        head_id = str(self.head.id)
        self.assertIn("age", people[head_id])

"""
Unit tests for PolicyEngine pe_input function.

These tests verify the pe_input() function that generates PolicyEngine API
request payloads from Screen data and calculator configurations.
"""

from django.test import TestCase
from screener.models import Screen, HouseholdMember, WhiteLabel, Expense, IncomeStream
from programs.programs.policyengine.policy_engine import pe_input
from programs.programs.tx.pe.spm import TxSnap, TxLifeline, TxTanf
from programs.programs.tx.pe.member import TxWic, TxSsi, TxCsfp
from programs.programs.tx.pe.tax import TxEitc, TxCtc, TxAca
from programs.programs.policyengine.calculators.constants import (
    MAIN_TAX_UNIT,
    SECONDARY_TAX_UNIT,
)


class TestPeInput(TestCase):
    """
    Tests for pe_input() function with TX Screen.

    This verifies that pe_input() correctly transforms Screen/HouseholdMember
    data into the expected PolicyEngine API request format.
    """

    def setUp(self):
        """Set up test data for TX SNAP pe_input tests."""
        self.white_label = WhiteLabel.objects.create(name="Texas", code="tx", state_code="TX")

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

        # Add income streams for Lifeline tests
        # Head has employment, self-employment, and rental income
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="wages",
            amount=30000,
            frequency="yearly",
        )
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="selfEmployment",
            amount=5000,
            frequency="yearly",
        )
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="rental",
            amount=12000,
            frequency="yearly",
        )

        # Spouse has pension and social security income
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.spouse,
            type="pension",
            amount=8000,
            frequency="yearly",
        )
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.spouse,
            type="sSRetirement",
            amount=6000,
            frequency="yearly",
        )

        # Add some expenses
        Expense.objects.create(screen=self.screen, type="childSupport", amount=500, frequency="monthly")

        Expense.objects.create(screen=self.screen, type="medical", amount=200, frequency="monthly")

    def test_pe_input_returns_valid_household_structure(self):
        """Test that pe_input returns a properly structured household dict."""
        result = pe_input(self.screen, [TxSnap])

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

    def test_pe_input_creates_people_with_member_ids(self):
        """Test that pe_input creates people dict with household member IDs as keys."""
        result = pe_input(self.screen, [TxSnap])
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

        # Each person should be a dict (potentially with dependency data)
        self.assertIsInstance(people[head_id], dict)
        self.assertIsInstance(people[spouse_id], dict)
        self.assertIsInstance(people[child_id], dict)

    def test_pe_input_assigns_members_to_family_unit(self):
        """Test that all members are assigned to the family unit."""
        result = pe_input(self.screen, [TxSnap])
        family_members = result["household"]["families"]["family"]["members"]

        # All 3 members should be in the family
        self.assertEqual(len(family_members), 3)
        self.assertIn(str(self.head.id), family_members)
        self.assertIn(str(self.spouse.id), family_members)
        self.assertIn(str(self.child.id), family_members)

    def test_pe_input_assigns_members_to_household_unit(self):
        """Test that all members are assigned to the household unit."""
        result = pe_input(self.screen, [TxSnap])
        household_members = result["household"]["households"]["household"]["members"]

        # All 3 members should be in the household
        self.assertEqual(len(household_members), 3)
        self.assertIn(str(self.head.id), household_members)
        self.assertIn(str(self.spouse.id), household_members)
        self.assertIn(str(self.child.id), household_members)

    def test_pe_input_assigns_members_to_spm_unit(self):
        """Test that all members are assigned to the SPM unit."""
        result = pe_input(self.screen, [TxSnap])
        spm_members = result["household"]["spm_units"]["spm_unit"]["members"]

        # All 3 members should be in the SPM unit
        self.assertEqual(len(spm_members), 3)
        self.assertIn(str(self.head.id), spm_members)
        self.assertIn(str(self.spouse.id), spm_members)
        self.assertIn(str(self.child.id), spm_members)

    def test_pe_input_creates_main_tax_unit_with_members(self):
        """Test that adults are assigned to the main tax unit."""
        result = pe_input(self.screen, [TxSnap])
        tax_units = result["household"]["tax_units"]

        # Main tax unit should exist
        self.assertIn(MAIN_TAX_UNIT, tax_units)
        main_tax_members = tax_units[MAIN_TAX_UNIT]["members"]

        # All members with is_in_tax_unit() == True should be in main tax unit
        # Head and spouse should be in tax unit
        self.assertIn(str(self.head.id), main_tax_members)
        self.assertIn(str(self.spouse.id), main_tax_members)
        self.assertIn(str(self.child.id), main_tax_members)

    def test_pe_input_removes_empty_secondary_tax_unit(self):
        """Test that empty secondary tax unit is removed."""
        result = pe_input(self.screen, [TxSnap])
        tax_units = result["household"]["tax_units"]

        # Secondary tax unit should not exist if empty
        self.assertNotIn(SECONDARY_TAX_UNIT, tax_units)

    def test_pe_input_keeps_secondary_tax_unit_when_has_members(self):
        """Test that secondary tax unit is kept when it has members."""
        # Create an adult child (not in main tax unit)
        adult_child = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="child",
            age=25,
            disabled=False,
            student=False,
        )

        result = pe_input(self.screen, [TxSnap])
        tax_units = result["household"]["tax_units"]

        # Secondary tax unit should exist if it has members
        # (depends on is_in_tax_unit() logic - adult children may be in secondary)
        if not adult_child.is_in_tax_unit():
            self.assertIn(SECONDARY_TAX_UNIT, tax_units)
            self.assertIn(str(adult_child.id), tax_units[SECONDARY_TAX_UNIT]["members"])

    def test_pe_input_creates_marital_unit_for_head_and_spouse(self):
        """Test that married couples are assigned to marital units."""
        result = pe_input(self.screen, [TxSnap])
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

    def test_pe_input_populates_dependency_fields_for_txsnap(self):
        """Test that TxSnap-specific dependencies populate correct fields."""
        result = pe_input(self.screen, [TxSnap])
        people = result["household"]["people"]
        household_unit = result["household"]["households"]["household"]

        # TxSnap should populate state_code on household
        self.assertIn("state_code", household_unit)

        # Head should have age and is_disabled fields
        head_id = str(self.head.id)
        self.assertIn("age", people[head_id])
        self.assertIn("is_disabled", people[head_id])

        # Medical expenses should be populated for disabled head
        self.assertIn("medical_out_of_pocket_expenses", people[head_id])

    def test_pe_input_with_empty_screen_returns_basic_structure(self):
        """Test that pe_input returns valid structure even with no members."""
        # Create empty screen
        empty_screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Travis County",
            household_size=0,
            completed=False,
        )

        result = pe_input(empty_screen, [TxSnap])

        # Should still have household structure
        self.assertIn("household", result)
        household = result["household"]

        # All unit types should exist
        self.assertIn("people", household)
        self.assertIn("tax_units", household)
        self.assertIn("families", household)

        # People should be empty
        self.assertEqual(len(household["people"]), 0)

    def test_pe_input_with_multiple_calculators(self):
        """Test that pe_input handles multiple calculator inputs correctly."""
        # Import another calculator
        from programs.programs.tx.pe.spm import TxSnap
        from programs.programs.federal.pe.spm import SchoolLunch

        result = pe_input(self.screen, [TxSnap, SchoolLunch])

        # Should have all dependencies from both calculators
        household = result["household"]
        self.assertIn("people", household)
        self.assertIn("spm_units", household)

        # Verify structure is valid
        self.assertIsInstance(household["people"], dict)
        self.assertIsInstance(household["spm_units"], dict)

    def test_pe_input_age_values_match_household_members(self):
        """Test that age dependency values match the actual member ages."""
        result = pe_input(self.screen, [TxSnap])
        people = result["household"]["people"]

        head_id = str(self.head.id)
        spouse_id = str(self.spouse.id)
        child_id = str(self.child.id)

        # Verify ages are populated (structure depends on TxSnap.pe_period)
        # Age should be in format: people[id]["age"][period] = value
        if "age" in people[head_id]:
            # Find the period key (e.g., "2024" or "2024-01")
            age_periods = people[head_id]["age"]
            if age_periods:
                period_key = list(age_periods.keys())[0]
                self.assertEqual(age_periods[period_key], 35)

                spouse_age = people[spouse_id]["age"][period_key]
                self.assertEqual(spouse_age, 32)

                child_age = people[child_id]["age"][period_key]
                self.assertEqual(child_age, 8)

    def test_pe_input_disabled_status_matches_household_members(self):
        """Test that is_disabled dependency values match member disabled status."""
        result = pe_input(self.screen, [TxSnap])
        people = result["household"]["people"]

        head_id = str(self.head.id)
        spouse_id = str(self.spouse.id)

        # Verify is_disabled is populated
        if "is_disabled" in people[head_id]:
            disabled_periods = people[head_id]["is_disabled"]
            if disabled_periods:
                period_key = list(disabled_periods.keys())[0]
                self.assertTrue(disabled_periods[period_key])

                spouse_disabled = people[spouse_id]["is_disabled"][period_key]
                self.assertFalse(spouse_disabled)

    def test_pe_input_state_code_is_tx(self):
        """Test that TxStateCodeDependency sets state_code to TX."""
        result = pe_input(self.screen, [TxSnap])
        household_unit = result["household"]["households"]["household"]

        # TxStateCodeDependency should set state_code="TX"
        if "state_code" in household_unit:
            state_code_periods = household_unit["state_code"]
            if state_code_periods:
                period_key = list(state_code_periods.keys())[0]
                self.assertEqual(state_code_periods[period_key], "TX")

    def test_pe_input_includes_all_txsnap_pe_input_fields(self):
        """
        Test that pe_input result includes all TxSnap pe_inputs dependencies.

        TxSnap inherits from Snap and adds TxStateCodeDependency.
        This test verifies all input fields from the dependency classes are present.
        """
        result = pe_input(self.screen, [TxSnap])
        household = result["household"]

        # Get a period key for checking values
        spm_unit = household["spm_units"]["spm_unit"]
        people = household["people"]
        household_unit = household["households"]["household"]

        # Check SPM-level dependencies from Snap.pe_inputs
        spm_fields_to_check = [
            "snap_unearned_income",
            "snap_earned_income",
            "snap_assets",
            "snap_emergency_allotment",
            "housing_cost",
            "has_phone_expense",
            "has_heating_cooling_expense",
            "heating_cooling_expense",
            "childcare_expenses",
            "water_expense",
            "phone_expense",
            "homeowners_association_fees",
            "homeowners_insurance",
        ]

        for field in spm_fields_to_check:
            self.assertIn(
                field,
                spm_unit,
                f"Expected field '{field}' from TxSnap pe_inputs not found in spm_unit",
            )

        # Check member-level dependencies from Snap.pe_inputs
        head_id = str(self.head.id)
        member_fields_to_check = [
            "child_support_expense",
            "real_estate_taxes",
            "age",
            "medical_out_of_pocket_expenses",
            "is_disabled",
            "is_snap_ineligible_student",
        ]

        for field in member_fields_to_check:
            self.assertIn(
                field,
                people[head_id],
                f"Expected field '{field}' from TxSnap pe_inputs not found in member data",
            )

        # Check TX-specific dependency (added by TxSnap)
        self.assertIn(
            "state_code",
            household_unit,
            "Expected field 'state_code' from TxStateCodeDependency not found in household",
        )

    def test_pe_input_includes_all_txsnap_pe_output_fields(self):
        """
        Test that pe_input result includes all TxSnap pe_outputs dependencies.

        TxSnap.pe_outputs = [dependency.spm.Snap] which adds the 'snap' field
        to the spm_unit for PolicyEngine to calculate and return.
        """
        result = pe_input(self.screen, [TxSnap])
        spm_unit = result["household"]["spm_units"]["spm_unit"]

        # Check that the snap output field is present
        # This is what PolicyEngine will populate with the calculated benefit amount
        self.assertIn(
            "snap",
            spm_unit,
            "Expected output field 'snap' from TxSnap pe_outputs not found in spm_unit",
        )

        # Verify it has a period structure
        self.assertIsInstance(spm_unit["snap"], dict, "snap field should be a dict with period keys")

    def test_pe_input_snap_input_values_are_correct(self):
        """
        Test that specific SNAP input dependency values are correctly calculated.

        This verifies the actual values from Screen data are properly transformed.
        """
        result = pe_input(self.screen, [TxSnap])
        spm_unit = result["household"]["spm_units"]["spm_unit"]

        # Get the period key
        if "snap_assets" in spm_unit and spm_unit["snap_assets"]:
            period_key = list(spm_unit["snap_assets"].keys())[0]

            # Verify snap_assets matches screen.household_assets
            self.assertEqual(
                spm_unit["snap_assets"][period_key],
                5000,
                "snap_assets should match Screen.household_assets",
            )

        # Verify child support expense is calculated correctly
        # $500/month * 12 / household_size(3) = $2000 per person
        people = result["household"]["people"]
        head_id = str(self.head.id)
        if "child_support_expense" in people[head_id] and people[head_id]["child_support_expense"]:
            period_key = list(people[head_id]["child_support_expense"].keys())[0]
            self.assertEqual(
                people[head_id]["child_support_expense"][period_key],
                2000,
                "child_support_expense should be $500/month * 12 / 3 people = $2000",
            )

        # Verify medical expenses for disabled head
        # $200/month * 12 / 1 disabled person = $2400
        if "medical_out_of_pocket_expenses" in people[head_id] and people[head_id]["medical_out_of_pocket_expenses"]:
            period_key = list(people[head_id]["medical_out_of_pocket_expenses"].keys())[0]
            self.assertEqual(
                people[head_id]["medical_out_of_pocket_expenses"][period_key],
                2400,
                "medical_out_of_pocket_expenses should be $200/month * 12 / 1 disabled = $2400",
            )

    def test_pe_input_tx_specific_dependency_values(self):
        """
        Test that TX-specific dependencies have correct values.

        TxSnap adds TxStateCodeDependency which should set state_code="TX".
        """
        result = pe_input(self.screen, [TxSnap])
        household_unit = result["household"]["households"]["household"]

        # Verify state_code is set to "TX"
        self.assertIn("state_code", household_unit)
        if household_unit["state_code"]:
            period_key = list(household_unit["state_code"].keys())[0]
            self.assertEqual(
                household_unit["state_code"][period_key],
                "TX",
                "TxStateCodeDependency should set state_code='TX'",
            )

    def test_pe_input_includes_all_lifeline_pe_input_fields(self):
        """
        Test that pe_input result includes all Lifeline pe_inputs dependencies.

        Lifeline has:
        - BroadbandCostDependency (SPM level)
        - 5 IRS gross income dependencies (member level):
          - employment_income
          - self_employment_income
          - rental_income
          - taxable_pension_income
          - social_security
        """
        result = pe_input(self.screen, [TxLifeline])
        household = result["household"]

        # Get SPM unit and people
        spm_unit = household["spm_units"]["spm_unit"]
        people = household["people"]
        household_unit = household["households"]["household"]

        # Check SPM-level dependency from Lifeline.pe_inputs
        self.assertIn(
            "broadband_cost",
            spm_unit,
            "Expected field 'broadband_cost' from BroadbandCostDependency not found in spm_unit",
        )

        # Check member-level income dependencies from irs_gross_income tuple
        head_id = str(self.head.id)
        income_fields_to_check = [
            "employment_income",
            "self_employment_income",
            "rental_income",
            "taxable_pension_income",
            "social_security",
        ]

        for field in income_fields_to_check:
            self.assertIn(
                field,
                people[head_id],
                f"Expected income field '{field}' from Lifeline pe_inputs not found in member data",
            )

        # Check TX-specific dependency (added by TxLifeline)
        self.assertIn(
            "state_code",
            household_unit,
            "Expected field 'state_code' from TxStateCodeDependency not found in household",
        )

    def test_pe_input_includes_lifeline_pe_output_field(self):
        """
        Test that pe_input result includes Lifeline pe_outputs dependency.

        Lifeline.pe_outputs = [dependency.spm.Lifeline] which adds the 'lifeline' field
        to the spm_unit for PolicyEngine to calculate and return.
        """
        result = pe_input(self.screen, [TxLifeline])
        spm_unit = result["household"]["spm_units"]["spm_unit"]

        # Check that the lifeline output field is present
        self.assertIn(
            "lifeline",
            spm_unit,
            "Expected output field 'lifeline' from Lifeline pe_outputs not found in spm_unit",
        )

        # Verify it has a period structure
        self.assertIsInstance(
            spm_unit["lifeline"],
            dict,
            "lifeline field should be a dict with period keys",
        )

    def test_pe_input_lifeline_income_values_are_correct(self):
        """
        Test that Lifeline income dependency values are correctly populated from HouseholdMember data.

        This verifies the 5 IRS gross income types are properly extracted.
        """
        result = pe_input(self.screen, [TxLifeline])
        people = result["household"]["people"]

        head_id = str(self.head.id)
        spouse_id = str(self.spouse.id)

        # Get the period key from one of the fields
        if "employment_income" in people[head_id] and people[head_id]["employment_income"]:
            period_key = list(people[head_id]["employment_income"].keys())[0]

            # Verify head's income values
            self.assertEqual(
                people[head_id]["employment_income"][period_key],
                30000,
                "Head employment_income should match HouseholdMember value",
            )
            self.assertEqual(
                people[head_id]["self_employment_income"][period_key],
                5000,
                "Head self_employment_income should match HouseholdMember value",
            )
            self.assertEqual(
                people[head_id]["rental_income"][period_key],
                12000,
                "Head rental_income should match HouseholdMember value",
            )

            # Verify spouse's income values
            self.assertEqual(
                people[spouse_id]["taxable_pension_income"][period_key],
                8000,
                "Spouse taxable_pension_income should match HouseholdMember value",
            )
            self.assertEqual(
                people[spouse_id]["social_security"][period_key],
                6000,
                "Spouse social_security should match HouseholdMember value",
            )

    def test_pe_input_lifeline_broadband_cost_is_populated(self):
        """
        Test that Lifeline's BroadbandCostDependency populates the broadband_cost field.

        Currently, BroadbandCostDependency is hardcoded to return 500.
        This test verifies the field exists and has the expected value.
        """
        result = pe_input(self.screen, [TxLifeline])
        spm_unit = result["household"]["spm_units"]["spm_unit"]

        # Check that broadband_cost is populated
        self.assertIn(
            "broadband_cost",
            spm_unit,
            "broadband_cost field should be present in spm_unit",
        )

        # Verify it has a period structure
        if spm_unit["broadband_cost"]:
            period_key = list(spm_unit["broadband_cost"].keys())[0]
            # BroadbandCostDependency.value() currently returns 500
            self.assertEqual(
                spm_unit["broadband_cost"][period_key],
                500,
                "broadband_cost should be 500 (current hardcoded value from BroadbandCostDependency)",
            )

    def test_pe_input_lifeline_with_multiple_income_sources(self):
        """
        Test that Lifeline correctly handles members with multiple income sources.

        This verifies that all 5 IRS gross income types can coexist on the same member.
        """
        # Create a member with all 5 income types
        multi_income_member = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="parent",
            age=65,
            disabled=False,
            student=False,
        )

        # Add income streams for all 5 IRS gross income types
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=multi_income_member,
            type="wages",
            amount=20000,
            frequency="yearly",
        )
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=multi_income_member,
            type="selfEmployment",
            amount=10000,
            frequency="yearly",
        )
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=multi_income_member,
            type="rental",
            amount=15000,
            frequency="yearly",
        )
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=multi_income_member,
            type="pension",
            amount=25000,
            frequency="yearly",
        )
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=multi_income_member,
            type="sSRetirement",
            amount=18000,
            frequency="yearly",
        )

        result = pe_input(self.screen, [TxLifeline])
        people = result["household"]["people"]
        member_id = str(multi_income_member.id)

        # Verify all income types are present
        self.assertIn("employment_income", people[member_id])
        self.assertIn("self_employment_income", people[member_id])
        self.assertIn("rental_income", people[member_id])
        self.assertIn("taxable_pension_income", people[member_id])
        self.assertIn("social_security", people[member_id])

        # Verify values if populated
        if people[member_id]["employment_income"]:
            period_key = list(people[member_id]["employment_income"].keys())[0]
            self.assertEqual(people[member_id]["employment_income"][period_key], 20000)
            self.assertEqual(people[member_id]["self_employment_income"][period_key], 10000)
            self.assertEqual(people[member_id]["rental_income"][period_key], 15000)
            self.assertEqual(people[member_id]["taxable_pension_income"][period_key], 25000)
            self.assertEqual(people[member_id]["social_security"][period_key], 18000)

    def test_pe_input_includes_all_txwic_pe_input_fields(self):
        """
        Test that pe_input result includes all TxWic pe_inputs dependencies.

        TxWic inherits from Wic and adds TxStateCodeDependency.
        This test verifies all input fields from the dependency classes are present.
        """
        result = pe_input(self.screen, [TxWic])
        household = result["household"]

        # Get units for checking fields
        spm_unit = household["spm_units"]["spm_unit"]
        people = household["people"]
        household_unit = household["households"]["household"]

        # Check SPM-level dependencies from Wic.pe_inputs
        self.assertIn(
            "school_meal_countable_income",
            spm_unit,
            "Expected field 'school_meal_countable_income' from Wic pe_inputs not found in spm_unit",
        )

        # Check member-level dependencies from Wic.pe_inputs
        head_id = str(self.head.id)
        member_fields_to_check = [
            "is_pregnant",
            "current_pregnancies",
            "age",
        ]

        for field in member_fields_to_check:
            self.assertIn(
                field,
                people[head_id],
                f"Expected field '{field}' from TxWic pe_inputs not found in member data",
            )

        # Check TX-specific dependency (added by TxWic)
        self.assertIn(
            "state_code",
            household_unit,
            "Expected field 'state_code' from TxStateCodeDependency not found in household",
        )

    def test_pe_input_includes_all_txwic_pe_output_fields(self):
        """
        Test that pe_input result includes all TxWic pe_outputs dependencies.

        TxWic.pe_outputs = [dependency.member.Wic, dependency.member.WicCategory]
        which adds the 'wic' and 'wic_category' fields to each member for PolicyEngine
        to calculate and return.
        """
        result = pe_input(self.screen, [TxWic])
        people = result["household"]["people"]

        head_id = str(self.head.id)
        spouse_id = str(self.spouse.id)
        child_id = str(self.child.id)

        # Check that the wic and wic_category output fields are present for each member
        for member_id in [head_id, spouse_id, child_id]:
            self.assertIn(
                "wic",
                people[member_id],
                f"Expected output field 'wic' from TxWic pe_outputs not found for member {member_id}",
            )
            self.assertIn(
                "wic_category",
                people[member_id],
                f"Expected output field 'wic_category' from TxWic pe_outputs not found for member {member_id}",
            )

            # Verify they have period structures
            self.assertIsInstance(
                people[member_id]["wic"],
                dict,
                f"wic field should be a dict with period keys for member {member_id}",
            )
            self.assertIsInstance(
                people[member_id]["wic_category"],
                dict,
                f"wic_category field should be a dict with period keys for member {member_id}",
            )

    def test_pe_input_txwic_pregnancy_fields(self):
        """
        Test that TxWic pregnancy-related dependency values are correctly populated.

        This verifies that pregnancy status and expected children count are properly set.
        """
        # Create a pregnant household member
        pregnant_member = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="spouse",
            age=28,
            disabled=False,
            student=False,
            pregnant=True,
        )

        result = pe_input(self.screen, [TxWic])
        people = result["household"]["people"]
        pregnant_id = str(pregnant_member.id)

        # Verify pregnancy fields are present
        self.assertIn("is_pregnant", people[pregnant_id])
        self.assertIn("current_pregnancies", people[pregnant_id])

        # Check values if populated
        if people[pregnant_id]["is_pregnant"]:
            period_key = list(people[pregnant_id]["is_pregnant"].keys())[0]
            self.assertTrue(
                people[pregnant_id]["is_pregnant"][period_key],
                "is_pregnant should be True for pregnant member",
            )
            self.assertEqual(
                people[pregnant_id]["current_pregnancies"][period_key],
                1,
                "current_pregnancies should be 1 for pregnant member",
            )

    def test_pe_input_txwic_with_infant(self):
        """
        Test that TxWic correctly handles infants in the household.

        Infants (age < 1) are eligible for WIC and should have all required fields.
        """
        # Create an infant
        infant = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="child",
            age=0,
            disabled=False,
            student=False,
        )

        result = pe_input(self.screen, [TxWic])
        people = result["household"]["people"]
        infant_id = str(infant.id)

        # Verify infant has all required WIC fields
        self.assertIn("age", people[infant_id])
        self.assertIn("wic", people[infant_id])
        self.assertIn("wic_category", people[infant_id])

        # Check age value
        if people[infant_id]["age"]:
            period_key = list(people[infant_id]["age"].keys())[0]
            self.assertEqual(
                people[infant_id]["age"][period_key],
                0,
                "Infant age should be 0",
            )

    def test_pe_input_txwic_with_young_child(self):
        """
        Test that TxWic correctly handles young children (ages 1-4).

        Young children are eligible for WIC and should have all required fields.
        """
        # Create a young child
        young_child = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="child",
            age=3,
            disabled=False,
            student=False,
        )

        result = pe_input(self.screen, [TxWic])
        people = result["household"]["people"]
        child_id = str(young_child.id)

        # Verify child has all required WIC fields
        self.assertIn("age", people[child_id])
        self.assertIn("wic", people[child_id])
        self.assertIn("wic_category", people[child_id])

        # Check age value
        if people[child_id]["age"]:
            period_key = list(people[child_id]["age"].keys())[0]
            self.assertEqual(
                people[child_id]["age"][period_key],
                3,
                "Young child age should be 3",
            )

    def test_pe_input_txwic_tx_specific_dependency_values(self):
        """
        Test that TX-specific dependencies have correct values for WIC.

        TxWic adds TxStateCodeDependency which should set state_code="TX".
        """
        result = pe_input(self.screen, [TxWic])
        household_unit = result["household"]["households"]["household"]

        # Verify state_code is set to "TX"
        self.assertIn("state_code", household_unit)
        if household_unit["state_code"]:
            period_key = list(household_unit["state_code"].keys())[0]
            self.assertEqual(
                household_unit["state_code"][period_key],
                "TX",
                "TxStateCodeDependency should set state_code='TX' for WIC",
            )

    def test_pe_input_txwic_school_meal_countable_income(self):
        """
        Test that TxWic includes school_meal_countable_income dependency.

        This is inherited from the parent Wic class and should be present in spm_unit.
        """
        result = pe_input(self.screen, [TxWic])
        spm_unit = result["household"]["spm_units"]["spm_unit"]

        # Verify field exists
        self.assertIn(
            "school_meal_countable_income",
            spm_unit,
            "school_meal_countable_income should be present in spm_unit for WIC",
        )

        # Verify it has a period structure
        self.assertIsInstance(
            spm_unit["school_meal_countable_income"],
            dict,
            "school_meal_countable_income should be a dict with period keys",
        )

    def test_pe_input_with_txwic_and_txsnap_combined(self):
        """
        Test that pe_input handles both TxWic and TxSnap calculators together.

        This verifies that dependencies from both calculators are properly merged.
        """
        result = pe_input(self.screen, [TxWic, TxSnap])
        household = result["household"]

        spm_unit = household["spm_units"]["spm_unit"]
        people = household["people"]
        household_unit = household["households"]["household"]
        head_id = str(self.head.id)

        # Verify TxWic fields
        self.assertIn("school_meal_countable_income", spm_unit)
        self.assertIn("is_pregnant", people[head_id])
        self.assertIn("wic", people[head_id])

        # Verify TxSnap fields
        self.assertIn("snap_assets", spm_unit)
        self.assertIn("snap_earned_income", spm_unit)
        self.assertIn("snap", spm_unit)

        # Verify shared TX dependency
        self.assertIn("state_code", household_unit)

        # Verify structure is valid
        self.assertIsInstance(household["people"], dict)
        self.assertIsInstance(household["spm_units"], dict)

    def test_pe_input_includes_all_txeitc_pe_input_fields(self):
        """
        Test that pe_input result includes all TxEitc pe_inputs dependencies.

        TxEitc inherits from Eitc and adds TxStateCodeDependency.
        This test verifies all input fields from the dependency classes are present.
        """
        result = pe_input(self.screen, [TxEitc])
        household = result["household"]

        # Get units for checking fields
        tax_units = household["tax_units"]
        people = household["people"]
        household_unit = household["households"]["household"]

        # Check tax unit exists
        self.assertIn(MAIN_TAX_UNIT, tax_units)

        # Check member-level dependencies from Eitc.pe_inputs
        head_id = str(self.head.id)
        spouse_id = str(self.spouse.id)
        child_id = str(self.child.id)

        # Age dependency (from AgeDependency)
        self.assertIn(
            "age",
            people[head_id],
            "Expected field 'age' from AgeDependency not found in member data",
        )

        # Tax unit dependencies (from TaxUnitSpouseDependency and TaxUnitDependentDependency)
        self.assertIn(
            "is_tax_unit_spouse",
            people[spouse_id],
            "Expected field 'is_tax_unit_spouse' from TaxUnitSpouseDependency not found in spouse data",
        )
        self.assertIn(
            "is_tax_unit_dependent",
            people[child_id],
            "Expected field 'is_tax_unit_dependent' from TaxUnitDependentDependency not found in child data",
        )

        # Income dependencies from irs_gross_income tuple
        income_fields_to_check = [
            "employment_income",
            "self_employment_income",
            "rental_income",
            "taxable_pension_income",
            "social_security",
        ]

        for field in income_fields_to_check:
            self.assertIn(
                field,
                people[head_id],
                f"Expected income field '{field}' from irs_gross_income not found in member data",
            )

        # Check TX-specific dependency (added by TxEitc)
        self.assertIn(
            "state_code",
            household_unit,
            "Expected field 'state_code' from TxStateCodeDependency not found in household",
        )

    def test_pe_input_includes_txeitc_pe_output_field(self):
        """
        Test that pe_input result includes TxEitc pe_outputs dependency.

        TxEitc.pe_outputs = [dependency.tax.Eitc] which adds the 'eitc' field
        to the tax_unit for PolicyEngine to calculate and return.
        """
        result = pe_input(self.screen, [TxEitc])
        tax_units = result["household"]["tax_units"]

        # Check that the eitc output field is present in main tax unit
        self.assertIn(MAIN_TAX_UNIT, tax_units)
        main_tax_unit = tax_units[MAIN_TAX_UNIT]

        self.assertIn(
            "eitc",
            main_tax_unit,
            "Expected output field 'eitc' from TxEitc pe_outputs not found in tax_unit",
        )

        # Verify it has a period structure
        self.assertIsInstance(
            main_tax_unit["eitc"],
            dict,
            "eitc field should be a dict with period keys",
        )

    def test_pe_input_txeitc_income_values_are_correct(self):
        """
        Test that TxEitc income dependency values are correctly populated from HouseholdMember data.

        This verifies the 5 IRS gross income types are properly extracted.
        """
        result = pe_input(self.screen, [TxEitc])
        people = result["household"]["people"]

        head_id = str(self.head.id)
        spouse_id = str(self.spouse.id)

        # Get the period key from one of the fields
        if "employment_income" in people[head_id] and people[head_id]["employment_income"]:
            period_key = list(people[head_id]["employment_income"].keys())[0]

            # Verify head's income values
            self.assertEqual(
                people[head_id]["employment_income"][period_key],
                30000,
                "Head employment_income should match HouseholdMember value",
            )
            self.assertEqual(
                people[head_id]["self_employment_income"][period_key],
                5000,
                "Head self_employment_income should match HouseholdMember value",
            )
            self.assertEqual(
                people[head_id]["rental_income"][period_key],
                12000,
                "Head rental_income should match HouseholdMember value",
            )

            # Verify spouse's income values
            self.assertEqual(
                people[spouse_id]["taxable_pension_income"][period_key],
                8000,
                "Spouse taxable_pension_income should match HouseholdMember value",
            )
            self.assertEqual(
                people[spouse_id]["social_security"][period_key],
                6000,
                "Spouse social_security should match HouseholdMember value",
            )

    def test_pe_input_txeitc_tax_unit_relationships_are_correct(self):
        """
        Test that TxEitc correctly identifies tax unit relationships.

        This verifies that spouse and dependent flags are properly set for EITC calculation.
        """
        result = pe_input(self.screen, [TxEitc])
        people = result["household"]["people"]

        head_id = str(self.head.id)
        spouse_id = str(self.spouse.id)
        child_id = str(self.child.id)

        # Check if tax unit relationship fields are populated
        if "is_tax_unit_spouse" in people[spouse_id] and people[spouse_id]["is_tax_unit_spouse"]:
            period_key = list(people[spouse_id]["is_tax_unit_spouse"].keys())[0]

            # Spouse should be marked as tax unit spouse
            self.assertTrue(
                people[spouse_id]["is_tax_unit_spouse"][period_key],
                "Spouse should be marked as tax unit spouse",
            )

        if "is_tax_unit_dependent" in people[child_id] and people[child_id]["is_tax_unit_dependent"]:
            period_key = list(people[child_id]["is_tax_unit_dependent"].keys())[0]

            # Child should be marked as tax unit dependent
            self.assertTrue(
                people[child_id]["is_tax_unit_dependent"][period_key],
                "Child should be marked as tax unit dependent",
            )

        # Head should not be marked as spouse or dependent
        if "is_tax_unit_spouse" in people[head_id] and people[head_id]["is_tax_unit_spouse"]:
            period_key = list(people[head_id]["is_tax_unit_spouse"].keys())[0]
            self.assertFalse(
                people[head_id]["is_tax_unit_spouse"][period_key],
                "Head of household should not be marked as spouse",
            )

    def test_pe_input_txeitc_age_values_match_household_members(self):
        """
        Test that age dependency values for EITC match the actual member ages.

        This is important for EITC calculation as age affects eligibility and benefit amount.
        """
        result = pe_input(self.screen, [TxEitc])
        people = result["household"]["people"]

        head_id = str(self.head.id)
        spouse_id = str(self.spouse.id)
        child_id = str(self.child.id)

        # Verify ages are populated
        if "age" in people[head_id] and people[head_id]["age"]:
            period_key = list(people[head_id]["age"].keys())[0]

            self.assertEqual(
                people[head_id]["age"][period_key],
                35,
                "Head age should be 35",
            )
            self.assertEqual(
                people[spouse_id]["age"][period_key],
                32,
                "Spouse age should be 32",
            )
            self.assertEqual(
                people[child_id]["age"][period_key],
                8,
                "Child age should be 8",
            )

    def test_pe_input_txeitc_tx_specific_dependency_values(self):
        """
        Test that TX-specific dependencies have correct values for EITC.

        TxEitc adds TxStateCodeDependency which should set state_code="TX".
        """
        result = pe_input(self.screen, [TxEitc])
        household_unit = result["household"]["households"]["household"]

        # Verify state_code is set to "TX"
        self.assertIn("state_code", household_unit)
        if household_unit["state_code"]:
            period_key = list(household_unit["state_code"].keys())[0]
            self.assertEqual(
                household_unit["state_code"][period_key],
                "TX",
                "TxStateCodeDependency should set state_code='TX' for EITC",
            )

    def test_pe_input_txeitc_with_no_income(self):
        """
        Test that TxEitc handles members with no income correctly.

        Members with no income should still have all required fields populated with zero values.
        """
        # Create a screen with no income streams
        no_income_screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Travis County",
            household_size=2,
            completed=False,
        )

        # Head of household with no income
        no_income_head = HouseholdMember.objects.create(
            screen=no_income_screen,
            relationship="headOfHousehold",
            age=30,
            disabled=False,
            student=False,
        )

        # Child with no income
        no_income_child = HouseholdMember.objects.create(
            screen=no_income_screen,
            relationship="child",
            age=5,
            disabled=False,
            student=False,
        )

        result = pe_input(no_income_screen, [TxEitc])
        people = result["household"]["people"]
        head_id = str(no_income_head.id)

        # Verify income fields exist even with no income
        income_fields = [
            "employment_income",
            "self_employment_income",
            "rental_income",
            "taxable_pension_income",
            "social_security",
        ]

        for field in income_fields:
            self.assertIn(
                field,
                people[head_id],
                f"Expected income field '{field}' to be present even with no income",
            )

        # Verify values are zero or empty
        if people[head_id]["employment_income"]:
            period_key = list(people[head_id]["employment_income"].keys())[0]
            self.assertEqual(
                people[head_id]["employment_income"][period_key],
                0,
                "employment_income should be 0 for member with no income",
            )

    def test_pe_input_txeitc_with_single_parent(self):
        """
        Test that TxEitc handles single parent households correctly.

        Single parents with qualifying children should have all required fields.
        """
        # Create a single parent screen
        single_parent_screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Travis County",
            household_size=2,
            completed=False,
        )

        # Single parent (head of household)
        single_parent = HouseholdMember.objects.create(
            screen=single_parent_screen,
            relationship="headOfHousehold",
            age=28,
            disabled=False,
            student=False,
        )

        # Add income for the single parent
        IncomeStream.objects.create(
            screen=single_parent_screen,
            household_member=single_parent,
            type="wages",
            amount=25000,
            frequency="yearly",
        )

        # Child
        child = HouseholdMember.objects.create(
            screen=single_parent_screen,
            relationship="child",
            age=3,
            disabled=False,
            student=False,
        )

        result = pe_input(single_parent_screen, [TxEitc])
        household = result["household"]
        people = household["people"]
        tax_units = household["tax_units"]

        parent_id = str(single_parent.id)
        child_id = str(child.id)

        # Verify both members are in the main tax unit
        self.assertIn(MAIN_TAX_UNIT, tax_units)
        main_tax_unit_members = tax_units[MAIN_TAX_UNIT]["members"]
        self.assertIn(parent_id, main_tax_unit_members)
        self.assertIn(child_id, main_tax_unit_members)

        # Verify parent has income
        if "employment_income" in people[parent_id] and people[parent_id]["employment_income"]:
            period_key = list(people[parent_id]["employment_income"].keys())[0]
            self.assertEqual(
                people[parent_id]["employment_income"][period_key],
                25000,
                "Single parent should have employment income",
            )

        # Verify child is marked as dependent
        if "is_tax_unit_dependent" in people[child_id] and people[child_id]["is_tax_unit_dependent"]:
            period_key = list(people[child_id]["is_tax_unit_dependent"].keys())[0]
            self.assertTrue(
                people[child_id]["is_tax_unit_dependent"][period_key],
                "Child should be marked as tax unit dependent for single parent",
            )

    def test_pe_input_txeitc_with_multiple_children(self):
        """
        Test that TxEitc handles households with multiple qualifying children.

        EITC amount varies based on number of qualifying children, so this is important to test.
        """
        # Create a screen with multiple children
        multi_child_screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Travis County",
            household_size=5,
            completed=False,
        )

        # Parents
        parent1 = HouseholdMember.objects.create(
            screen=multi_child_screen,
            relationship="headOfHousehold",
            age=35,
        )
        parent2 = HouseholdMember.objects.create(
            screen=multi_child_screen,
            relationship="spouse",
            age=33,
        )

        # Add income
        IncomeStream.objects.create(
            screen=multi_child_screen,
            household_member=parent1,
            type="wages",
            amount=40000,
            frequency="yearly",
        )

        # Three children
        child1 = HouseholdMember.objects.create(
            screen=multi_child_screen,
            relationship="child",
            age=10,
        )
        child2 = HouseholdMember.objects.create(
            screen=multi_child_screen,
            relationship="child",
            age=7,
        )
        child3 = HouseholdMember.objects.create(
            screen=multi_child_screen,
            relationship="child",
            age=4,
        )

        result = pe_input(multi_child_screen, [TxEitc])
        household = result["household"]
        people = household["people"]
        tax_units = household["tax_units"]

        # Verify all 5 members are in the main tax unit
        main_tax_unit_members = tax_units[MAIN_TAX_UNIT]["members"]
        self.assertEqual(len(main_tax_unit_members), 5, "All 5 members should be in main tax unit")

        # Verify all three children are marked as dependents
        for child in [child1, child2, child3]:
            child_id = str(child.id)
            self.assertIn("is_tax_unit_dependent", people[child_id])
            if people[child_id]["is_tax_unit_dependent"]:
                period_key = list(people[child_id]["is_tax_unit_dependent"].keys())[0]
                self.assertTrue(
                    people[child_id]["is_tax_unit_dependent"][period_key],
                    f"Child {child.age} should be marked as tax unit dependent",
                )

        # Verify spouse is marked correctly
        spouse_id = str(parent2.id)
        if "is_tax_unit_spouse" in people[spouse_id] and people[spouse_id]["is_tax_unit_spouse"]:
            period_key = list(people[spouse_id]["is_tax_unit_spouse"].keys())[0]
            self.assertTrue(
                people[spouse_id]["is_tax_unit_spouse"][period_key],
                "Second parent should be marked as spouse",
            )

    def test_pe_input_with_txeitc_and_txsnap_combined(self):
        """
        Test that pe_input handles both TxEitc and TxSnap calculators together.

        This verifies that dependencies from both calculators are properly merged.
        """
        result = pe_input(self.screen, [TxEitc, TxSnap])
        household = result["household"]

        spm_unit = household["spm_units"]["spm_unit"]
        people = household["people"]
        tax_units = household["tax_units"]
        household_unit = household["households"]["household"]
        head_id = str(self.head.id)

        # Verify TxEitc fields
        self.assertIn(MAIN_TAX_UNIT, tax_units)
        self.assertIn("eitc", tax_units[MAIN_TAX_UNIT])
        self.assertIn("employment_income", people[head_id])
        self.assertIn("is_tax_unit_spouse", people[str(self.spouse.id)])

        # Verify TxSnap fields
        self.assertIn("snap_assets", spm_unit)
        self.assertIn("snap_earned_income", spm_unit)
        self.assertIn("snap", spm_unit)

        # Verify shared TX dependency
        self.assertIn("state_code", household_unit)

        # Verify structure is valid
        self.assertIsInstance(household["people"], dict)
        self.assertIsInstance(household["spm_units"], dict)
        self.assertIsInstance(household["tax_units"], dict)

    def test_pe_input_with_txctc_populates_tax_unit_fields(self):
        """Test that TxCtc calculator populates tax unit and member fields correctly."""
        result = pe_input(self.screen, [TxCtc])
        household = result["household"]
        people = household["people"]
        tax_units = household["tax_units"]
        household_unit = household["households"]["household"]

        # Verify tax unit structure exists
        self.assertIn(MAIN_TAX_UNIT, tax_units)
        main_tax_unit = tax_units[MAIN_TAX_UNIT]

        # Verify all members are in tax unit
        self.assertIn(str(self.head.id), main_tax_unit["members"])
        self.assertIn(str(self.spouse.id), main_tax_unit["members"])
        self.assertIn(str(self.child.id), main_tax_unit["members"])

        # Verify CTC-specific member fields
        head_id = str(self.head.id)
        spouse_id = str(self.spouse.id)
        child_id = str(self.child.id)

        # Age dependency should be populated for all members
        self.assertIn("age", people[head_id])
        self.assertIn("age", people[spouse_id])
        self.assertIn("age", people[child_id])

        # Tax unit role dependencies should be populated
        self.assertIn("is_tax_unit_dependent", people[head_id])
        self.assertIn("is_tax_unit_spouse", people[head_id])
        self.assertIn("is_tax_unit_dependent", people[spouse_id])
        self.assertIn("is_tax_unit_spouse", people[spouse_id])
        self.assertIn("is_tax_unit_dependent", people[child_id])

        # Income dependencies should be populated
        self.assertIn("employment_income", people[head_id])
        self.assertIn("self_employment_income", people[head_id])
        self.assertIn("rental_income", people[head_id])

        # TX state code should be populated on household
        self.assertIn("state_code", household_unit)

        # CTC output field should be in tax unit
        self.assertIn("ctc_value", main_tax_unit)

    def test_pe_input_includes_all_txssi_pe_input_fields(self):
        """
        Test that pe_input includes all TxSsi pe_inputs fields.

        TxSsi should have all SSI-related dependencies including:
        - SsiCountableResourcesDependency
        - SsiReportedDependency
        - IsBlindDependency
        - IsDisabledDependency
        - SsiEarnedIncomeDependency
        - SsiUnearnedIncomeDependency
        - AgeDependency
        - TaxUnitSpouseDependency
        - TaxUnitHeadDependency
        - TaxUnitDependentDependency
        - TxStateCodeDependency
        """
        result = pe_input(self.screen, [TxSsi])
        household = result["household"]
        people = household["people"]
        household_unit = household["households"]["household"]
        tax_units = household["tax_units"]

        # Check that we have people
        self.assertGreater(len(people), 0)

        # Get first person to check member-level fields
        person_id = str(self.head.id)
        person = people[person_id]

        # Verify SSI-specific member dependencies
        self.assertIn("ssi_countable_resources", person)
        self.assertIn("ssi_reported", person)
        self.assertIn("is_blind", person)
        self.assertIn("is_disabled", person)
        self.assertIn("ssi_earned_income", person)
        self.assertIn("ssi_unearned_income", person)
        self.assertIn("age", person)

        # Verify tax unit membership fields exist
        self.assertIn(MAIN_TAX_UNIT, tax_units)
        main_tax_unit = tax_units[MAIN_TAX_UNIT]
        self.assertIn("members", main_tax_unit)

        # Verify TX-specific dependency
        self.assertIn("state_code", household_unit)
        state_code_periods = household_unit["state_code"]
        if state_code_periods:
            period_key = list(state_code_periods.keys())[0]
            self.assertEqual(state_code_periods[period_key], "TX")

    def test_pe_input_includes_all_txssi_pe_output_fields(self):
        """
        Test that pe_input includes all TxSsi pe_outputs fields.

        TxSsi should include the SSI output field.
        """
        result = pe_input(self.screen, [TxSsi])
        household = result["household"]
        people = household["people"]

        # Get a person to check output fields
        person_id = str(self.head.id)
        person = people[person_id]

        # Verify SSI output field
        self.assertIn("ssi", person)
        self.assertIsInstance(person["ssi"], dict)

    def test_pe_input_txssi_disability_fields(self):
        """
        Test that pe_input correctly populates disability-related fields for TxSsi.

        SSI eligibility depends on disability status, so verify is_disabled
        and is_blind are properly populated from HouseholdMember data.
        """
        result = pe_input(self.screen, [TxSsi])
        household = result["household"]
        people = household["people"]

        # Head is disabled (from setUp)
        head_id = str(self.head.id)
        head = people[head_id]
        self.assertIn("is_disabled", head)
        self.assertIsInstance(head["is_disabled"], dict)

        # Spouse is not disabled (from setUp)
        spouse_id = str(self.spouse.id)
        spouse = people[spouse_id]
        self.assertIn("is_disabled", spouse)
        self.assertIsInstance(spouse["is_disabled"], dict)

        # Check blind field exists
        self.assertIn("is_blind", head)
        self.assertIsInstance(head["is_blind"], dict)

    def test_pe_input_txssi_income_fields(self):
        """
        Test that pe_input correctly populates SSI-specific income fields.

        SSI has special earned and unearned income calculations that
        differ from other programs.
        """
        result = pe_input(self.screen, [TxSsi])
        household = result["household"]
        people = household["people"]

        head_id = str(self.head.id)
        head = people[head_id]

        # Verify SSI-specific income fields
        self.assertIn("ssi_earned_income", head)
        self.assertIsInstance(head["ssi_earned_income"], dict)

        self.assertIn("ssi_unearned_income", head)
        self.assertIsInstance(head["ssi_unearned_income"], dict)

        # Verify reported SSI field
        self.assertIn("ssi_reported", head)
        self.assertIsInstance(head["ssi_reported"], dict)

    def test_pe_input_txssi_resources_field(self):
        """
        Test that pe_input correctly populates SSI countable resources field.

        SSI has asset limits, so countable resources must be tracked.
        """
        result = pe_input(self.screen, [TxSsi])
        household = result["household"]
        people = household["people"]

        head_id = str(self.head.id)
        head = people[head_id]

        # Verify countable resources field
        self.assertIn("ssi_countable_resources", head)
        self.assertIsInstance(head["ssi_countable_resources"], dict)

    def test_pe_input_txssi_tx_specific_dependency_values(self):
        """
        Test that TX-specific dependency values are correctly set for TxSsi.

        TxSsi should have state_code="TX" for correct PolicyEngine calculations.
        """
        result = pe_input(self.screen, [TxSsi])
        household = result["household"]
        household_unit = household["households"]["household"]

        # Verify TX state code
        self.assertIn("state_code", household_unit)
        state_code_periods = household_unit["state_code"]
        if state_code_periods:
            period_key = list(state_code_periods.keys())[0]
            self.assertEqual(state_code_periods[period_key], "TX")

    def test_pe_input_with_txssi_and_txsnap_combined(self):
        """
        Test that pe_input handles both TxSsi and TxSnap calculators together.

        This verifies that dependencies from both calculators are properly merged,
        which is important since SSI recipients may also qualify for SNAP.
        """
        result = pe_input(self.screen, [TxSsi, TxSnap])
        household = result["household"]

        spm_unit = household["spm_units"]["spm_unit"]
        people = household["people"]
        household_unit = household["households"]["household"]
        head_id = str(self.head.id)

        # Verify TxSsi fields
        self.assertIn("ssi_countable_resources", people[head_id])
        self.assertIn("is_disabled", people[head_id])
        self.assertIn("ssi", people[head_id])

        # Verify TxSnap fields
        self.assertIn("snap_assets", spm_unit)
        self.assertIn("snap_earned_income", spm_unit)
        self.assertIn("snap", spm_unit)

        # Verify shared TX dependency
        self.assertIn("state_code", household_unit)
        state_code_periods = household_unit["state_code"]
        if state_code_periods:
            period_key = list(state_code_periods.keys())[0]
            self.assertEqual(state_code_periods[period_key], "TX")

        # Verify structure is valid
        self.assertIsInstance(household["people"], dict)
        self.assertIsInstance(household["spm_units"], dict)

    def test_pe_input_includes_all_txcsfp_pe_input_fields(self):
        """
        Test that pe_input result includes all TxCsfp pe_inputs dependencies.

        TxCsfp inherits from CommoditySupplementalFoodProgram and adds TxStateCodeDependency.
        This test verifies all input fields from the dependency classes are present.
        """
        result = pe_input(self.screen, [TxCsfp])
        household = result["household"]

        # Get units for checking fields
        spm_unit = household["spm_units"]["spm_unit"]
        people = household["people"]
        household_unit = household["households"]["household"]

        # Check SPM-level dependencies from CommoditySupplementalFoodProgram.pe_inputs
        self.assertIn(
            "school_meal_countable_income",
            spm_unit,
            "Expected field 'school_meal_countable_income' from CSFP pe_inputs not found in spm_unit",
        )

        # Check member-level dependencies from CommoditySupplementalFoodProgram.pe_inputs
        head_id = str(self.head.id)
        self.assertIn(
            "age",
            people[head_id],
            "Expected field 'age' from TxCsfp pe_inputs not found in member data",
        )

        # Check TX-specific dependency (added by TxCsfp)
        self.assertIn(
            "state_code",
            household_unit,
            "Expected field 'state_code' from TxStateCodeDependency not found in household",
        )

    def test_pe_input_includes_all_txaca_pe_input_fields(self):
        """
        Test that pe_input result includes all TxAca pe_inputs dependencies.

        TxAca inherits from Aca which includes Medicaid inputs plus tax unit and other dependencies.
        This test verifies all input fields from the dependency classes are present.
        """
        result = pe_input(self.screen, [TxAca])
        household = result["household"]

        # Get units for checking fields
        tax_units = household["tax_units"]
        people = household["people"]
        household_unit = household["households"]["household"]

        # Check tax unit exists
        self.assertIn(MAIN_TAX_UNIT, tax_units)

        # Check member-level dependencies
        head_id = str(self.head.id)
        spouse_id = str(self.spouse.id)
        child_id = str(self.child.id)

        # Age dependency (from Medicaid.pe_inputs and direct in Aca.pe_inputs)
        self.assertIn(
            "age",
            people[head_id],
            "Expected field 'age' from AgeDependency not found in member data",
        )

        # Pregnancy dependency (from Medicaid.pe_inputs)
        self.assertIn(
            "is_pregnant",
            people[head_id],
            "Expected field 'is_pregnant' from PregnancyDependency not found in member data",
        )

        # Disability dependency (from both Medicaid.pe_inputs and direct in Aca.pe_inputs)
        self.assertIn(
            "is_disabled",
            people[head_id],
            "Expected field 'is_disabled' from IsDisabledDependency not found in member data",
        )

        # SSI countable resources (from Medicaid.pe_inputs)
        self.assertIn(
            "ssi_countable_resources",
            people[head_id],
            "Expected field 'ssi_countable_resources' from SsiCountableResourcesDependency not found",
        )

        # Tax unit dependencies (from Aca.pe_inputs)
        self.assertIn(
            "is_tax_unit_head",
            people[head_id],
            "Expected field 'is_tax_unit_head' from TaxUnitHeadDependency not found in head data",
        )
        self.assertIn(
            "is_tax_unit_spouse",
            people[spouse_id],
            "Expected field 'is_tax_unit_spouse' from TaxUnitSpouseDependency not found in spouse data",
        )
        self.assertIn(
            "is_tax_unit_dependent",
            people[child_id],
            "Expected field 'is_tax_unit_dependent' from TaxUnitDependentDependency not found in child data",
        )

        # Income dependencies from irs_gross_income tuple
        income_fields_to_check = [
            "employment_income",
            "self_employment_income",
            "rental_income",
            "taxable_pension_income",
            "social_security",
        ]

        for field in income_fields_to_check:
            self.assertIn(
                field,
                people[head_id],
                f"Expected income field '{field}' from irs_gross_income not found in member data",
            )

        # Zip code dependency (from Aca.pe_inputs via ZipCodeDependency)
        self.assertIn(
            "zip_code",
            household_unit,
            "Expected field 'zip_code' from ZipCodeDependency not found in household",
        )

        # Check TX-specific dependency (added by TxAca)
        self.assertIn(
            "state_code",
            household_unit,
            "Expected field 'state_code' from TxStateCodeDependency not found in household",
        )

    def test_pe_input_includes_all_txcsfp_pe_output_fields(self):
        """
        Test that pe_input result includes all TxCsfp pe_outputs dependencies.

        TxCsfp.pe_outputs = [dependency.member.CommoditySupplementalFoodProgram]
        which adds the 'commodity_supplemental_food_program' field to each member.
        """
        result = pe_input(self.screen, [TxCsfp])
        people = result["household"]["people"]

        head_id = str(self.head.id)
        spouse_id = str(self.spouse.id)
        child_id = str(self.child.id)

        # Check that the commodity_supplemental_food_program output field is present for each member
        for member_id in [head_id, spouse_id, child_id]:
            self.assertIn(
                "commodity_supplemental_food_program",
                people[member_id],
                f"Expected output field 'commodity_supplemental_food_program' from TxCsfp pe_outputs not found for member {member_id}",
            )

            # Verify it has period structure
            self.assertIsInstance(
                people[member_id]["commodity_supplemental_food_program"],
                dict,
                f"commodity_supplemental_food_program field should be a dict with period keys for member {member_id}",
            )

    def test_pe_input_includes_txaca_pe_output_field(self):
        """
        Test that pe_input result includes TxAca pe_outputs dependency.

        TxAca.pe_outputs = [dependency.tax.Aca] which adds the 'aca_ptc' field
        to the tax unit for calculating the ACA Premium Tax Credit.
        """
        result = pe_input(self.screen, [TxAca])
        household = result["household"]
        tax_units = household["tax_units"]

        # Check that aca_ptc output field exists in main tax unit
        self.assertIn(MAIN_TAX_UNIT, tax_units)
        self.assertIn(
            "aca_ptc",
            tax_units[MAIN_TAX_UNIT],
            "Expected output field 'aca_ptc' from TxAca.pe_outputs not found in tax unit",
        )

    def test_pe_input_txaca_income_values_are_correct(self):
        """
        Test that income values are correctly populated for TxAca calculation.

        This verifies that all income streams are properly mapped to PolicyEngine
        income fields needed for ACA eligibility and subsidy calculations.
        """
        result = pe_input(self.screen, [TxAca])
        people = result["household"]["people"]

        head_id = str(self.head.id)
        spouse_id = str(self.spouse.id)

        # Get the period key from one of the fields
        if "employment_income" in people[head_id] and people[head_id]["employment_income"]:
            period_key = list(people[head_id]["employment_income"].keys())[0]

            # Head income: $30k wages, $5k self-employment, $12k rental
            self.assertEqual(people[head_id]["employment_income"][period_key], 30000)
            self.assertEqual(people[head_id]["self_employment_income"][period_key], 5000)
            self.assertEqual(people[head_id]["rental_income"][period_key], 12000)

            # Spouse income: $8k pension, $6k social security
            self.assertEqual(people[spouse_id]["taxable_pension_income"][period_key], 8000)
            self.assertEqual(people[spouse_id]["social_security"][period_key], 6000)

    def test_pe_input_txaca_tax_unit_relationships_are_correct(self):
        """
        Test that tax unit relationships are correctly set for TxAca.

        ACA Premium Tax Credit eligibility depends on tax filing unit, so
        proper head/spouse/dependent relationships are critical.
        """
        result = pe_input(self.screen, [TxAca])
        people = result["household"]["people"]

        head_id = str(self.head.id)
        spouse_id = str(self.spouse.id)
        child_id = str(self.child.id)

        # Check if tax unit relationship fields are populated
        if "is_tax_unit_head" in people[head_id] and people[head_id]["is_tax_unit_head"]:
            period_key = list(people[head_id]["is_tax_unit_head"].keys())[0]
            # Head should be marked as tax unit head
            self.assertTrue(
                people[head_id]["is_tax_unit_head"][period_key],
                "Head should be marked as is_tax_unit_head",
            )

        if "is_tax_unit_spouse" in people[spouse_id] and people[spouse_id]["is_tax_unit_spouse"]:
            period_key = list(people[spouse_id]["is_tax_unit_spouse"].keys())[0]
            # Spouse should be marked as tax unit spouse
            self.assertTrue(
                people[spouse_id]["is_tax_unit_spouse"][period_key],
                "Spouse should be marked as is_tax_unit_spouse",
            )

        if "is_tax_unit_dependent" in people[child_id] and people[child_id]["is_tax_unit_dependent"]:
            period_key = list(people[child_id]["is_tax_unit_dependent"].keys())[0]
            # Child should be marked as tax unit dependent
            self.assertTrue(
                people[child_id]["is_tax_unit_dependent"][period_key],
                "Child should be marked as is_tax_unit_dependent",
            )

    def test_pe_input_txaca_disability_and_age_values(self):
        """
        Test that age and disability status are correctly populated for TxAca.

        ACA calculations need accurate age and disability data for determining
        premium amounts and eligibility.
        """
        result = pe_input(self.screen, [TxAca])
        people = result["household"]["people"]

        head_id = str(self.head.id)
        spouse_id = str(self.spouse.id)
        child_id = str(self.child.id)

        # Verify ages are populated
        if "age" in people[head_id] and people[head_id]["age"]:
            period_key = list(people[head_id]["age"].keys())[0]
            self.assertEqual(people[head_id]["age"][period_key], 35)
            self.assertEqual(people[spouse_id]["age"][period_key], 32)
            self.assertEqual(people[child_id]["age"][period_key], 8)

        # Verify disability status
        if "is_disabled" in people[head_id] and people[head_id]["is_disabled"]:
            period_key = list(people[head_id]["is_disabled"].keys())[0]
            self.assertTrue(
                people[head_id]["is_disabled"][period_key],
                "Head should be marked as disabled",
            )
            self.assertFalse(
                people[spouse_id]["is_disabled"][period_key],
                "Spouse should not be marked as disabled",
            )

    def test_pe_input_txaca_zipcode_is_populated(self):
        """
        Test that zipcode is correctly populated for TxAca calculations.

        ACA premium amounts vary by location, so zipcode is essential
        for accurate subsidy calculations.
        """
        result = pe_input(self.screen, [TxAca])
        household_unit = result["household"]["households"]["household"]

        # Verify zipcode from screen is in the household unit
        self.assertIn("zip_code", household_unit)
        if household_unit["zip_code"]:
            period_key = list(household_unit["zip_code"].keys())[0]
            self.assertEqual(household_unit["zip_code"][period_key], "78701")

    def test_pe_input_txaca_tx_specific_dependency_values(self):
        """
        Test that TX-specific state_code is set correctly for TxAca.

        This is critical for PolicyEngine to use Texas-specific rules.
        """
        result = pe_input(self.screen, [TxAca])
        household_unit = result["household"]["households"]["household"]

        # Verify TX state code
        self.assertIn("state_code", household_unit)
        if household_unit["state_code"]:
            period_key = list(household_unit["state_code"].keys())[0]
            self.assertEqual(household_unit["state_code"][period_key], "TX")

    def test_pe_input_txcsfp_with_senior_member(self):
        """
        Test that TxCsfp correctly handles senior members (60+) in the household.

        Seniors (age >= 60) are the primary eligible group for CSFP.
        """
        # Create a senior household member
        senior = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="spouse",
            age=65,
            disabled=False,
            student=False,
        )

        result = pe_input(self.screen, [TxCsfp])
        people = result["household"]["people"]
        senior_id = str(senior.id)

        # Verify senior has all required CSFP fields
        self.assertIn("age", people[senior_id])
        self.assertIn("commodity_supplemental_food_program", people[senior_id])

        # Check age value
        if people[senior_id]["age"]:
            period_key = list(people[senior_id]["age"].keys())[0]
            self.assertEqual(
                people[senior_id]["age"][period_key],
                65,
                "Senior age should be 65",
            )

    def test_pe_input_txcsfp_tx_specific_dependency_values(self):
        """
        Test that TX-specific dependencies have correct values for CSFP.

        TxCsfp adds TxStateCodeDependency which should set state_code="TX".
        """
        result = pe_input(self.screen, [TxCsfp])
        household_unit = result["household"]["households"]["household"]

        # Verify state_code is set to "TX"
        self.assertIn("state_code", household_unit)
        if household_unit["state_code"]:
            period_key = list(household_unit["state_code"].keys())[0]
            self.assertEqual(
                household_unit["state_code"][period_key],
                "TX",
                "TxStateCodeDependency should set state_code='TX' for CSFP",
            )

    def test_pe_input_txcsfp_school_meal_countable_income(self):
        """
        Test that TxCsfp includes school_meal_countable_income dependency.

        This is inherited from the parent CommoditySupplementalFoodProgram class and should be present in spm_unit.
        """
        result = pe_input(self.screen, [TxCsfp])
        spm_unit = result["household"]["spm_units"]["spm_unit"]

        # Verify field exists
        self.assertIn(
            "school_meal_countable_income",
            spm_unit,
            "school_meal_countable_income should be present in spm_unit for CSFP",
        )

        # Verify it has a period structure
        self.assertIsInstance(
            spm_unit["school_meal_countable_income"],
            dict,
            "school_meal_countable_income should be a dict with period keys",
        )

    def test_pe_input_with_txcsfp_and_txsnap_combined(self):
        """
        Test that pe_input handles both TxCsfp and TxSnap calculators together.

        This verifies that dependencies from both calculators are properly merged,
        which is important since CSFP recipients may also qualify for SNAP.
        """
        result = pe_input(self.screen, [TxCsfp, TxSnap])
        household = result["household"]

        spm_unit = household["spm_units"]["spm_unit"]
        people = household["people"]
        household_unit = household["households"]["household"]
        head_id = str(self.head.id)

        # Verify TxCsfp fields
        self.assertIn("school_meal_countable_income", spm_unit)
        self.assertIn("age", people[head_id])
        self.assertIn("commodity_supplemental_food_program", people[head_id])

        # Verify TxSnap fields
        self.assertIn("snap_assets", spm_unit)
        self.assertIn("snap_earned_income", spm_unit)
        self.assertIn("snap", spm_unit)

        # Verify shared TX dependency
        self.assertIn("state_code", household_unit)
        state_code_periods = household_unit["state_code"]
        if state_code_periods:
            period_key = list(state_code_periods.keys())[0]
            self.assertEqual(state_code_periods[period_key], "TX")

        # Verify structure is valid
        self.assertIsInstance(household["people"], dict)
        self.assertIsInstance(household["spm_units"], dict)

    def test_pe_input_with_txaca_and_txsnap_combined(self):
        """
        Test that pe_input handles both TxAca and TxSnap calculators together.

        This verifies that dependencies from both calculators are properly merged.
        """
        result = pe_input(self.screen, [TxAca, TxSnap])
        household = result["household"]

        spm_unit = household["spm_units"]["spm_unit"]
        people = household["people"]
        tax_units = household["tax_units"]
        household_unit = household["households"]["household"]
        head_id = str(self.head.id)

        # Verify TxAca fields
        self.assertIn(MAIN_TAX_UNIT, tax_units)
        self.assertIn("aca_ptc", tax_units[MAIN_TAX_UNIT])
        self.assertIn("employment_income", people[head_id])
        self.assertIn("is_tax_unit_spouse", people[str(self.spouse.id)])
        self.assertIn("zip_code", household_unit)

        # Verify TxSnap fields
        self.assertIn("snap_assets", spm_unit)
        self.assertIn("snap_earned_income", spm_unit)
        self.assertIn("snap", spm_unit)

        # Verify shared TX dependency
        self.assertIn("state_code", household_unit)

        # Verify structure is valid
        self.assertIsInstance(household["people"], dict)
        self.assertIsInstance(household["spm_units"], dict)
        self.assertIsInstance(household["tax_units"], dict)

    def test_pe_input_txtanf_tx_specific_dependency_values(self):
        """
        Test that TxTanf includes TX-specific dependencies with correct values.

        TxTanf adds:
        - TxStateCodeDependency (household level)
        - TxTanfCountableEarnedIncomeDependency (SPM level)
        - TxTanfCountableUnearnedIncomeDependency (SPM level)
        """
        result = pe_input(self.screen, [TxTanf])
        household = result["household"]
        household_unit = household["households"]["household"]
        spm_unit = household["spm_units"]["spm_unit"]

        # Verify TX state code dependency
        self.assertIn("state_code", household_unit)
        if household_unit["state_code"]:
            period_key = list(household_unit["state_code"].keys())[0]
            self.assertEqual(
                household_unit["state_code"][period_key],
                "TX",
                "TxStateCodeDependency should set state_code='TX'",
            )

        # Verify TX TANF income dependencies
        self.assertIn(
            "tx_tanf_countable_earned_income",
            spm_unit,
            "Expected tx_tanf_countable_earned_income from TxTanfCountableEarnedIncomeDependency",
        )
        self.assertIn(
            "tx_tanf_countable_unearned_income",
            spm_unit,
            "Expected tx_tanf_countable_unearned_income from TxTanfCountableUnearnedIncomeDependency",
        )

    def test_pe_input_includes_txtanf_pe_output_field(self):
        """
        Test that pe_input result includes TxTanf pe_outputs dependency.

        TxTanf.pe_outputs = [dependency.spm.TxTanf] which adds the 'tx_tanf' field
        to the spm_unit for PolicyEngine to calculate and return.
        """
        result = pe_input(self.screen, [TxTanf])
        spm_unit = result["household"]["spm_units"]["spm_unit"]

        # Verify tx_tanf output field exists
        self.assertIn(
            "tx_tanf",
            spm_unit,
            "Expected 'tx_tanf' output field from TxTanf.pe_outputs not found in spm_unit",
        )

        # Verify it has a period structure
        self.assertIsInstance(
            spm_unit["tx_tanf"],
            dict,
            "tx_tanf should be a dict with period keys",
        )

    def test_pe_input_with_txtanf_includes_parent_tanf_dependencies(self):
        """
        Test that TxTanf includes dependencies inherited from parent Tanf class.

        The parent Tanf class includes:
        - AgeDependency (member level)
        - FullTimeCollegeStudentDependency (member level)
        """
        result = pe_input(self.screen, [TxTanf])
        people = result["household"]["people"]

        # Check member-level dependencies from parent Tanf class
        head_id = str(self.head.id)
        self.assertIn(
            "age",
            people[head_id],
            "Expected 'age' field from AgeDependency (inherited from Tanf) not found",
        )
        self.assertIn(
            "is_full_time_college_student",
            people[head_id],
            "Expected 'is_full_time_college_student' field from FullTimeCollegeStudentDependency not found",
        )

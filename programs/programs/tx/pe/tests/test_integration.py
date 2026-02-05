"""
Unit tests for pe_input() function with TX-specific calculators.

These tests verify that TX PE calculators correctly populate their
dependencies in the pe_input() result. Core pe_input() structure tests
live in policyengine/tests/test_pe_input.py.

Tests are organized by calculator type (SPM, member, tax).
"""

from django.test import TestCase
from screener.models import Screen, HouseholdMember, WhiteLabel, Expense, IncomeStream
from programs.programs.policyengine.policy_engine import pe_input
from programs.programs.tx.pe.spm import TxSnap, TxLifeline, TxTanf
from programs.programs.tx.pe.member import TxWic, TxSsi, TxCsfp, TxChip
from programs.programs.tx.pe.tax import TxEitc, TxCtc, TxAca
from programs.programs.policyengine.calculators.constants import (
    MAIN_TAX_UNIT,
    SECONDARY_TAX_UNIT,
)


class TxPeInputTestBase(TestCase):
    """Base class with shared test fixtures for TX pe_input tests."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data that doesn't change between tests."""
        cls.white_label = WhiteLabel.objects.create(name="Texas", code="tx", state_code="TX")

    def setUp(self):
        """Set up test screen with household members."""
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

        # Add income streams
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

        # Add expenses
        Expense.objects.create(screen=self.screen, type="childSupport", amount=500, frequency="monthly")
        Expense.objects.create(screen=self.screen, type="medical", amount=200, frequency="monthly")


# =============================================================================
# SPM Calculator Tests
# =============================================================================


class TestTxSnapPeInput(TxPeInputTestBase):
    """Tests for TxSnap calculator pe_input dependencies."""

    def test_includes_all_pe_input_fields(self):
        """Test that pe_input includes all TxSnap pe_inputs dependencies."""
        result = pe_input(self.screen, [TxSnap])
        household = result["household"]
        spm_unit = household["spm_units"]["spm_unit"]
        people = household["people"]
        household_unit = household["households"]["household"]

        # SPM-level dependencies
        spm_fields = [
            "snap_unearned_income",
            "snap_earned_income",
            "snap_assets",
            "snap_emergency_allotment",
            "housing_cost",
            "has_phone_expense",
            "has_heating_cooling_expense",
        ]
        for field in spm_fields:
            self.assertIn(field, spm_unit)

        # Member-level dependencies
        head_id = str(self.head.id)
        member_fields = ["child_support_expense", "age", "is_disabled"]
        for field in member_fields:
            self.assertIn(field, people[head_id])

        # TX-specific dependency
        self.assertIn("state_code", household_unit)

    def test_includes_pe_output_fields(self):
        """Test that pe_input includes TxSnap pe_outputs."""
        result = pe_input(self.screen, [TxSnap])
        spm_unit = result["household"]["spm_units"]["spm_unit"]
        self.assertIn("snap", spm_unit)
        self.assertIsInstance(spm_unit["snap"], dict)

    def test_state_code_is_tx(self):
        """Test that TxStateCodeDependency sets state_code to TX."""
        result = pe_input(self.screen, [TxSnap])
        household_unit = result["household"]["households"]["household"]

        if household_unit["state_code"]:
            period_key = list(household_unit["state_code"].keys())[0]
            self.assertEqual(household_unit["state_code"][period_key], "TX")

    def test_snap_assets_matches_screen(self):
        """Test that snap_assets matches Screen.household_assets."""
        result = pe_input(self.screen, [TxSnap])
        spm_unit = result["household"]["spm_units"]["spm_unit"]

        if spm_unit["snap_assets"]:
            period_key = list(spm_unit["snap_assets"].keys())[0]
            self.assertEqual(spm_unit["snap_assets"][period_key], 5000)


class TestTxLifelinePeInput(TxPeInputTestBase):
    """Tests for TxLifeline calculator pe_input dependencies."""

    def test_includes_all_pe_input_fields(self):
        """Test that pe_input includes all Lifeline pe_inputs dependencies."""
        result = pe_input(self.screen, [TxLifeline])
        household = result["household"]
        spm_unit = household["spm_units"]["spm_unit"]
        people = household["people"]

        # SPM-level dependency
        self.assertIn("broadband_cost", spm_unit)

        # Member-level income dependencies
        head_id = str(self.head.id)
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
        """Test that pe_input includes Lifeline pe_outputs."""
        result = pe_input(self.screen, [TxLifeline])
        spm_unit = result["household"]["spm_units"]["spm_unit"]
        self.assertIn("lifeline", spm_unit)

    def test_income_values_are_correct(self):
        """Test that income values match HouseholdMember data."""
        result = pe_input(self.screen, [TxLifeline])
        people = result["household"]["people"]
        head_id = str(self.head.id)
        spouse_id = str(self.spouse.id)

        if people[head_id]["employment_income"]:
            period_key = list(people[head_id]["employment_income"].keys())[0]
            self.assertEqual(people[head_id]["employment_income"][period_key], 30000)
            self.assertEqual(people[head_id]["self_employment_income"][period_key], 5000)
            self.assertEqual(people[spouse_id]["taxable_pension_income"][period_key], 8000)


class TestTxTanfPeInput(TxPeInputTestBase):
    """Tests for TxTanf calculator pe_input dependencies."""

    def test_includes_tx_specific_dependencies(self):
        """Test that TxTanf includes TX-specific dependencies."""
        result = pe_input(self.screen, [TxTanf])
        household = result["household"]
        spm_unit = household["spm_units"]["spm_unit"]
        household_unit = household["households"]["household"]

        # TX TANF income dependencies
        self.assertIn("tx_tanf_countable_earned_income", spm_unit)
        self.assertIn("tx_tanf_countable_unearned_income", spm_unit)

        # TX state code
        self.assertIn("state_code", household_unit)

    def test_includes_pe_output_field(self):
        """Test that pe_input includes TxTanf pe_outputs."""
        result = pe_input(self.screen, [TxTanf])
        spm_unit = result["household"]["spm_units"]["spm_unit"]
        self.assertIn("tx_tanf", spm_unit)

    def test_includes_parent_tanf_dependencies(self):
        """Test that TxTanf includes dependencies from parent Tanf class."""
        result = pe_input(self.screen, [TxTanf])
        people = result["household"]["people"]
        head_id = str(self.head.id)

        self.assertIn("age", people[head_id])
        self.assertIn("is_full_time_college_student", people[head_id])


# =============================================================================
# Member Calculator Tests
# =============================================================================


class TestTxWicPeInput(TxPeInputTestBase):
    """Tests for TxWic calculator pe_input dependencies."""

    def test_includes_all_pe_input_fields(self):
        """Test that pe_input includes all TxWic pe_inputs dependencies."""
        result = pe_input(self.screen, [TxWic])
        household = result["household"]
        spm_unit = household["spm_units"]["spm_unit"]
        people = household["people"]

        # SPM-level dependency
        self.assertIn("school_meal_countable_income", spm_unit)

        # Member-level dependencies
        head_id = str(self.head.id)
        self.assertIn("is_pregnant", people[head_id])
        self.assertIn("current_pregnancies", people[head_id])
        self.assertIn("age", people[head_id])

    def test_includes_pe_output_fields(self):
        """Test that pe_input includes TxWic pe_outputs."""
        result = pe_input(self.screen, [TxWic])
        people = result["household"]["people"]

        for member_id in [str(self.head.id), str(self.spouse.id), str(self.child.id)]:
            self.assertIn("wic", people[member_id])
            self.assertIn("wic_category", people[member_id])

    def test_pregnancy_fields_for_pregnant_member(self):
        """Test that pregnancy fields are populated for pregnant members."""
        pregnant_member = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="parent",
            age=28,
            pregnant=True,
        )

        result = pe_input(self.screen, [TxWic])
        people = result["household"]["people"]
        pregnant_id = str(pregnant_member.id)

        if people[pregnant_id]["is_pregnant"]:
            period_key = list(people[pregnant_id]["is_pregnant"].keys())[0]
            self.assertTrue(people[pregnant_id]["is_pregnant"][period_key])
            self.assertEqual(people[pregnant_id]["current_pregnancies"][period_key], 1)

    def test_handles_infant(self):
        """Test that TxWic correctly handles infants."""
        infant = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="child",
            age=0,
        )

        result = pe_input(self.screen, [TxWic])
        people = result["household"]["people"]
        infant_id = str(infant.id)

        self.assertIn("age", people[infant_id])
        self.assertIn("wic", people[infant_id])


class TestTxSsiPeInput(TxPeInputTestBase):
    """Tests for TxSsi calculator pe_input dependencies."""

    def test_includes_all_pe_input_fields(self):
        """Test that pe_input includes all TxSsi pe_inputs dependencies."""
        result = pe_input(self.screen, [TxSsi])
        people = result["household"]["people"]
        head_id = str(self.head.id)

        # SSI-specific member dependencies
        ssi_fields = [
            "ssi_countable_resources",
            "ssi_reported",
            "is_blind",
            "is_disabled",
            "ssi_earned_income",
            "ssi_unearned_income",
            "age",
        ]
        for field in ssi_fields:
            self.assertIn(field, people[head_id])

    def test_includes_pe_output_field(self):
        """Test that pe_input includes TxSsi pe_outputs."""
        result = pe_input(self.screen, [TxSsi])
        people = result["household"]["people"]
        head_id = str(self.head.id)

        self.assertIn("ssi", people[head_id])
        self.assertIsInstance(people[head_id]["ssi"], dict)

    def test_disability_fields_populated(self):
        """Test that disability fields are populated correctly."""
        result = pe_input(self.screen, [TxSsi])
        people = result["household"]["people"]

        head = people[str(self.head.id)]
        spouse = people[str(self.spouse.id)]

        self.assertIn("is_disabled", head)
        self.assertIn("is_disabled", spouse)
        self.assertIn("is_blind", head)


class TestTxCsfpPeInput(TxPeInputTestBase):
    """Tests for TxCsfp calculator pe_input dependencies."""

    def test_includes_all_pe_input_fields(self):
        """Test that pe_input includes all TxCsfp pe_inputs dependencies."""
        result = pe_input(self.screen, [TxCsfp])
        household = result["household"]
        spm_unit = household["spm_units"]["spm_unit"]
        people = household["people"]
        head_id = str(self.head.id)

        self.assertIn("school_meal_countable_income", spm_unit)
        self.assertIn("age", people[head_id])

    def test_includes_pe_output_fields(self):
        """Test that pe_input includes TxCsfp pe_outputs."""
        result = pe_input(self.screen, [TxCsfp])
        people = result["household"]["people"]

        for member_id in [str(self.head.id), str(self.spouse.id), str(self.child.id)]:
            self.assertIn("commodity_supplemental_food_program", people[member_id])

    def test_handles_senior_member(self):
        """Test that TxCsfp correctly handles senior members (60+)."""
        senior = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="parent",
            age=65,
        )

        result = pe_input(self.screen, [TxCsfp])
        people = result["household"]["people"]
        senior_id = str(senior.id)

        if people[senior_id]["age"]:
            period_key = list(people[senior_id]["age"].keys())[0]
            self.assertEqual(people[senior_id]["age"][period_key], 65)


class TestTxChipPeInput(TxPeInputTestBase):
    """Tests for TxChip calculator pe_input dependencies."""

    def test_includes_all_pe_input_fields(self):
        """Test that pe_input includes all TxChip pe_inputs dependencies."""
        result = pe_input(self.screen, [TxChip])
        household = result["household"]
        people = household["people"]
        head_id = str(self.head.id)

        # Member-level dependencies
        self.assertIn("age", people[head_id])
        self.assertIn("is_pregnant", people[head_id])
        self.assertIn("is_disabled", people[head_id])
        self.assertIn("ssi_countable_resources", people[head_id])

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
        """Test that pe_input includes TxChip pe_outputs."""
        result = pe_input(self.screen, [TxChip])
        people = result["household"]["people"]

        for member_id in [str(self.head.id), str(self.spouse.id), str(self.child.id)]:
            self.assertIn("chip", people[member_id])

    def test_age_values_match_household_members(self):
        """Test that age values match HouseholdMember data."""
        result = pe_input(self.screen, [TxChip])
        people = result["household"]["people"]

        if people[str(self.head.id)]["age"]:
            period_key = list(people[str(self.head.id)]["age"].keys())[0]
            self.assertEqual(people[str(self.head.id)]["age"][period_key], 35)
            self.assertEqual(people[str(self.spouse.id)]["age"][period_key], 32)
            self.assertEqual(people[str(self.child.id)]["age"][period_key], 8)


# =============================================================================
# Tax Calculator Tests
# =============================================================================


class TestTxEitcPeInput(TxPeInputTestBase):
    """Tests for TxEitc calculator pe_input dependencies."""

    def test_includes_all_pe_input_fields(self):
        """Test that pe_input includes all TxEitc pe_inputs dependencies."""
        result = pe_input(self.screen, [TxEitc])
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
        """Test that pe_input includes TxEitc pe_outputs."""
        result = pe_input(self.screen, [TxEitc])
        tax_units = result["household"]["tax_units"]

        self.assertIn(MAIN_TAX_UNIT, tax_units)
        self.assertIn("eitc", tax_units[MAIN_TAX_UNIT])

    def test_tax_unit_relationships_are_correct(self):
        """Test that tax unit relationships are correctly set."""
        result = pe_input(self.screen, [TxEitc])
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
        """Test that TxEitc handles single parent households correctly."""
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

        result = pe_input(single_parent_screen, [TxEitc])
        tax_units = result["household"]["tax_units"]

        self.assertIn(MAIN_TAX_UNIT, tax_units)
        self.assertIn(str(single_parent.id), tax_units[MAIN_TAX_UNIT]["members"])
        self.assertIn(str(child.id), tax_units[MAIN_TAX_UNIT]["members"])


class TestTxCtcPeInput(TxPeInputTestBase):
    """Tests for TxCtc calculator pe_input dependencies."""

    def test_populates_tax_unit_fields(self):
        """Test that TxCtc populates tax unit and member fields correctly."""
        result = pe_input(self.screen, [TxCtc])
        household = result["household"]
        people = household["people"]
        tax_units = household["tax_units"]

        # Tax unit structure exists
        self.assertIn(MAIN_TAX_UNIT, tax_units)
        main_tax_unit = tax_units[MAIN_TAX_UNIT]

        # All members in tax unit
        self.assertIn(str(self.head.id), main_tax_unit["members"])
        self.assertIn(str(self.spouse.id), main_tax_unit["members"])
        self.assertIn(str(self.child.id), main_tax_unit["members"])

        # CTC output field
        self.assertIn("ctc_value", main_tax_unit)

        # Member fields
        head_id = str(self.head.id)
        self.assertIn("age", people[head_id])
        self.assertIn("is_tax_unit_dependent", people[head_id])
        self.assertIn("employment_income", people[head_id])


class TestTxAcaPeInput(TxPeInputTestBase):
    """Tests for TxAca calculator pe_input dependencies."""

    def test_includes_all_pe_input_fields(self):
        """Test that pe_input includes all TxAca pe_inputs dependencies."""
        result = pe_input(self.screen, [TxAca])
        household = result["household"]
        tax_units = household["tax_units"]
        people = household["people"]
        household_unit = household["households"]["household"]

        # Tax unit exists
        self.assertIn(MAIN_TAX_UNIT, tax_units)

        head_id = str(self.head.id)
        spouse_id = str(self.spouse.id)
        child_id = str(self.child.id)

        # Member-level dependencies
        self.assertIn("age", people[head_id])
        self.assertIn("is_pregnant", people[head_id])
        self.assertIn("is_disabled", people[head_id])
        self.assertIn("is_tax_unit_head", people[head_id])
        self.assertIn("is_tax_unit_spouse", people[spouse_id])
        self.assertIn("is_tax_unit_dependent", people[child_id])

        # Income dependencies
        self.assertIn("employment_income", people[head_id])

        # Household-level dependencies
        self.assertIn("zip_code", household_unit)
        self.assertIn("state_code", household_unit)

    def test_includes_pe_output_field(self):
        """Test that pe_input includes TxAca pe_outputs."""
        result = pe_input(self.screen, [TxAca])
        tax_units = result["household"]["tax_units"]

        self.assertIn(MAIN_TAX_UNIT, tax_units)
        self.assertIn("aca_ptc", tax_units[MAIN_TAX_UNIT])

    def test_zipcode_is_populated(self):
        """Test that zipcode is correctly populated."""
        result = pe_input(self.screen, [TxAca])
        household_unit = result["household"]["households"]["household"]

        if household_unit["zip_code"]:
            period_key = list(household_unit["zip_code"].keys())[0]
            self.assertEqual(household_unit["zip_code"][period_key], "78701")

    def test_income_values_are_correct(self):
        """Test that income values are correctly populated."""
        result = pe_input(self.screen, [TxAca])
        people = result["household"]["people"]
        head_id = str(self.head.id)

        if people[head_id]["employment_income"]:
            period_key = list(people[head_id]["employment_income"].keys())[0]
            self.assertEqual(people[head_id]["employment_income"][period_key], 30000)
            self.assertEqual(people[head_id]["self_employment_income"][period_key], 5000)
            self.assertEqual(people[head_id]["rental_income"][period_key], 12000)


# =============================================================================
# Combined Calculator Tests
# =============================================================================


class TestTxCombinedCalculatorsPeInput(TxPeInputTestBase):
    """Tests for pe_input with multiple TX calculators combined."""

    def test_snap_and_wic_combined(self):
        """Test that pe_input handles both TxSnap and TxWic together."""
        result = pe_input(self.screen, [TxSnap, TxWic])
        household = result["household"]
        spm_unit = household["spm_units"]["spm_unit"]
        people = household["people"]
        head_id = str(self.head.id)

        # TxWic fields
        self.assertIn("school_meal_countable_income", spm_unit)
        self.assertIn("wic", people[head_id])

        # TxSnap fields
        self.assertIn("snap_assets", spm_unit)
        self.assertIn("snap", spm_unit)

    def test_eitc_and_snap_combined(self):
        """Test that pe_input handles both TxEitc and TxSnap together."""
        result = pe_input(self.screen, [TxEitc, TxSnap])
        household = result["household"]
        spm_unit = household["spm_units"]["spm_unit"]
        tax_units = household["tax_units"]

        # TxEitc fields
        self.assertIn(MAIN_TAX_UNIT, tax_units)
        self.assertIn("eitc", tax_units[MAIN_TAX_UNIT])

        # TxSnap fields
        self.assertIn("snap", spm_unit)

    def test_ssi_and_snap_combined(self):
        """Test that pe_input handles both TxSsi and TxSnap together."""
        result = pe_input(self.screen, [TxSsi, TxSnap])
        household = result["household"]
        spm_unit = household["spm_units"]["spm_unit"]
        people = household["people"]
        head_id = str(self.head.id)

        # TxSsi fields
        self.assertIn("ssi", people[head_id])
        self.assertIn("ssi_countable_resources", people[head_id])

        # TxSnap fields
        self.assertIn("snap", spm_unit)

    def test_chip_and_snap_combined(self):
        """Test that pe_input handles both TxChip and TxSnap together."""
        result = pe_input(self.screen, [TxChip, TxSnap])
        household = result["household"]
        spm_unit = household["spm_units"]["spm_unit"]
        people = household["people"]
        head_id = str(self.head.id)

        # TxChip fields
        self.assertIn("chip", people[head_id])

        # TxSnap fields
        self.assertIn("snap", spm_unit)

    def test_aca_and_snap_combined(self):
        """Test that pe_input handles both TxAca and TxSnap together."""
        result = pe_input(self.screen, [TxAca, TxSnap])
        household = result["household"]
        spm_unit = household["spm_units"]["spm_unit"]
        tax_units = household["tax_units"]

        # TxAca fields
        self.assertIn("aca_ptc", tax_units[MAIN_TAX_UNIT])

        # TxSnap fields
        self.assertIn("snap", spm_unit)

    def test_all_state_codes_match(self):
        """Test that state_code is TX regardless of which calculator is used."""
        calculators = [TxSnap, TxWic, TxEitc, TxSsi, TxTanf, TxChip, TxAca]

        for calc in calculators:
            result = pe_input(self.screen, [calc])
            household_unit = result["household"]["households"]["household"]

            if household_unit.get("state_code"):
                period_key = list(household_unit["state_code"].keys())[0]
                self.assertEqual(
                    household_unit["state_code"][period_key],
                    "TX",
                    f"state_code should be TX for {calc.__name__}",
                )

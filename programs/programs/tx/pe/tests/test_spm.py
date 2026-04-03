"""
Unit tests for TX SPM (Supplemental Poverty Measure) PolicyEngine calculator classes.

These tests verify TX-specific calculator logic including:
- Calculator registration
- TX-specific pe_inputs (TxStateCodeDependency)

Note: Tests for Screen.has_benefit() have been moved to screener/tests/test_models.py
as they test Screen model methods, not TX-specific logic.
"""

from django.test import TestCase

from programs.programs.federal.pe.spm import Lifeline, Snap, SchoolLunch, Tanf
from programs.programs.policyengine.calculators.dependencies import household, irs_gross_income, member, spm
from programs.programs.policyengine.calculators.dependencies.household import TxStateCodeDependency
from programs.programs.tx.pe import tx_pe_calculators
from programs.programs.tx.pe.spm import TxLifeline, TxSnap, TxNslp, TxTanf


class TestTxSnap(TestCase):
    """Tests for TxSnap calculator class."""

    def test_exists_and_is_subclass_of_snap(self):
        """
        Test that TxSnap calculator class exists and is registered.

        This verifies the calculator has been set up in the codebase.
        """
        # Verify TxSnap is a subclass of Snap
        self.assertTrue(issubclass(TxSnap, Snap))

        # Verify it has the expected properties
        self.assertEqual(TxSnap.pe_name, "snap")
        self.assertIsNotNone(TxSnap.pe_inputs)
        self.assertGreater(len(TxSnap.pe_inputs), 0)

    def test_is_registered_in_tx_pe_calculators(self):
        """Test that TX SNAP is registered in the calculators dictionary."""
        # Verify tx_snap is in the calculators dictionary
        self.assertIn("tx_snap", tx_pe_calculators)

        # Verify it points to the correct class
        self.assertEqual(tx_pe_calculators["tx_snap"], TxSnap)

    def test_pe_inputs_includes_all_parent_inputs_plus_tx_specific(self):
        """
        Test that TxSnap has all expected pe_inputs from parent and TX-specific.

        TxSnap should inherit all inputs from parent Snap class plus add
        TX-specific dependencies like TxStateCodeDependency.
        """
        # TxSnap should have all parent inputs plus TxStateCodeDependency
        self.assertGreater(len(TxSnap.pe_inputs), len(Snap.pe_inputs))

        # Verify TxStateCodeDependency is in the list
        self.assertIn(household.TxStateCodeDependency, TxSnap.pe_inputs)

        # Verify all parent inputs are present
        for parent_input in Snap.pe_inputs:
            self.assertIn(parent_input, TxSnap.pe_inputs)

    def test_pe_inputs_includes_tx_state_code_dependency(self):
        """
        Test that TxStateCodeDependency is properly added to TX SNAP inputs.

        This is the key TX-specific dependency that sets state_code="TX" for
        PolicyEngine calculations.
        """
        # Verify TxStateCodeDependency is in pe_inputs
        self.assertIn(TxStateCodeDependency, TxSnap.pe_inputs)

        # Verify it's configured correctly
        self.assertEqual(TxStateCodeDependency.state, "TX")
        self.assertEqual(TxStateCodeDependency.field, "state_code")


class TestTxLifeline(TestCase):
    """Tests for TxLifeline calculator class."""

    def test_exists_and_is_subclass_of_lifeline(self):
        """
        Test that TxLifeline calculator class exists and is registered.

        This verifies the calculator has been set up in the codebase.
        """
        # Verify TxLifeline is a subclass of Lifeline
        self.assertTrue(issubclass(TxLifeline, Lifeline))

        # Verify it has the expected properties
        self.assertEqual(TxLifeline.pe_name, "lifeline")
        self.assertIsNotNone(TxLifeline.pe_inputs)
        self.assertGreater(len(TxLifeline.pe_inputs), 0)

    def test_is_registered_in_tx_pe_calculators(self):
        """Test that TX Lifeline is registered in the calculators dictionary."""
        # Verify tx_lifeline is in the calculators dictionary
        self.assertIn("tx_lifeline", tx_pe_calculators)

        # Verify it points to the correct class
        self.assertEqual(tx_pe_calculators["tx_lifeline"], TxLifeline)

    def test_pe_inputs_includes_all_parent_inputs_plus_tx_specific(self):
        """
        Test that TxLifeline has all expected pe_inputs from parent and TX-specific.

        TxLifeline should inherit all inputs from parent Lifeline class plus add
        TX-specific dependencies like TxStateCodeDependency.
        """
        # TxLifeline should have all parent inputs plus TxStateCodeDependency
        self.assertGreater(len(TxLifeline.pe_inputs), len(Lifeline.pe_inputs))

        # Verify TxStateCodeDependency is in the list
        self.assertIn(household.TxStateCodeDependency, TxLifeline.pe_inputs)

        # Verify all parent inputs are present
        for parent_input in Lifeline.pe_inputs:
            self.assertIn(parent_input, TxLifeline.pe_inputs)

    def test_pe_inputs_includes_tx_state_code_dependency(self):
        """
        Test that TxStateCodeDependency is properly added to TX Lifeline inputs.

        This is the key TX-specific dependency that sets state_code="TX" for
        PolicyEngine calculations.
        """
        # Verify TxStateCodeDependency is in pe_inputs
        self.assertIn(TxStateCodeDependency, TxLifeline.pe_inputs)

        # Verify it's configured correctly
        self.assertEqual(TxStateCodeDependency.state, "TX")
        self.assertEqual(TxStateCodeDependency.field, "state_code")


class TestTxNslp(TestCase):
    """Tests for TxNslp (National School Lunch Program) calculator class."""

    def test_exists_and_is_subclass_of_school_lunch(self):
        """
        Test that TxNslp calculator class exists and is registered.

        This verifies the calculator has been set up in the codebase.
        """
        # Verify TxNslp is a subclass of SchoolLunch
        self.assertTrue(issubclass(TxNslp, SchoolLunch))

        # Verify it has the expected properties from parent
        self.assertEqual(TxNslp.pe_name, "school_meal_daily_subsidy")
        self.assertIsNotNone(TxNslp.pe_inputs)
        self.assertGreater(len(TxNslp.pe_inputs), 0)

    def test_is_registered_in_tx_pe_calculators(self):
        """Test that TX NSLP is registered in the calculators dictionary."""
        # Verify tx_nslp is in the calculators dictionary
        self.assertIn("tx_nslp", tx_pe_calculators)

        # Verify it points to the correct class
        self.assertEqual(tx_pe_calculators["tx_nslp"], TxNslp)

    def test_pe_inputs_includes_all_parent_inputs_plus_tx_specific(self):
        """
        Test that TxNslp has all expected pe_inputs from parent and TX-specific.

        TxNslp should inherit all inputs from parent SchoolLunch class plus add
        TX-specific dependencies like TxStateCodeDependency.
        """
        # TxNslp should have all parent inputs plus TxStateCodeDependency
        self.assertGreater(len(TxNslp.pe_inputs), len(SchoolLunch.pe_inputs))

        # Verify TxStateCodeDependency is in the list
        self.assertIn(household.TxStateCodeDependency, TxNslp.pe_inputs)

        # Verify all parent inputs are present
        for parent_input in SchoolLunch.pe_inputs:
            self.assertIn(parent_input, TxNslp.pe_inputs)

    def test_pe_inputs_includes_tx_state_code_dependency(self):
        """
        Test that TxStateCodeDependency is properly added to TX NSLP inputs.

        This is the key TX-specific dependency that sets state_code="TX" for
        PolicyEngine calculations.
        """
        # Verify TxStateCodeDependency is in pe_inputs
        self.assertIn(TxStateCodeDependency, TxNslp.pe_inputs)

        # Verify it's configured correctly
        self.assertEqual(TxStateCodeDependency.state, "TX")
        self.assertEqual(TxStateCodeDependency.field, "state_code")


class TestTxTanf(TestCase):
    """Tests for TxTanf (Temporary Assistance for Needy Families) calculator class."""

    def test_exists_and_is_subclass_of_tanf(self):
        """
        Test that TxTanf calculator class exists and is registered.

        This verifies the calculator has been set up in the codebase.
        """
        # Verify TxTanf is a subclass of Tanf
        self.assertTrue(issubclass(TxTanf, Tanf))

        # Verify it has the expected properties
        self.assertEqual(TxTanf.pe_name, "tx_tanf")
        self.assertIsNotNone(TxTanf.pe_inputs)
        self.assertGreater(len(TxTanf.pe_inputs), 0)
        self.assertIsNotNone(TxTanf.pe_outputs)
        self.assertGreater(len(TxTanf.pe_outputs), 0)

    def test_is_registered_in_tx_pe_calculators(self):
        """Test that TX TANF is registered in the calculators dictionary."""
        # Verify tx_tanf is in the calculators dictionary
        self.assertIn("tx_tanf", tx_pe_calculators)

        # Verify it points to the correct class
        self.assertEqual(tx_pe_calculators["tx_tanf"], TxTanf)

    def test_pe_inputs_includes_all_parent_inputs_plus_tx_specific(self):
        """
        Test that TxTanf has all expected pe_inputs from parent and TX-specific.

        TxTanf should inherit all inputs from parent Tanf class plus add
        TX-specific dependencies like TxStateCodeDependency and income dependencies.
        """
        # TxTanf should have more inputs than the parent Tanf class
        self.assertGreater(len(TxTanf.pe_inputs), len(Tanf.pe_inputs))

        # Verify TxStateCodeDependency is in the list
        self.assertIn(household.TxStateCodeDependency, TxTanf.pe_inputs)

        # Verify TaxUnitDependentDependency is present — required because PolicyEngine's
        # tx_tanf_age_eligible_child checks is_tax_unit_dependent to identify eligible
        # children in the TX certified group (§ 372.104 / 1-TAC-372-307).
        self.assertIn(member.TaxUnitDependentDependency, TxTanf.pe_inputs)

        # Verify person-level income dependencies are present so PE can apply the $120
        # work expense deduction and 1/3 earned income disregard (§ 372.409)
        for dep in irs_gross_income:
            self.assertIn(dep, TxTanf.pe_inputs)

        # Verify all parent inputs are present
        for parent_input in Tanf.pe_inputs:
            self.assertIn(parent_input, TxTanf.pe_inputs)

    def test_pe_inputs_includes_tx_state_code_dependency(self):
        """
        Test that TxStateCodeDependency is properly added to TX TANF inputs.

        This is the key TX-specific dependency that sets state_code="TX" for
        PolicyEngine calculations.
        """
        # Verify TxStateCodeDependency is in pe_inputs
        self.assertIn(TxStateCodeDependency, TxTanf.pe_inputs)

        # Verify it's configured correctly
        self.assertEqual(TxStateCodeDependency.state, "TX")
        self.assertEqual(TxStateCodeDependency.field, "state_code")

    def test_pe_inputs_includes_tax_unit_dependent_dependency(self):
        """
        Test that TaxUnitDependentDependency is in TxTanf pe_inputs.

        PolicyEngine's tx_tanf_age_eligible_child formula requires is_tax_unit_dependent
        to identify eligible children in the TX certified group (per § 372.104 /
        1-TAC-372-307). Without this dependency, is_tax_unit_dependent defaults to
        False for all members, causing tx_tanf_eligible to always be False and the
        program to return $0 for every household.

        Other states (CO, IL, NC) use the federal is_demographic_tanf_eligible check
        which only requires age and pregnancy — no is_tax_unit_dependent needed. TX is
        unique in explicitly modeling the certified group composition this way.
        """
        self.assertIn(member.TaxUnitDependentDependency, TxTanf.pe_inputs)
        self.assertEqual(member.TaxUnitDependentDependency.field, "is_tax_unit_dependent")

    def test_pe_inputs_includes_person_level_income_dependencies(self):
        """
        Test that person-level income dependencies are in TxTanf pe_inputs.

        TX TANF income eligibility uses two tests (§ 372.408):
          - Budgetary needs test: income after $120 work expense < budgetary needs standard
          - Recognizable needs test: income after work expense + 1/3 disregard < 25% of standard

        Providing income at the person level (employment_income, self_employment_income, etc.)
        lets PolicyEngine apply the work expense deduction and earned income disregard through
        its own formula chain. The previous approach of passing gross income directly as
        tx_tanf_countable_earned_income bypassed these deductions, causing households with
        gross wages between ~$188–$402/month (family of 3, 1 parent) to be incorrectly denied.
        """
        for dep in irs_gross_income:
            self.assertIn(dep, TxTanf.pe_inputs)

        # Confirm the old SPM-level overrides are NOT used
        self.assertNotIn(spm.TxTanfCountableEarnedIncomeDependency, TxTanf.pe_inputs)
        self.assertNotIn(spm.TxTanfCountableUnearnedIncomeDependency, TxTanf.pe_inputs)

    def test_pe_outputs_includes_tx_tanf(self):
        """
        Test that TxTanf output dependency is properly configured.

        The calculator should output the tx_tanf variable to PolicyEngine.
        """
        # Verify TxTanf output dependency is in pe_outputs
        self.assertIn(spm.TxTanf, TxTanf.pe_outputs)
        self.assertEqual(spm.TxTanf.field, "tx_tanf")

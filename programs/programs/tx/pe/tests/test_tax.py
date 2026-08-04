"""
Unit tests for TX Tax Unit PolicyEngine calculator classes.

``tx_eitc`` and ``tx_ctc`` register the shared federal ``Eitc``/``Ctc`` classes
directly — neither federal credit has state variance — so those tests only pin
the registration. The calculators' own properties live in
``programs/programs/federal/pe/tests/test_tax.py``.

``TxAca`` is a genuine TX subclass: ACA premiums are state-rated, so it does add
``TxStateCodeDependency`` on top of the federal inputs.
"""

from django.test import TestCase

from programs.programs.federal.pe.tax import Eitc, Ctc, Aca
from programs.programs.policyengine.calculators.dependencies import household
from programs.programs.policyengine.calculators.dependencies.household import (
    TxStateCodeDependency,
)
from programs.programs.policyengine.calculators.registry import (
    all_calculators,
    all_tax_unit_calculators,
)
from programs.programs.tx.pe import tx_pe_calculators, tx_tax_unit_calculators
from programs.programs.tx.pe.tax import TxAca


class TestTxEitc(TestCase):
    """tx_eitc registration against the shared federal Eitc calculator.

    The federal EITC has no Texas variance, so the slug maps to the shared class
    with no TX subclass. Its own properties are asserted once in
    ``programs/programs/federal/pe/tests/test_tax.py``.
    """

    def test_is_federal_eitc_everywhere(self):
        self.assertIs(tx_tax_unit_calculators["tx_eitc"], Eitc)
        self.assertIs(tx_pe_calculators["tx_eitc"], Eitc)
        self.assertIs(all_tax_unit_calculators["tx_eitc"], Eitc)
        self.assertIs(all_calculators["tx_eitc"], Eitc)

    def test_matches_builtin_federal_registry_key(self):
        """Same calculator the federal registry serves as ``eitc`` — no TX subclass."""
        self.assertIs(all_tax_unit_calculators["tx_eitc"], all_tax_unit_calculators["eitc"])


class TestTxCtc(TestCase):
    """tx_ctc registration against the shared federal Ctc calculator.

    The federal CTC has no Texas variance, so the slug maps to the shared class
    with no TX subclass. Its own properties (``pe_name``, ``pe_outputs``, the input
    set, and the absence of a state code) are asserted once in
    ``programs/programs/federal/pe/tests/test_tax.py``.
    """

    def test_is_federal_ctc_everywhere(self):
        self.assertIs(tx_tax_unit_calculators["tx_ctc"], Ctc)
        self.assertIs(tx_pe_calculators["tx_ctc"], Ctc)
        self.assertIs(all_tax_unit_calculators["tx_ctc"], Ctc)
        self.assertIs(all_calculators["tx_ctc"], Ctc)

    def test_matches_builtin_federal_registry_key(self):
        """Same calculator the federal registry serves as ``ctc`` — no TX subclass."""
        self.assertIs(all_tax_unit_calculators["tx_ctc"], all_tax_unit_calculators["ctc"])


class TestTxAca(TestCase):
    """Tests for TxAca calculator class."""

    def test_exists_and_is_subclass_of_aca(self):
        """
        Test that TxAca calculator class exists and inherits from Aca.

        This verifies the calculator has been set up in the codebase.
        """
        # Verify TxAca has the expected properties
        self.assertEqual(TxAca.pe_name, "aca_ptc")
        self.assertIsNotNone(TxAca.pe_inputs)
        self.assertGreater(len(TxAca.pe_inputs), 0)

        # Verify it inherits from Aca
        self.assertTrue(issubclass(TxAca, Aca))

    def test_is_registered_in_tx_pe_calculators(self):
        """Test that TX ACA is registered in the calculators dictionary."""
        # Verify tx_aca is in the calculators dictionary
        self.assertIn("tx_aca", tx_pe_calculators)

        # Verify it points to the correct class
        self.assertEqual(tx_pe_calculators["tx_aca"], TxAca)

    def test_pe_inputs_includes_all_parent_inputs_plus_tx_specific(self):
        """
        Test that TxAca has all expected pe_inputs from parent and TX-specific.

        TxAca should inherit all inputs from parent Aca class plus add
        TX-specific dependencies like TxStateCodeDependency.
        """
        # TxAca should have all parent inputs plus TxStateCodeDependency
        self.assertGreater(len(TxAca.pe_inputs), len(Aca.pe_inputs))

        # Verify TxStateCodeDependency is in the list
        self.assertIn(household.TxStateCodeDependency, TxAca.pe_inputs)

        # Verify all parent inputs are present
        for parent_input in Aca.pe_inputs:
            self.assertIn(parent_input, TxAca.pe_inputs)

    def test_pe_inputs_includes_tx_state_code_dependency(self):
        """
        Test that TxStateCodeDependency is properly added to TX ACA inputs.

        This is the key TX-specific dependency that sets state_code="TX" for
        PolicyEngine calculations.
        """
        # Verify TxStateCodeDependency is in pe_inputs
        self.assertIn(TxStateCodeDependency, TxAca.pe_inputs)

        # Verify it's configured correctly
        self.assertEqual(TxStateCodeDependency.state, "TX")
        self.assertEqual(TxStateCodeDependency.field, "state_code")

    def test_pe_name_matches_federal_aca(self):
        """
        Test that TxAca uses the same pe_name as federal ACA.

        Since this is the federal ACA Premium Tax Credit program for Texas residents,
        it should use the same PolicyEngine name as the federal calculator.
        """
        self.assertEqual(TxAca.pe_name, "aca_ptc")
        self.assertEqual(TxAca.pe_name, Aca.pe_name)

    def test_pe_outputs_inherits_from_federal_aca(self):
        """
        Test that TxAca uses the same pe_outputs as federal ACA.

        The outputs should be the same since this is calculating
        the federal ACA Premium Tax Credit benefit amount.
        """
        self.assertEqual(TxAca.pe_outputs, Aca.pe_outputs)

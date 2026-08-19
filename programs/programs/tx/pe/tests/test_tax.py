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

from programs.framework.pe_dependencies import household
from programs.framework.pe_dependencies.household import (
    TxStateCodeDependency,
)
from programs.programs.cross_white_label.eitc.base import Eitc
from programs.programs.cross_white_label.eitc.tx import TxEitc
from programs.programs.cross_white_label.ctc.base import Ctc
from programs.programs.cross_white_label.ctc.tx import TxCtc
from programs.programs.cross_white_label.aca.base import Aca
from programs.programs.cross_white_label.aca.tx import TxAca


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


class TestTxCtc(TestCase):
    """tx_ctc registration against the shared federal Ctc calculator.

    The federal CTC has no Texas variance, so the slug maps to the shared class
    with no TX subclass. Its own properties (``pe_name``, ``pe_outputs``, the input
    set, and the absence of a state code) are asserted once in
    ``programs/programs/federal/pe/tests/test_tax.py``.
    """

    def test_is_the_federal_calculator_with_nothing_added(self):
        """A thin subclass of the federal calculator: same PE variable, same inputs.

        TX has no state CTC, so ``tx_ctc`` must not diverge from the federal
        credit. It is its own class only so the registry maps one key to one
        calculator. Asserting it overrides nothing is stricter than asserting
        identity with ``Ctc`` was: a subclass that added an input would still be a
        subclass, but would fail here.
        """
        self.assertTrue(issubclass(TxCtc, Ctc))
        self.assertEqual(TxCtc.pe_name, Ctc.pe_name)
        self.assertEqual(list(TxCtc.pe_inputs), list(Ctc.pe_inputs))
        self.assertEqual(list(TxCtc.pe_outputs), list(Ctc.pe_outputs))


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

"""TX tests."""

from django.test import TestCase
from programs.programs.cross_white_label.liheap.tx import TxCeap
from programs.framework.pe_dependencies.household import TxStateCodeDependency
from programs.framework.pe_dependencies import irs_gross_income
from programs.framework.pe_dependencies import receipt_contract
from programs.framework.pe_dependencies import spm


class TestTxCeap(TestCase):
    """Tests for TxCeap (TX Comprehensive Energy Assistance Program / LIHEAP) calculator class."""

    def test_exists_with_expected_pe_config(self):
        """TxCeap maps to the tx_ceap PE variable and has inputs/outputs configured."""
        self.assertEqual(TxCeap.pe_name, "tx_ceap")
        self.assertIsNotNone(TxCeap.pe_inputs)
        self.assertGreater(len(TxCeap.pe_inputs), 0)
        self.assertIsNotNone(TxCeap.pe_outputs)
        self.assertGreater(len(TxCeap.pe_outputs), 0)

    def test_pe_inputs_includes_tx_state_code_dependency(self):
        """TxStateCodeDependency gates tx_ceap to TX (defined_for=StateCode.TX)."""
        self.assertIn(TxStateCodeDependency, TxCeap.pe_inputs)
        self.assertEqual(TxStateCodeDependency.state, "TX")

    def test_pe_inputs_includes_income_and_energy_expense(self):
        """
        tx_ceap needs gross income (for the 150% FPL income test and benefit tier) and
        energy expenses (the benefit is capped at electricity_expense + gas_expense).
        """
        for dep in irs_gross_income:
            self.assertIn(dep, TxCeap.pe_inputs)
        self.assertIn(spm.TxCeapEnergyExpenseDependency, TxCeap.pe_inputs)
        self.assertEqual(spm.TxCeapEnergyExpenseDependency.field, "electricity_expense")

    def test_pe_outputs_includes_tx_ceap(self):
        """The calculator outputs the tx_ceap variable to PolicyEngine."""
        self.assertIn(spm.TxCeap, TxCeap.pe_outputs)
        self.assertEqual(spm.TxCeap.field, "tx_ceap")

    def test_pe_inputs_includes_the_receipt_contract(self):
        """
        tx_ceap counts SSI via applicable_ssi, which follows the `ssi` input. The receipt
        contract supplies the household's reported amount where they report one, and
        suppresses PolicyEngine's simulated SSI otherwise — without it, modeled SSI counts
        as income and SS/SSI households land in the wrong (too-generous) benefit tier.
        """
        for dep in receipt_contract:
            self.assertIn(dep, TxCeap.pe_inputs)

    def test_receipt_inputs_are_version_gated(self):
        """
        Every field the contract adds carries the floor of the release that introduced it, so
        none is ever sent to an earlier model — an unknown input 400s the whole request, taking
        every PE program in it down. The amount inputs (`ssi`, `tanf`) predate it and stay
        ungated.
        """
        for dep in receipt_contract:
            expected = () if dep.field in ("ssi", "tanf") else (1, 779, 3)
            self.assertEqual(dep.min_pe_version, expected, dep.field)

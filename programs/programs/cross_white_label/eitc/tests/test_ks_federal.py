"""KS federal tests."""

from django.test import TestCase

from integrations.clients.policyengine.registry import all_calculators
from programs.framework.pe_dependencies.household import StateCode
from programs.programs.cross_white_label.eitc.base import Eitc
from programs.programs.cross_white_label.eitc.ks_federal import KsEitcFederal


class TestKsEitcFederal(TestCase):
    """ks_eitc_federal registration against the shared federal Eitc calculator.

    Distinct from ``ks_eitc``, which is the Kansas credit and has its own class.
    """

    def test_is_the_federal_calculator_with_nothing_added(self):
        """PolicyEngine's federal EITC has no Kansas variance, so this must not
        diverge from the federal credit."""
        self.assertTrue(issubclass(KsEitcFederal, Eitc))
        self.assertEqual(KsEitcFederal.pe_name, Eitc.pe_name)
        self.assertEqual(list(KsEitcFederal.pe_inputs), list(Eitc.pe_inputs))
        self.assertEqual(list(KsEitcFederal.pe_outputs), list(Eitc.pe_outputs))

    def test_registers_under_its_own_key(self):
        self.assertIs(all_calculators["ks_eitc_federal"], KsEitcFederal)

    def test_is_not_the_kansas_eitc(self):
        """The federal and Kansas EITC slugs resolve to different calculators."""
        self.assertIsNot(
            all_calculators["ks_eitc_federal"],
            all_calculators["ks_eitc"],
        )

    def test_reads_the_federal_variable_not_the_kansas_one(self):
        """``ks_eitc`` reads ``ks_total_eitc``; this reads federal ``eitc``."""
        self.assertEqual(KsEitcFederal.pe_name, "eitc")
        self.assertNotEqual(
            KsEitcFederal.pe_name,
            all_calculators["ks_eitc"].pe_name,
        )

    def test_sends_no_state_code(self):
        """The federal formula ignores ``state_code``, so sending Kansas's would be
        an input the formula never reads."""
        for pe_input in KsEitcFederal.pe_inputs:
            self.assertFalse(
                isinstance(pe_input, type) and issubclass(pe_input, StateCode),
                f"{pe_input.__name__} sends a state code to the federal EITC",
            )

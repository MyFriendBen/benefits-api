"""KS tests."""

from programs.programs.cross_white_label.msp.ks import KsMsp
from programs.framework.pe_dependencies.household import KsStateCodeDependency
from programs.programs.cross_white_label.medicaid.base import Medicaid
from django.test import TestCase
from programs.framework.pe_dependencies import member as member_deps
from programs.programs.cross_white_label.medicaid.ks import KsKanCare


class TestKsMspWiring(TestCase):
    """
    KS-specific MSP wiring. The shared contract every state's MSP must satisfy (pe_name,
    pe_category, pe_outputs, no federal input dropped, the Medicaid input set, exactly one
    state code matching the slug, no ``member_value`` override) is asserted once for all
    registered subclasses in ``federal/pe/tests/test_msp.py``.
    """

    def test_program_code_is_ks_medicare_savings(self):
        self.assertEqual(KsMsp.program_code, "ks_medicare_savings")

    def test_pe_name_is_msp(self):
        self.assertEqual(KsMsp.pe_name, "msp")

    def test_pe_inputs_includes_ks_state_code(self):
        """Resolves the MSP asset-test-applies parameter, which is true for Kansas."""
        self.assertIn(KsStateCodeDependency, KsMsp.pe_inputs)

    def test_pe_inputs_includes_medicaid_inputs(self):
        """MSP needs *Medicaid.pe_inputs for the QI ~is_medicaid_eligible check and for the
        msp_asset_eligible resource test."""
        for medicaid_input in Medicaid.pe_inputs:
            self.assertIn(medicaid_input, KsMsp.pe_inputs)

    def test_pe_inputs_includes_ssi_countable_resources(self):
        """Without it, msp_asset_eligible sees $0 and an over-asset applicant wrongly qualifies."""
        self.assertIn(member_deps.SsiCountableResourcesDependency, KsMsp.pe_inputs)


class TestKsMspKanCareAssetConsistency(TestCase):
    """KanCare and MSP both read ssi_countable_resources in one shared simulation, so they must
    screen assets identically — sending it from one but not the other corrupts that program's
    eligibility. These assertions fail if the two ever diverge."""

    def test_kancare_and_msp_agree_on_ssi_countable_resources(self):
        kancare_sends = member_deps.SsiCountableResourcesDependency in KsKanCare.pe_inputs
        msp_sends = member_deps.SsiCountableResourcesDependency in KsMsp.pe_inputs
        self.assertEqual(kancare_sends, msp_sends)

    def test_both_send_ssi_countable_resources(self):
        self.assertIn(member_deps.SsiCountableResourcesDependency, KsKanCare.pe_inputs)
        self.assertIn(member_deps.SsiCountableResourcesDependency, KsMsp.pe_inputs)

"""IL tests."""

from programs.programs.cross_white_label.msp.il import IlMsp
from programs.framework.pe_dependencies.household import IlStateCodeDependency
from programs.framework.pe_base import PolicyEngineMembersCalculator
from django.test import TestCase


class TestIlMsp(TestCase):
    """
    IL-specific MSP wiring. The shared contract every state's MSP must satisfy (pe_name,
    pe_category, pe_outputs, no federal input dropped, the Medicaid input set, exactly one
    state code matching the slug, no ``member_value`` override) is asserted once for all
    registered subclasses in ``federal/pe/tests/test_msp.py``.
    """

    def test_exists_and_is_subclass_of_policy_engine_members_calculator(self):
        """Test that IlMsp is a subclass of PolicyEngineMembersCalculator."""
        self.assertTrue(issubclass(IlMsp, PolicyEngineMembersCalculator))

    def test_pe_name_is_msp(self):
        """Test that IlMsp has the correct pe_name for PolicyEngine API calls."""
        self.assertEqual(IlMsp.pe_name, "msp")

    def test_pe_inputs_includes_il_state_code_dependency(self):
        """Resolves the MSP asset-test-applies parameter, which is true for Illinois."""
        self.assertIn(IlStateCodeDependency, IlMsp.pe_inputs)

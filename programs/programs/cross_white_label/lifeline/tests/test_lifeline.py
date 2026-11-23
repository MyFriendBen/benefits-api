"""Federal Lifeline tests."""

from django.test import SimpleTestCase

from programs.programs.cross_white_label.lifeline.base import Lifeline
import programs.framework.pe_dependencies as dependency


class TestLifelineWiring(SimpleTestCase):
    def test_pe_inputs_includes_broadband_and_phone_cost(self):
        """PE caps the benefit at combined phone + broadband cost, so both are needed
        or an eligible household's value collapses toward $0."""
        self.assertIn(dependency.spm.BroadbandCostDependency, Lifeline.pe_inputs)
        self.assertIn(dependency.spm.PhoneCostDependency, Lifeline.pe_inputs)

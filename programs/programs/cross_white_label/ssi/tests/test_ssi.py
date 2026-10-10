"""Federal SSI tests."""

from django.test import SimpleTestCase

from programs.programs.cross_white_label.ssi.base import Ssi
import programs.framework.pe_dependencies as dependency


class TestSsiWiring(SimpleTestCase):
    def test_pe_inputs_includes_disability_criteria(self):
        """PE gates SSI disability on ``meets_ssi_disability_criteria``; unsent, every disabled
        applicant under 65 reads as not disabled and is valued at $0."""
        self.assertIn(dependency.member.MeetsSsiDisabilityCriteriaDependency, Ssi.pe_inputs)

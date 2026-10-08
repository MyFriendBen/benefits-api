"""Federal TANF tests."""

from django.test import SimpleTestCase

from programs.programs.cross_white_label.tanf.base import Tanf
import programs.framework.pe_dependencies as dependency


class TestTanfWiring(SimpleTestCase):
    def test_pe_inputs_includes_in_secondary_school(self):
        """Unsent, it reads False for everyone and narrows the minor-child age limit."""
        self.assertIn(dependency.member.InSecondarySchoolDependency, Tanf.pe_inputs)

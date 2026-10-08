"""IL tests."""

from programs.programs.cross_white_label.lifeline.base import Lifeline
from programs.programs.cross_white_label.lifeline.il import IlLifeline
import programs.framework.pe_dependencies as dependency
from django.test import TestCase


class TestIlLifelineWiring(TestCase):
    """IlLifeline registration and IL-specific pe_inputs handling."""

    def test_program_code_is_state_scoped(self):
        """The bare ``lifeline`` code belongs to the base class, which must not back a row."""
        self.assertEqual(IlLifeline.program_code, "il_lifeline")

    def test_pe_name_is_lifeline(self):
        """The federal SPM-level variable; IL adds no state variable of its own."""
        self.assertEqual(IlLifeline.pe_name, "lifeline")

    def test_pe_inputs_adds_exactly_the_state_code(self):
        added = [d for d in IlLifeline.pe_inputs if d not in Lifeline.pe_inputs]
        self.assertEqual(added, [dependency.household.IlStateCodeDependency])

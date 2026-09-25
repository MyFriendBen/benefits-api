"""NC tests."""

from programs.programs.cross_white_label.lifeline.nc import NcLifeline
from django.test import TestCase


class TestNcLifelineWiring(TestCase):
    """NcLifeline registration and NC-specific pe_inputs handling."""

    def test_program_code_is_state_scoped(self):
        """The bare ``lifeline`` code belongs to the base class, which must not back a row."""
        self.assertEqual(NcLifeline.program_code, "nc_lifeline")

    def test_pe_name_is_lifeline(self):
        """The federal SPM-level variable; NC adds no state variable of its own."""
        self.assertEqual(NcLifeline.pe_name, "lifeline")

"""MA tests."""

from programs.programs.cross_white_label.lifeline.ma import MaLifeline
from django.test import TestCase


class TestMaLifelineWiring(TestCase):
    """MaLifeline registration and MA-specific pe_inputs handling."""

    def test_program_code_is_state_scoped(self):
        """The bare ``lifeline`` code belongs to the base class, which must not back a row."""
        self.assertEqual(MaLifeline.program_code, "ma_lifeline")

    def test_pe_name_is_lifeline(self):
        """The federal SPM-level variable; MA adds no state variable of its own."""
        self.assertEqual(MaLifeline.pe_name, "lifeline")

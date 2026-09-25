"""CO tests."""

from programs.programs.cross_white_label.lifeline.co import CoLifeline
from django.test import TestCase


class TestCoLifelineWiring(TestCase):
    """CoLifeline registration and CO-specific pe_inputs handling."""

    def test_program_code_is_state_scoped(self):
        """The bare ``lifeline`` code belongs to the base class, which must not back a row."""
        self.assertEqual(CoLifeline.program_code, "co_lifeline")

    def test_pe_name_is_lifeline(self):
        """The federal SPM-level variable; CO adds no state variable of its own."""
        self.assertEqual(CoLifeline.pe_name, "lifeline")

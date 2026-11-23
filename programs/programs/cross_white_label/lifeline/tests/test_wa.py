"""WA tests."""

from django.test import TestCase
from programs.programs.cross_white_label.lifeline.wa import WaLifeline


class TestWaLifeline(TestCase):
    """Tests for WaLifeline calculator class."""

    def test_pe_name_is_lifeline(self):
        """Test that pe_name is lifeline."""
        self.assertEqual(WaLifeline.pe_name, "lifeline")

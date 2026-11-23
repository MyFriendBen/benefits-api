"""WA tests."""

from django.test import TestCase
from programs.programs.cross_white_label.snap.wa import WaSnap, WaFap


class TestWaSnap(TestCase):
    """Tests for WaSnap calculator class."""

    def test_pe_name_is_snap(self):
        """Test that pe_name is snap."""
        self.assertEqual(WaSnap.pe_name, "snap_if_takes_up")


class TestWaFap(TestCase):
    """Tests for WaFap calculator class."""

    def test_program_code_is_wa_fap(self):
        """Test that program_code backs the wa_fap program row."""
        self.assertEqual(WaFap.program_code, "wa_fap")

    def test_pe_name_matches_wa_snap(self):
        """
        Test that FAP resolves the same PolicyEngine variable as Basic Food.

        FAP pays the same amount as Basic Food, so it inherits pe_name rather
        than declaring its own.
        """
        self.assertEqual(WaFap.pe_name, WaSnap.pe_name)

    def test_pe_inputs_match_wa_snap(self):
        """
        Test that WaFap requests exactly the same PolicyEngine inputs as WaSnap.

        FAP pays the same amount as Basic Food, so any divergence in inputs
        would make the two programs return different dollar values for the
        same household.
        """
        self.assertEqual(WaFap.pe_inputs, WaSnap.pe_inputs)

    def test_pe_outputs_match_wa_snap(self):
        """Test that both programs read the same PolicyEngine output."""
        self.assertEqual(WaFap.pe_outputs, WaSnap.pe_outputs)

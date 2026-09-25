"""WA tests."""

from django.test import TestCase
from programs.programs.cross_white_label.ssi.wa import WaSsi


class TestWaSsi(TestCase):
    """Tests for WaSsi calculator class wiring."""

    def test_pe_name_is_ssi(self):
        """pe_name is inherited from Ssi and resolves to PolicyEngine's `ssi` variable."""
        self.assertEqual(WaSsi.pe_name, "ssi_if_takes_up")

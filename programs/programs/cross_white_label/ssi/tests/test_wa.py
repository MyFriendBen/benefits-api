"""WA tests."""

from django.test import TestCase
from programs.programs.cross_white_label.ssi.base import Ssi
from programs.programs.cross_white_label.ssi.wa import WaSsi
from programs.framework.pe_dependencies.household import WaStateCodeDependency


class TestWaSsi(TestCase):
    """Tests for WaSsi calculator class wiring."""

    def test_pe_name_is_ssi(self):
        """pe_name is inherited from Ssi and resolves to PolicyEngine's `ssi` variable."""
        self.assertEqual(WaSsi.pe_name, "ssi_if_takes_up")

    def test_adds_nothing_but_the_state_code(self):
        """WA pays no general SSI state supplement, so the state code is the only addition."""
        self.assertEqual(set(WaSsi.pe_inputs) - set(Ssi.pe_inputs), {WaStateCodeDependency})

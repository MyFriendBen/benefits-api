"""MO tests."""

from django.test import TestCase

from programs.framework.pe_dependencies.household import MoStateCodeDependency
from programs.programs.cross_white_label.snap.base import Snap
from programs.programs.cross_white_label.snap.mo import MoSnap


class TestMoSnap(TestCase):
    """Tests for Missouri SNAP calculator."""

    def test_program_code_is_mo_snap(self):
        self.assertEqual(MoSnap.program_code, "mo_snap")

    def test_pe_name_is_the_ungated_federal_variable(self):
        """Missouri adds no calculator of its own: the amount comes from the federal
        variable, which is the ungated one so a household not yet enrolled sees what
        applying would get them."""
        self.assertEqual(MoSnap.pe_name, "snap_if_takes_up")

    def test_adds_nothing_but_the_state_code(self):
        """Missouri's variance is all state-keyed parameters inside PolicyEngine's federal
        SNAP tree. An extra input here would mean something is being computed on our side
        that PolicyEngine should be resolving."""
        self.assertEqual(set(MoSnap.pe_inputs) - set(Snap.pe_inputs), {MoStateCodeDependency})

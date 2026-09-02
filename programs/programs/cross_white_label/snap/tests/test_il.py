"""IL tests."""

from programs.programs.cross_white_label.snap.il import IlSnap
from programs.framework.pe_dependencies.household import IlStateCodeDependency
from programs.programs.cross_white_label.snap.base import Snap
from django.test import TestCase


class TestIlSnap(TestCase):
    """Tests for Illinois SNAP calculator."""

    def test_exists_and_is_subclass_of_snap(self):
        """Test that IlSnap is a subclass of federal Snap."""
        self.assertTrue(issubclass(IlSnap, Snap))

    def test_pe_inputs_includes_il_state_code_dependency(self):
        """Test that IlStateCodeDependency is in pe_inputs."""
        self.assertIn(IlStateCodeDependency, IlSnap.pe_inputs)

    def test_pe_inputs_includes_all_parent_inputs(self):
        """Test that all parent Snap inputs are included."""
        for parent_input in Snap.pe_inputs:
            self.assertIn(parent_input, IlSnap.pe_inputs)

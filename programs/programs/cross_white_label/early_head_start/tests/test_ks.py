"""KS tests."""

from programs.programs.cross_white_label.early_head_start.base import EarlyHeadStart
from programs.programs.cross_white_label.early_head_start.ks import KsEarlyHeadStart
from programs.framework.pe_dependencies.household import KsStateCodeDependency
from django.test import TestCase


class TestKsEarlyHeadStartWiring(TestCase):
    """
    KS-specific wiring for Early Head Start (birth-3 / pregnant). A thin wrapper on
    the federal ``EarlyHeadStart`` PE calculator, adding only the KS state code.

    The shared contract (pe_name, pe_outputs, no federal input dropped, exactly one
    state code matching the slug, no ``member_value`` override) is asserted once for
    all registered subclasses in ``federal/pe/tests/test_head_start.py``.

    The spec's dollar-value scenarios ($13,323 per eligible individual) are verified
    end-to-end against the live PolicyEngine API — see
    ``programs/programs/ks/early_head_start/spec.md``.
    """

    def test_pe_inputs_includes_ks_state_code(self):
        self.assertTrue(issubclass(KsEarlyHeadStart, EarlyHeadStart))
        self.assertIn(KsStateCodeDependency, KsEarlyHeadStart.pe_inputs)

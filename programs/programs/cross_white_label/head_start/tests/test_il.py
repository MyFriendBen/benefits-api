"""IL tests."""

from programs.programs.cross_white_label.head_start.base import HeadStart
from programs.programs.cross_white_label.head_start.il import IlHeadStart
from programs.framework.pe_dependencies.household import IlStateCodeDependency
from django.test import TestCase


class TestIlHeadStartWiring(TestCase):
    """
    IlHeadStart is a thin wrapper on the federal ``HeadStart`` PE calculator that
    adds only the IL state code — all eligibility and the per-child value come
    from PolicyEngine's ``head_start`` variable with no IL-specific variance.

    The shared contract every state's Head Start must satisfy (pe_name, pe_outputs,
    no federal input dropped, exactly one state code matching the slug, no
    ``member_value`` override) is asserted once for all registered subclasses in
    ``federal/pe/tests/test_head_start.py``. Only the IL-specific wiring is
    asserted here.

    The spec's dollar-value scenarios ($17,227 per eligible child) are verified
    against PolicyEngine's IL spending/enrollment parameters — see
    ``programs/programs/cross_white_label/head_start/specs/il.md``.
    """

    def test_is_subclass_of_head_start(self):
        self.assertTrue(issubclass(IlHeadStart, HeadStart))

    def test_pe_inputs_includes_il_state_code(self):
        """The IL state code is what selects IL's spending/enrollment parameters in PE,
        and so what makes the per-child value Illinois' rather than another state's."""
        self.assertTrue(issubclass(IlHeadStart, HeadStart))
        self.assertIn(IlStateCodeDependency, IlHeadStart.pe_inputs)

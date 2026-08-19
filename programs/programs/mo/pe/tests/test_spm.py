"""
Unit tests for the MO SPM-level PolicyEngine calculators ``MoLifeline`` (mo_lifeline)
and ``MoNslp`` (mo_nslp).

Both are straight passthroughs to their federal PolicyEngine calculators, so the MFB-side
surface under test is registration and ``pe_inputs`` wiring rather than benefit math.

MoLifeline is a Fed (as-is) program: PolicyEngine's ``lifeline`` supplies eligibility and
value unchanged, and Missouri has no state supplement in PE (only CA/OR via ``in_effect``,
plus explicit TX and KS supplements). These tests pin that MO stays on the federal branch
and that the state code reaches PE.

MoNslp is a straight passthrough to PolicyEngine's federal ``SchoolLunch`` calculator:
eligibility and the benefit dollar value come from PE, so there is no MFB-side routing
to unit-test. What *does* live on the MFB side is the ``pe_inputs`` wiring, and one
input beyond the federal set is load-bearing:

  - ``MoStateCodeDependency`` — PE's school meal tier branches on the state's
    universal-free-meals election, and ``pe_input()`` never sends ``state_code`` on
    its own. Without this input PE falls back to its default state, which *does* have
    universal free meals, so every MO household would be scored FREE tier at any
    income. Verified live against PE ``current``: a household of 2 (one 9-year-old) at
    $90,000/yr returns $0 / PAID with ``state_code=MO`` but $1130.96 / FREE with the
    state code omitted.

These tests pin that wiring so a future refactor can't silently drop it.
"""

from django.test import TestCase

import programs.framework.pe_dependencies as dependency
from programs.programs.cross_white_label.lifeline.base import Lifeline
from programs.programs.cross_white_label.lifeline.mo import MoLifeline
from programs.programs.cross_white_label.nslp.base import SchoolLunch
from programs.programs.cross_white_label.nslp.mo import MoNslp


class TestMoLifelineWiring(TestCase):
    """MoLifeline registration and MO-specific pe_inputs handling."""

    def test_is_subclass_of_lifeline(self):
        self.assertTrue(issubclass(MoLifeline, Lifeline))

    def test_pe_name_is_lifeline(self):
        """The federal SPM-level variable; MO adds no state variable of its own."""
        self.assertEqual(MoLifeline.pe_name, "lifeline")

    def test_pe_outputs_are_inherited_from_lifeline(self):
        self.assertEqual(MoLifeline.pe_outputs, [dependency.spm.Lifeline])

    # --- the MO-specific input ---

    def test_pe_inputs_includes_mo_state_code(self):
        """``pe_input()`` never sends state_code on its own; PE's Lifeline chain reads
        it for both the state supplement branch and the TX FPG expansion."""
        self.assertIn(dependency.household.MoStateCodeDependency, MoLifeline.pe_inputs)

    def test_mo_state_code_dependency_sends_mo(self):
        self.assertEqual(dependency.household.MoStateCodeDependency.state, "MO")

    # --- federal inputs must survive the MO override ---

    def test_pe_inputs_retains_all_federal_inputs(self):
        for federal_input in Lifeline.pe_inputs:
            self.assertIn(federal_input, MoLifeline.pe_inputs)

    def test_pe_inputs_includes_broadband_and_phone_cost(self):
        """PE caps the benefit at combined phone + broadband cost, so both are needed
        or an eligible household's value collapses toward $0."""
        self.assertIn(dependency.spm.BroadbandCostDependency, MoLifeline.pe_inputs)
        self.assertIn(dependency.spm.PhoneCostDependency, MoLifeline.pe_inputs)

    def test_pe_inputs_adds_exactly_one_input_over_federal(self):
        """Fed (as-is): the state code is the only MO addition."""
        self.assertEqual(len(MoLifeline.pe_inputs), len(Lifeline.pe_inputs) + 1)


class TestMoNslpWiring(TestCase):
    """MoNslp registration and MO-specific pe_inputs handling."""

    def test_is_subclass_of_school_lunch(self):
        self.assertTrue(issubclass(MoNslp, SchoolLunch))

    def test_pe_name_is_school_meal_net_subsidy(self):
        """The annual net subsidy, not the per-day ``school_meal_daily_subsidy``."""
        self.assertEqual(MoNslp.pe_name, "school_meal_net_subsidy")

    def test_pe_outputs_are_inherited_from_school_lunch(self):
        self.assertEqual(
            MoNslp.pe_outputs,
            [dependency.spm.SchoolMealNetSubsidy, dependency.spm.SchoolMealTier],
        )

    # --- the load-bearing input (over-eligibility regression guard) ---

    def test_pe_inputs_includes_mo_state_code(self):
        """Dropping this scores every MO household FREE tier at any income."""
        self.assertIn(dependency.household.MoStateCodeDependency, MoNslp.pe_inputs)

    # --- federal inputs must survive the MO override ---

    def test_pe_inputs_retains_all_federal_inputs(self):
        for federal_input in SchoolLunch.pe_inputs:
            self.assertIn(federal_input, MoNslp.pe_inputs)

    def test_pe_inputs_includes_school_meal_countable_income(self):
        self.assertIn(dependency.spm.SchoolMealCountableIncomeDependency, MoNslp.pe_inputs)

    def test_pe_inputs_includes_age(self):
        """PE derives ``is_in_k12_school`` from age; without it there are no K-12 children
        to value and the subsidy collapses to $0."""
        self.assertIn(dependency.member.AgeDependency, MoNslp.pe_inputs)

    def test_pe_inputs_adds_exactly_one_input_over_federal(self):
        self.assertEqual(len(MoNslp.pe_inputs), len(SchoolLunch.pe_inputs) + 1)

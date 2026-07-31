"""
Unit tests for the MO SPM-level PolicyEngine calculator ``MoNslp`` (mo_nslp).

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

from programs.programs.federal.pe.spm import SchoolLunch
from programs.programs.mo.pe import mo_pe_calculators, mo_spm_calculators
from programs.programs.mo.pe.spm import MoNslp
from programs.programs.policyengine.calculators.registry import (
    all_calculators,
    all_spm_unit_calculators,
)
import programs.programs.policyengine.calculators.dependencies as dependency


class TestMoNslpWiring(TestCase):
    """MoNslp registration and MO-specific pe_inputs handling."""

    def test_is_subclass_of_school_lunch(self):
        self.assertTrue(issubclass(MoNslp, SchoolLunch))

    def test_pe_name_is_school_meal_net_subsidy(self):
        """The annual net subsidy, not the per-day ``school_meal_daily_subsidy``."""
        self.assertEqual(MoNslp.pe_name, "school_meal_net_subsidy")

    def test_is_registered_in_mo_spm_calculators(self):
        self.assertIn("mo_nslp", mo_spm_calculators)
        self.assertIs(mo_spm_calculators["mo_nslp"], MoNslp)

    def test_is_registered_in_mo_pe_calculators(self):
        self.assertIn("mo_nslp", mo_pe_calculators)
        self.assertIs(mo_pe_calculators["mo_nslp"], MoNslp)

    def test_is_registered_in_the_global_registry(self):
        """screener.views matches Program.name_abbreviated against all_calculators keys,
        so the MO spm calculators must be spread into the global registry too."""
        self.assertIn("mo_nslp", all_spm_unit_calculators)
        self.assertIs(all_spm_unit_calculators["mo_nslp"], MoNslp)
        self.assertIn("mo_nslp", all_calculators)
        self.assertIs(all_calculators["mo_nslp"], MoNslp)

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

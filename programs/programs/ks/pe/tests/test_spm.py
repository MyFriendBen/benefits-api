"""
Unit tests for the KS SPM-level PolicyEngine calculator ``KsTanf`` (ks_tanf).

KsTanf is a straight passthrough to PolicyEngine's KS-specific ``ks_tanf`` calculator:
eligibility and the benefit dollar value come from PE, so there is no MFB-side routing
to unit-test the way KS Medicaid has. What *does* live on the MFB side is the set of
``pe_inputs`` that feed the household's real circumstances into PE. Four inputs beyond
the state code are load-bearing:

  - ``KsCountyDependency``                    — county tier (KEESM T-2); absent → Group I statewide
  - ``Ssi``                                   — SSI assistance-unit exclusion (KEESM 2210)
  - ``ChildCareDependency``                   — childcare deduction (K.A.R. 30-4-111(b))
  - ``PreSubsidyChildcareExpensesDependency`` — dependent-care deduction (KEESM 7224)

These tests pin the wiring so a future refactor can't silently drop one again.
"""

from django.test import TestCase

from programs.programs.ks.pe import ks_spm_calculators, ks_pe_calculators
from programs.programs.ks.pe.spm import KsTanf
from programs.programs.federal.pe.spm import Tanf
import programs.programs.policyengine.calculators.dependencies as dependency


class TestKsTanfWiring(TestCase):
    """KsTanf registration and KS-specific pe_inputs handling."""

    def test_is_subclass_of_tanf(self):
        self.assertTrue(issubclass(KsTanf, Tanf))

    def test_pe_name_is_ks_tanf(self):
        self.assertEqual(KsTanf.pe_name, "ks_tanf")

    def test_is_registered_in_ks_spm_calculators(self):
        self.assertIn("ks_tanf", ks_spm_calculators)
        self.assertEqual(ks_spm_calculators["ks_tanf"], KsTanf)

    def test_is_registered_in_ks_pe_calculators(self):
        self.assertIn("ks_tanf", ks_pe_calculators)
        self.assertEqual(ks_pe_calculators["ks_tanf"], KsTanf)

    def test_pe_output_is_ks_tanf(self):
        self.assertEqual(KsTanf.pe_outputs, [dependency.spm.KsTanf])

    # --- the four load-bearing inputs (discovery regression guard) ---

    def test_pe_inputs_includes_county(self):
        self.assertIn(dependency.household.KsCountyDependency, KsTanf.pe_inputs)

    def test_pe_inputs_includes_ssi(self):
        self.assertIn(dependency.member.Ssi, KsTanf.pe_inputs)

    def test_pe_inputs_includes_childcare(self):
        self.assertIn(dependency.spm.ChildCareDependency, KsTanf.pe_inputs)

    def test_pe_inputs_includes_pre_subsidy_childcare(self):
        self.assertIn(dependency.spm.PreSubsidyChildcareExpensesDependency, KsTanf.pe_inputs)

    # --- the remaining KS-specific inputs ---

    def test_pe_inputs_includes_ks_state_code(self):
        self.assertIn(dependency.household.KsStateCodeDependency, KsTanf.pe_inputs)

    def test_pe_inputs_includes_pregnancy(self):
        self.assertIn(dependency.member.PregnancyDependency, KsTanf.pe_inputs)

    def test_pe_inputs_includes_cash_assets(self):
        self.assertIn(dependency.spm.CashAssetsDependency, KsTanf.pe_inputs)

    def test_pe_inputs_includes_gross_income_streams(self):
        for income_dep in dependency.irs_gross_income:
            self.assertIn(income_dep, KsTanf.pe_inputs)

    def test_pe_inputs_keeps_inherited_demographic_inputs(self):
        for inherited in Tanf.pe_inputs:
            self.assertIn(inherited, KsTanf.pe_inputs)

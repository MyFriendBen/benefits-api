"""KS tests."""

from programs.programs.cross_white_label.tanf.ks import KsTanf
from programs.programs.cross_white_label.tanf.base import Tanf
from django.test import TestCase
import programs.framework.pe_dependencies as dependency


class TestKsTanfWiring(TestCase):
    """KsTanf registration and KS-specific pe_inputs handling."""

    def test_is_subclass_of_tanf(self):
        self.assertTrue(issubclass(KsTanf, Tanf))

    def test_pe_name_is_ks_tanf(self):
        self.assertEqual(KsTanf.pe_name, "ks_tanf")

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

    def test_pe_inputs_includes_ssi_aware_cash_assets(self):
        """KEESM 2210 excludes an SSI recipient's resources, and their share of the single
        reported household total cannot be isolated, so no countable figure is reported for
        such a household."""
        self.assertIn(dependency.spm.CashAssetsExcludingSsiHouseholdsDependency, KsTanf.pe_inputs)

    def test_does_not_send_the_plain_aggregate(self):
        """Both write spm_unit_cash_assets; the SSI-aware one must win."""
        self.assertNotIn(dependency.spm.CashAssetsDependency, KsTanf.pe_inputs)

    def test_pe_inputs_includes_gross_income_streams(self):
        for income_dep in dependency.irs_gross_income:
            self.assertIn(income_dep, KsTanf.pe_inputs)

    def test_pe_inputs_keeps_inherited_demographic_inputs(self):
        for inherited in Tanf.pe_inputs:
            self.assertIn(inherited, KsTanf.pe_inputs)

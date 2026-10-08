"""MO tests."""

from django.test import TestCase

import programs.framework.pe_dependencies as dependency
from programs.programs.cross_white_label.tanf.mo import MoTanf


class TestMoTanfWiring(TestCase):
    """MoTanf registration and MO-specific pe_inputs handling."""

    def test_pe_name_is_mo_tanf(self):
        self.assertEqual(MoTanf.pe_name, "mo_tanf")

    def test_pe_output_is_mo_tanf(self):
        self.assertEqual(MoTanf.pe_outputs, [dependency.spm.MoTanf])

    # --- the resource test ---

    def test_pe_inputs_includes_cash_assets(self):
        """The resource test (mo_tanf_resources_eligible) reads the reported assets."""
        self.assertIn(dependency.spm.CashAssetsDependency, MoTanf.pe_inputs)

    # --- the care-cost deduction (13 CSR 40-2.310(9)(A)5) ---

    def test_pe_inputs_includes_childcare(self):
        self.assertIn(dependency.spm.ChildCareDependency, MoTanf.pe_inputs)

    def test_pe_inputs_includes_care_expenses(self):
        """The incapacitated-adult tier reads person-level care_expenses."""
        self.assertIn(dependency.member.CareExpensesDependency, MoTanf.pe_inputs)

    def test_pe_inputs_includes_incapable_of_self_care(self):
        """The $175 incapacitated-person tier is gated on is_incapable_of_self_care."""
        self.assertIn(dependency.member.IsIncapableOfSelfCareDependency, MoTanf.pe_inputs)

    # --- income ---

    def test_pe_inputs_uses_the_tanf_income_group(self):
        """Not irs_gross_income alone: that is the taxable contract and omits child support,
        which TANF counts."""
        for income_dep in dependency.tanf_income:
            self.assertIn(income_dep, MoTanf.pe_inputs)

    def test_pe_inputs_includes_child_support(self):
        self.assertIn(dependency.member.ChildSupportReceivedDependency, MoTanf.pe_inputs)

    def test_pe_inputs_includes_pregnancy(self):
        self.assertIn(dependency.member.PregnancyDependency, MoTanf.pe_inputs)

    # --- the active/not-active disregard branch ---

    def test_pe_inputs_have_no_duplicates(self):
        self.assertEqual(len(MoTanf.pe_inputs), len(set(MoTanf.pe_inputs)))

    def test_pe_inputs_includes_tax_unit_dependent(self):
        """PE's own inference is wrong at both 18 and 19; see MoTanf."""
        self.assertIn(dependency.member.TaxUnitDependentDependency, MoTanf.pe_inputs)

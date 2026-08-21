"""MO tests."""

from django.test import TestCase

import programs.framework.pe_dependencies as dependency
from programs.programs.cross_white_label.tanf.base import Tanf
from programs.programs.cross_white_label.tanf.mo import MoTanf


class TestMoTanfWiring(TestCase):
    """MoTanf registration and MO-specific pe_inputs handling."""

    def test_is_subclass_of_tanf(self):
        self.assertTrue(issubclass(MoTanf, Tanf))

    def test_pe_name_is_mo_tanf(self):
        self.assertEqual(MoTanf.pe_name, "mo_tanf")

    def test_pe_output_is_mo_tanf(self):
        self.assertEqual(MoTanf.pe_outputs, [dependency.spm.MoTanf])

    def test_pe_inputs_includes_mo_state_code(self):
        """pe_input() never sends state_code on its own."""
        self.assertIn(dependency.household.MoStateCodeDependency, MoTanf.pe_inputs)

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

    def test_keeps_receipt_contract_for_the_disregard_branch(self):
        """is_tanf_enrolled defaults to receives_tanf, which selects the disregard sequence."""
        for receipt_dep in dependency.receipt_contract:
            self.assertIn(receipt_dep, MoTanf.pe_inputs)

    def test_pe_inputs_keeps_inherited_demographic_inputs(self):
        for inherited in Tanf.pe_inputs:
            self.assertIn(inherited, MoTanf.pe_inputs)

    def test_pe_inputs_have_no_duplicates(self):
        self.assertEqual(len(MoTanf.pe_inputs), len(set(MoTanf.pe_inputs)))

    def test_pe_inputs_includes_tax_unit_dependent(self):
        """PE's own inference is wrong at both 18 and 19; see MoTanf."""
        self.assertIn(dependency.member.TaxUnitDependentDependency, MoTanf.pe_inputs)

    def test_pe_inputs_includes_in_secondary_school(self):
        """Without it an 18-year-old child and their caretaker both leave the unit."""
        self.assertIn(dependency.member.InSecondarySchoolDependency, MoTanf.pe_inputs)

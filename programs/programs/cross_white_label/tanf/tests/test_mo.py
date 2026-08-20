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
        """Every mo_tanf variable is defined_for StateCode.MO, and pe_input() never sends
        state_code on its own."""
        self.assertIn(dependency.household.MoStateCodeDependency, MoTanf.pe_inputs)

    # --- the resource test ---

    def test_sends_assets_per_member_not_as_spm_aggregate(self):
        """PE's SSI-resource exclusion (mo_tanf_countable_resources) subtracts each SSI
        recipient's *person-level* asset components from the unit total. A household that
        sends only the spm_unit_cash_assets aggregate gives it nothing to subtract, so the
        exclusion silently never applies."""
        self.assertIn(dependency.member.NonSsiBankAccountAssetsDependency, MoTanf.pe_inputs)

    def test_does_not_also_send_the_cash_assets_aggregate(self):
        """The two write different halves of the same PolicyEngine total; sending both
        would count the household's assets twice."""
        self.assertNotIn(dependency.spm.CashAssetsDependency, MoTanf.pe_inputs)

    # --- the care-cost deduction (13 CSR 40-2.310(9)(A)5) ---

    def test_pe_inputs_includes_childcare(self):
        self.assertIn(dependency.spm.ChildCareDependency, MoTanf.pe_inputs)

    def test_pe_inputs_includes_care_expenses(self):
        """mo_tanf_child_care_deduction reads person-level care_expenses for the
        incapacitated-adult tier, separately from childcare_expenses."""
        self.assertIn(dependency.member.CareExpensesDependency, MoTanf.pe_inputs)

    def test_pe_inputs_includes_incapable_of_self_care(self):
        """The $175 incapacitated-person tier is gated on is_incapable_of_self_care."""
        self.assertIn(dependency.member.IsIncapableOfSelfCareDependency, MoTanf.pe_inputs)

    # --- income ---

    def test_pe_inputs_includes_gross_income_streams(self):
        """Sent per person, not pre-aggregated: PE runs each earner's disregard sequence
        separately (DSS Manual 0210.015.30.10) and applies the student-child and
        teen-parent exclusions to the right member's earnings."""
        for income_dep in dependency.irs_gross_income:
            self.assertIn(income_dep, MoTanf.pe_inputs)

    def test_pe_inputs_includes_pregnancy(self):
        self.assertIn(dependency.member.PregnancyDependency, MoTanf.pe_inputs)

    # --- the active/not-active disregard branch ---

    def test_keeps_receipt_contract_for_the_disregard_branch(self):
        """PE picks the earned-income disregard sequence off is_tanf_enrolled, which
        defaults to receives_tanf. Without the receipt contract every household would be
        treated as a new applicant."""
        for receipt_dep in dependency.receipt_contract:
            self.assertIn(receipt_dep, MoTanf.pe_inputs)

    def test_pe_inputs_keeps_inherited_demographic_inputs(self):
        for inherited in Tanf.pe_inputs:
            self.assertIn(inherited, MoTanf.pe_inputs)

    def test_pe_inputs_have_no_duplicates(self):
        self.assertEqual(len(MoTanf.pe_inputs), len(set(MoTanf.pe_inputs)))

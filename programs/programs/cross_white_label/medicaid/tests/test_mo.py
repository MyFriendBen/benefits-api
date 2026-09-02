"""MO Medicaid tests."""

from django.test import TestCase

from programs.framework.pe_dependencies.household import MoStateCodeDependency
from programs.framework.pe_dependencies.member import (
    IsBlindDependency,
    MeetsSsiDisabilityCriteriaDependency,
)
from programs.programs.cross_white_label.medicaid.base import Medicaid
from programs.programs.cross_white_label.medicaid.mo import MoHealthNet


class TestMoHealthNet(TestCase):
    """Tests for MoHealthNet calculator class wiring."""

    def test_is_subclass_of_medicaid(self):
        """MoHealthNet extends the federal Medicaid calculator."""
        self.assertTrue(issubclass(MoHealthNet, Medicaid))

    def test_program_code(self):
        """program_code matches the Program row the config imports."""
        self.assertEqual(MoHealthNet.program_code, "mo_medicaid")

    def test_pe_name_is_medicaid(self):
        """Eligibility comes from PolicyEngine's federal medicaid variable."""
        self.assertEqual(MoHealthNet.pe_name, "medicaid")

    def test_pe_inputs_includes_mo_state_code(self):
        """MO state code is added on top of the federal Medicaid inputs."""
        self.assertIn(MoStateCodeDependency, MoHealthNet.pe_inputs)

    def test_pe_inputs_includes_all_parent_inputs(self):
        """All federal Medicaid inputs flow through unchanged."""
        for parent_input in Medicaid.pe_inputs:
            self.assertIn(parent_input, MoHealthNet.pe_inputs)

    def test_pe_inputs_adds_only_state_code_and_disability_inputs(self):
        """Exactly three inputs are added, all of them wiring rather than logic.

        Pinning the count is what keeps this a wiring-only subclass: a new input here should be
        a deliberate change with a reason, not something that accumulates.
        """
        added = [dep for dep in MoHealthNet.pe_inputs if dep not in Medicaid.pe_inputs]

        self.assertEqual(
            set(added),
            {
                MeetsSsiDisabilityCriteriaDependency,
                IsBlindDependency,
                MoStateCodeDependency,
            },
        )

    def test_sends_ssi_disability_inputs_for_the_abd_pathway(self):
        """MO declares the disability inputs instead of relying on mo_ssi to supply them.

        PolicyEngine pools inputs per request, so a request without mo_ssi would resolve
        is_optional_senior_or_disabled_for_medicaid to False and return $0 for a disabled
        applicant who should qualify through MHABD.
        """
        self.assertIn(MeetsSsiDisabilityCriteriaDependency, MoHealthNet.pe_inputs)
        self.assertIn(IsBlindDependency, MoHealthNet.pe_inputs)

    def test_pe_outputs_inherited_from_medicaid(self):
        """pe_outputs are unchanged from the federal parent."""
        self.assertEqual(MoHealthNet.pe_outputs, Medicaid.pe_outputs)

    def test_does_not_override_member_value(self):
        """MO adds no eligibility or value logic of its own.

        MO HealthNet is a wiring-only PolicyEngine subclass: PolicyEngine stays the single
        source of both the eligibility decision and the category. Overriding member_value
        here would reintroduce the hybrid shape (a state gate or dollar figure decided in
        our code) that the known PE parameter divergences are being fixed upstream instead.
        """
        self.assertIs(MoHealthNet.member_value, Medicaid.member_value)

    def test_medicaid_categories_has_all_keys(self):
        """All standard Medicaid category keys are present."""
        expected_keys = {
            "NONE",
            "ADULT",
            "INFANT",
            "YOUNG_CHILD",
            "OLDER_CHILD",
            "PREGNANT",
            "YOUNG_ADULT",
            "PARENT",
            "SSI_RECIPIENT",
            "AGED",
            "DISABLED",
        }
        self.assertEqual(set(MoHealthNet.medicaid_categories.keys()), expected_keys)

    def test_medicaid_categories_are_kff_monthly_figures(self):
        """Category values are the KFF 2023 MO per-full-benefit-enrollee figures, monthly.

        KFF publishes five mutually exclusive groups; all five are represented, including
        the expansion-adult rate that PE's ADULT category maps to in an expansion state.
        """
        cats = MoHealthNet.medicaid_categories

        self.assertEqual(cats["NONE"], 0)
        self.assertEqual(cats["ADULT"], MoHealthNet.KFF_EXPANSION_ADULTS / 12)
        for adult_category in ("YOUNG_ADULT", "PARENT", "PREGNANT"):
            self.assertEqual(cats[adult_category], MoHealthNet.KFF_ADULTS / 12)
        for child_category in ("INFANT", "YOUNG_CHILD", "OLDER_CHILD"):
            self.assertEqual(cats[child_category], MoHealthNet.KFF_CHILDREN / 12)
        self.assertEqual(cats["AGED"], MoHealthNet.KFF_SENIORS / 12)
        self.assertEqual(cats["DISABLED"], MoHealthNet.KFF_DISABLED / 12)
        self.assertEqual(cats["SSI_RECIPIENT"], cats["DISABLED"])

    def test_kff_annual_figures_are_the_published_values(self):
        """The annual KFF figures are the source of truth, not the derived monthly rates."""
        self.assertEqual(MoHealthNet.KFF_CHILDREN, 4_576)
        self.assertEqual(MoHealthNet.KFF_ADULTS, 6_379)
        self.assertEqual(MoHealthNet.KFF_EXPANSION_ADULTS, 7_445)
        self.assertEqual(MoHealthNet.KFF_SENIORS, 21_857)
        self.assertEqual(MoHealthNet.KFF_DISABLED, 30_410)

    def test_every_category_annualizes_to_a_published_kff_figure(self):
        """member_value multiplies by 12, so each rate must restore its KFF annual figure exactly.

        A rounded whole-dollar monthly rate would report a value a few dollars away from
        KFF's published number, which is what this catches if one creeps back in.
        """
        published = {
            0,
            MoHealthNet.KFF_CHILDREN,
            MoHealthNet.KFF_ADULTS,
            MoHealthNet.KFF_EXPANSION_ADULTS,
            MoHealthNet.KFF_SENIORS,
            MoHealthNet.KFF_DISABLED,
        }

        for category, monthly in MoHealthNet.medicaid_categories.items():
            annual = monthly * 12
            self.assertEqual(annual, int(annual), f"{category} does not annualize to a whole dollar")
            self.assertIn(int(annual), published, f"{category} annualizes to an unpublished value")

    def test_expansion_and_mandatory_adult_rates_differ(self):
        """A parent found through MHF must be distinguishable from one found through expansion.

        Missouri's mandatory categories (MHF, MPW) take precedence over adult expansion and
        carry KFF's non-expansion Adults rate, so collapsing them onto one adult rate would
        make categorical precedence unobservable in the result.
        """
        cats = MoHealthNet.medicaid_categories

        self.assertNotEqual(cats["ADULT"], cats["PARENT"])
        self.assertGreater(cats["ADULT"], cats["PARENT"])

    def test_aged_min_age_inherited(self):
        """MO uses the federal 65+ cutoff for the aged pathway."""
        self.assertEqual(MoHealthNet.aged_min_age, 65)

    def test_registered_with_policyengine_registry(self):
        """The calculator is discovered by program_code, so the Program row resolves to it."""
        from integrations.clients.policyengine.registry import all_calculators

        self.assertIs(all_calculators["mo_medicaid"], MoHealthNet)

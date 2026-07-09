"""
Unit tests for the KS member-level PolicyEngine calculators (KsKanCare / KS Medicaid,
KsChip / KS CHIP, and KsMsp / KS Medicare Savings Program).

KsKanCare coverage is two layers:

1. **Wiring** — KsKanCare subclasses the federal ``Medicaid`` calculator, is registered
   as ``ks_medicaid``, and carries the KS-specific ``pe_inputs`` handling from the spec's
   Implementation Notes 1–2:
     - the federal ``SsiCountableResourcesDependency`` is sent (ABD asset test screened),
     - ``MeetsSsiDisabilityCriteriaDependency`` + ``IsBlindDependency`` are added (disability /
       blindness mapping), and ``KsStateCodeDependency`` selects KS parameters.

2. **Scenario coverage** — one test per scenario in the ``## Test Scenarios`` section of
   ``programs/programs/ks/medicaid/spec.md``. Because these unit tests run without the live
   PolicyEngine API, PolicyEngine's determination for each scenario is mocked
   (``get_member_variable`` = the ``medicaid`` variable; ``get_member_dependency_value`` =
   ``MedicaidCategory`` / ``is_optional_senior_or_disabled_for_medicaid``) exactly as the spec
   documents PE returning for that household. The assertion is on the KS calculator's MFB-side
   output: the per-member dollar value and the value-tier routing (MAGI $3,648 / AGED $20,508 /
   DISABLED $32,460, and DISABLED-over-AGED priority). The FPL/FBR threshold math itself lives in
   PolicyEngine and is verified end-to-end by the spec's PolicyEngine run.

Scenarios 12 (already-enrolled suppression) and 13 (no-separate-unborn-enrollee) are MFB
display-layer / household-construction rules with no calculator logic, so they are not unit-tested
here — see the spec's Implementation Notes.
"""

from unittest.mock import Mock, MagicMock

from django.test import TestCase

from programs.programs.federal.pe.member import Medicaid
from programs.programs.policyengine.calculators.base import PolicyEngineMembersCalculator
from programs.programs.policyengine.calculators.dependencies import member as member_deps
from programs.programs.policyengine.calculators.dependencies.household import KsStateCodeDependency
from programs.programs.policyengine.calculators.dependencies.member import (
    AgeDependency,
    PregnancyDependency,
    Chip,
)
from programs.programs.policyengine.calculators.dependencies.tax import KsChipPremium
from programs.programs.ks.pe import ks_member_calculators, ks_pe_calculators
from programs.programs.ks.pe.member import KsKanCare, KsChip, KsMsp

# Annual value tiers (medicaid_categories * 12)
MAGI = 3_648  # INFANT / YOUNG_CHILD / OLDER_CHILD / PREGNANT / PARENT / ADULT / YOUNG_ADULT
AGED = 20_508
DISABLED = 32_460


class TestKsKanCareWiring(TestCase):
    """KsKanCare registration and KS-specific pe_inputs handling."""

    def test_is_subclass_of_medicaid(self):
        self.assertTrue(issubclass(KsKanCare, Medicaid))

    def test_is_registered_in_ks_member_calculators(self):
        self.assertIn("ks_medicaid", ks_member_calculators)
        self.assertEqual(ks_member_calculators["ks_medicaid"], KsKanCare)

    def test_is_registered_in_ks_pe_calculators(self):
        self.assertIn("ks_medicaid", ks_pe_calculators)
        self.assertEqual(ks_pe_calculators["ks_medicaid"], KsKanCare)

    def test_pe_name_is_medicaid(self):
        self.assertEqual(KsKanCare.pe_name, "medicaid")

    def test_pe_inputs_includes_ks_state_code(self):
        self.assertIn(KsStateCodeDependency, KsKanCare.pe_inputs)

    def test_pe_inputs_sends_ssi_countable_resources(self):
        """Implementation Note 2: the ABD asset test is screened."""
        self.assertIn(member_deps.SsiCountableResourcesDependency, KsKanCare.pe_inputs)

    def test_pe_inputs_adds_meets_ssi_disability_criteria(self):
        """Implementation Note 1: map disability/SSDI signals to meets_ssi_disability_criteria."""
        self.assertIn(member_deps.MeetsSsiDisabilityCriteriaDependency, KsKanCare.pe_inputs)

    def test_pe_inputs_adds_is_blind(self):
        """Implementation Note 1: map visually_impaired to is_blind (SGA-exempt)."""
        self.assertIn(member_deps.IsBlindDependency, KsKanCare.pe_inputs)

    def test_pe_inputs_keeps_core_inputs(self):
        for dep in (
            member_deps.AgeDependency,
            member_deps.PregnancyDependency,
            member_deps.IsDisabledDependency,
        ):
            self.assertIn(dep, KsKanCare.pe_inputs)

    def test_pe_outputs_inherited_from_medicaid(self):
        self.assertEqual(KsKanCare.pe_outputs, Medicaid.pe_outputs)

    def test_ks_state_code_dependency_configured(self):
        self.assertEqual(KsStateCodeDependency.state, "KS")
        self.assertEqual(KsStateCodeDependency.field, "state_code")

    def test_medicaid_categories_has_all_keys(self):
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
        self.assertEqual(set(KsKanCare.medicaid_categories.keys()), expected_keys)

    def test_magi_categories_are_monthly_304(self):
        cats = KsKanCare.medicaid_categories
        for key in ("ADULT", "INFANT", "YOUNG_CHILD", "OLDER_CHILD", "PREGNANT", "YOUNG_ADULT", "PARENT"):
            self.assertEqual(cats[key], 304, key)

    def test_aged_and_disabled_monthly_values(self):
        cats = KsKanCare.medicaid_categories
        self.assertEqual(cats["AGED"], 1_709)
        self.assertEqual(cats["DISABLED"], 2_705)
        self.assertEqual(cats["SSI_RECIPIENT"], 2_705)
        self.assertEqual(cats["NONE"], 0)


class TestKsKanCareScenarios(TestCase):
    """One test per ks_medicaid.json / spec Test Scenario (PE determination mocked)."""

    def _make_calculator(self):
        mock_screen = Mock()
        calc = KsKanCare(mock_screen, Mock(), Mock())
        calc._sim = MagicMock()
        calc.screen = mock_screen
        return calc

    def _make_member(self, age=35, is_disabled=False, member_id=1):
        m = Mock()
        m.id = member_id
        m.calc_age = Mock(return_value=age)
        m.has_disability = Mock(return_value=is_disabled)
        return m

    def _magi_eligible(self, calc, category):
        """PE finds the member MAGI-eligible in ``category`` (non-senior, non-disabled path)."""
        calc.get_member_variable = Mock(return_value=1)
        calc.get_member_dependency_value = Mock(return_value=category)

    def _magi_ineligible(self, calc):
        """PE returns the member ineligible on the MAGI path."""
        calc.get_member_variable = Mock(return_value=0)
        calc.get_member_dependency_value = Mock(return_value="NONE")

    def _abd(self, calc, qualifies):
        """PE's is_optional_senior_or_disabled_for_medicaid result for the ABD/senior path."""
        calc.get_member_dependency_value = Mock(return_value=qualifies)

    # --- Scenario 1 & 2: pregnant, low income / near boundary -> PREGNANT $3,648 ---
    def test_s1_pregnant_low_income_eligible(self):
        calc = self._make_calculator()
        self._magi_eligible(calc, "PREGNANT")
        self.assertEqual(calc.member_value(self._make_member(age=35)), MAGI)

    def test_s2_pregnant_near_boundary_eligible(self):
        calc = self._make_calculator()
        self._magi_eligible(calc, "PREGNANT")
        self.assertEqual(calc.member_value(self._make_member(age=29)), MAGI)

    # --- Scenario 3: parent + 2 children, all eligible ---
    def test_s3_parent_eligible(self):
        calc = self._make_calculator()
        self._magi_eligible(calc, "PARENT")
        self.assertEqual(calc.member_value(self._make_member(age=34)), MAGI)

    def test_s3_older_child_eligible(self):
        calc = self._make_calculator()
        self._magi_eligible(calc, "OLDER_CHILD")
        self.assertEqual(calc.member_value(self._make_member(age=8)), MAGI)

    def test_s3_young_child_eligible(self):
        calc = self._make_calculator()
        self._magi_eligible(calc, "YOUNG_CHILD")
        self.assertEqual(calc.member_value(self._make_member(age=5)), MAGI)

    # --- Scenario 4: parent over 38% ineligible, children eligible ---
    def test_s4_parent_over_limit_ineligible(self):
        calc = self._make_calculator()
        self._magi_ineligible(calc)
        self.assertEqual(calc.member_value(self._make_member(age=35)), 0)

    def test_s4_children_still_eligible(self):
        calc = self._make_calculator()
        self._magi_eligible(calc, "YOUNG_CHILD")
        self.assertEqual(calc.member_value(self._make_member(age=5)), MAGI)

    # --- Scenario 5 & 6: childless adults, no pathway ---
    def test_s5_single_childless_adult_ineligible(self):
        calc = self._make_calculator()
        self._magi_ineligible(calc)
        self.assertEqual(calc.member_value(self._make_member(age=45)), 0)

    def test_s6_childless_adult_age_64_ineligible(self):
        """Age 64 is not senior, so it stays on the MAGI path and PE returns ineligible."""
        calc = self._make_calculator()
        self._magi_ineligible(calc)
        self.assertEqual(calc.member_value(self._make_member(age=64)), 0)

    # --- Scenario 7: senior 65+, assets over limit -> AGED (asset test not screened) ---
    def test_s7_senior_assets_over_limit_eligible_aged(self):
        calc = self._make_calculator()
        self._abd(calc, True)
        self.assertEqual(calc.member_value(self._make_member(age=66, is_disabled=False)), AGED)

    # --- Scenario 8: disabled adult on SSDI -> DISABLED ---
    def test_s8_disabled_on_ssdi_eligible_disabled(self):
        calc = self._make_calculator()
        self._abd(calc, True)
        self.assertEqual(calc.member_value(self._make_member(age=50, is_disabled=True)), DISABLED)

    # --- Scenario 9: SSI recipient -> DISABLED ---
    def test_s9_ssi_recipient_eligible_disabled(self):
        calc = self._make_calculator()
        self._abd(calc, True)
        self.assertEqual(calc.member_value(self._make_member(age=40, is_disabled=True)), DISABLED)

    # --- Scenario 10: infant eligible, parents ineligible ---
    def test_s10_infant_eligible(self):
        calc = self._make_calculator()
        self._magi_eligible(calc, "INFANT")
        self.assertEqual(calc.member_value(self._make_member(age=0)), MAGI)

    def test_s10_parents_ineligible(self):
        calc = self._make_calculator()
        self._magi_ineligible(calc)
        self.assertEqual(calc.member_value(self._make_member(age=32)), 0)

    # --- Scenario 11: school-age child eligible, parent ineligible ---
    def test_s11_older_child_eligible(self):
        calc = self._make_calculator()
        self._magi_eligible(calc, "OLDER_CHILD")
        self.assertEqual(calc.member_value(self._make_member(age=11)), MAGI)

    def test_s11_parent_ineligible(self):
        calc = self._make_calculator()
        self._magi_ineligible(calc)
        self.assertEqual(calc.member_value(self._make_member(age=41)), 0)

    # --- Scenario 14: young adult age 20, childless -> ineligible ---
    def test_s14_young_adult_childless_ineligible(self):
        calc = self._make_calculator()
        self._magi_ineligible(calc)
        self.assertEqual(calc.member_value(self._make_member(age=20)), 0)

    # --- Scenario 15: disabled, earnings above SGA -> ABD fails, ineligible ---
    def test_s15_disabled_above_sga_ineligible(self):
        """SGA flips is_ssi_disabled off, so is_optional_senior_or_disabled_for_medicaid is False."""
        calc = self._make_calculator()
        self._abd(calc, False)
        self.assertEqual(calc.member_value(self._make_member(age=50, is_disabled=True)), 0)

    # --- Scenario 16: legally blind under 65 -> DISABLED (blindness = has_disability) ---
    def test_s16_blind_under_65_eligible_disabled(self):
        calc = self._make_calculator()
        self._abd(calc, True)
        self.assertEqual(calc.member_value(self._make_member(age=50, is_disabled=True)), DISABLED)

    # --- Scenario 17: long-term disability only -> DISABLED ---
    def test_s17_long_term_disability_eligible_disabled(self):
        calc = self._make_calculator()
        self._abd(calc, True)
        self.assertEqual(calc.member_value(self._make_member(age=56, is_disabled=True)), DISABLED)

    # --- Scenario 18: aged, income above SSI FBR -> ineligible ---
    def test_s18_aged_over_fbr_ineligible(self):
        calc = self._make_calculator()
        self._abd(calc, False)
        self.assertEqual(calc.member_value(self._make_member(age=68, is_disabled=False)), 0)

    # --- Scenario 19: aged AND disabled -> DISABLED value, not AGED ---
    def test_s19_aged_and_disabled_gets_disabled_value(self):
        calc = self._make_calculator()
        self._abd(calc, True)
        member = self._make_member(age=68, is_disabled=True)
        result = calc.member_value(member)
        self.assertEqual(result, DISABLED)
        self.assertNotEqual(result, AGED)

    # --- Scenario 20: pregnant above 171% FPL -> ineligible ---
    def test_s20_pregnant_over_limit_ineligible(self):
        calc = self._make_calculator()
        self._magi_ineligible(calc)
        self.assertEqual(calc.member_value(self._make_member(age=28)), 0)

    # --- Scenario 21: parent + young child, income above child limits -> both ineligible ---
    def test_s21_parent_ineligible(self):
        calc = self._make_calculator()
        self._magi_ineligible(calc)
        self.assertEqual(calc.member_value(self._make_member(age=34)), 0)

    def test_s21_young_child_ineligible(self):
        calc = self._make_calculator()
        self._magi_ineligible(calc)
        self.assertEqual(calc.member_value(self._make_member(age=4)), 0)

    # --- Scenario 22: parent + infant, above infant's own ceiling -> both ineligible ---
    def test_s22_infant_over_ceiling_ineligible(self):
        calc = self._make_calculator()
        self._magi_ineligible(calc)
        self.assertEqual(calc.member_value(self._make_member(age=0)), 0)

    # --- Scenario 23: parent + older child, above older child's ceiling -> both ineligible ---
    def test_s23_older_child_over_ceiling_ineligible(self):
        calc = self._make_calculator()
        self._magi_ineligible(calc)
        self.assertEqual(calc.member_value(self._make_member(age=11)), 0)


class TestKsChip(TestCase):
    """Tests for the KsChip calculator class."""

    def test_exists_and_is_subclass_of_policy_engine_members_calculator(self):
        """KsChip exists and follows the member-level calculator pattern."""
        self.assertTrue(issubclass(KsChip, PolicyEngineMembersCalculator))
        self.assertIsNotNone(KsChip.pe_inputs)
        self.assertGreater(len(KsChip.pe_inputs), 0)

    def test_is_registered_in_ks_pe_calculators(self):
        """KS CHIP is registered under the ks_chip name_abbreviated."""
        self.assertIn("ks_chip", ks_pe_calculators)
        self.assertEqual(ks_pe_calculators["ks_chip"], KsChip)

    def test_pe_name_is_chip(self):
        """KsChip reads PolicyEngine's federal `chip` output."""
        self.assertEqual(KsChip.pe_name, "chip")

    def test_pe_inputs_includes_age_dependency(self):
        """CHIP eligibility is age-gated (under 19)."""
        self.assertIn(AgeDependency, KsChip.pe_inputs)
        self.assertEqual(AgeDependency.field, "age")

    def test_pe_inputs_includes_pregnancy_dependency(self):
        """PregnancyDependency mirrors the federal Chip inputs."""
        self.assertIn(PregnancyDependency, KsChip.pe_inputs)
        self.assertEqual(PregnancyDependency.field, "is_pregnant")

    def test_pe_inputs_match_ks_medicaid_inputs(self):
        """CHIP gates on ~is_medicaid_eligible, and every program on a screen shares one
        PolicyEngine simulation, so CHIP must send the exact same KS Medicaid inputs as
        KsKanCare — otherwise the shared medicaid computation would be inconsistent."""
        self.assertEqual(KsChip.pe_inputs, KsKanCare.pe_inputs)

    def test_pe_inputs_includes_all_ks_medicaid_inputs(self):
        """CHIP reuses KsKanCare.pe_inputs verbatim, so it carries every KS Medicaid input."""
        for kancare_input in KsKanCare.pe_inputs:
            self.assertIn(kancare_input, KsChip.pe_inputs)

    def test_pe_inputs_includes_ssi_countable_resources(self):
        """Inherited via KsKanCare.pe_inputs; CHIP applies no resource test of its own."""
        self.assertIn(member_deps.SsiCountableResourcesDependency, KsChip.pe_inputs)

    def test_pe_inputs_includes_ks_state_code_dependency(self):
        """KsStateCodeDependency sets state_code=KS so PE applies the KS income limit (2.55)."""
        self.assertIn(KsStateCodeDependency, KsChip.pe_inputs)
        self.assertEqual(KsStateCodeDependency.state, "KS")
        self.assertEqual(KsStateCodeDependency.field, "state_code")

    def test_pe_outputs_includes_chip_dependency(self):
        """The per-child coverage value comes from PE's `chip` output."""
        self.assertIn(Chip, KsChip.pe_outputs)
        self.assertEqual(Chip.field, "chip")

    def test_pe_outputs_includes_ks_chip_premium_dependency(self):
        """KS additionally surfaces the tax-unit-level `ks_chip_premium`."""
        self.assertIn(KsChipPremium, KsChip.pe_outputs)
        self.assertEqual(KsChipPremium.field, "ks_chip_premium")
        self.assertEqual(KsChipPremium.unit, "tax_units")

    def test_member_value_returns_pe_value_when_member_has_no_insurance(self):
        """An uninsured child receives the full PE-calculated coverage value."""
        calculator = KsChip(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        pe_value = 1896
        calculator.get_member_variable = Mock(return_value=pe_value)

        member = Mock()
        member.id = 1
        member.has_insurance_types = Mock(return_value=True)

        result = calculator.member_value(member)

        self.assertEqual(result, pe_value)
        member.has_insurance_types.assert_called_once_with(("none",))

    def test_member_value_returns_zero_when_member_has_insurance(self):
        """A child with any other coverage is zeroed out (uninsured-only rule)."""
        calculator = KsChip(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        pe_value = 1896
        calculator.get_member_variable = Mock(return_value=pe_value)

        member = Mock()
        member.id = 1
        member.has_insurance_types = Mock(return_value=False)

        result = calculator.member_value(member)

        self.assertEqual(result, 0)
        member.has_insurance_types.assert_called_once_with(("none",))


class TestKsMspWiring(TestCase):
    """KsMsp registration and pe_inputs handling."""

    def test_is_registered_in_ks_member_calculators(self):
        self.assertIn("ks_medicare_savings", ks_member_calculators)
        self.assertEqual(ks_member_calculators["ks_medicare_savings"], KsMsp)

    def test_pe_name_is_msp(self):
        self.assertEqual(KsMsp.pe_name, "msp")

    def test_pe_inputs_includes_medicaid_inputs(self):
        """MSP needs *Medicaid.pe_inputs for the QI ~is_medicaid_eligible check and for the
        msp_asset_eligible resource test."""
        for medicaid_input in Medicaid.pe_inputs:
            self.assertIn(medicaid_input, KsMsp.pe_inputs)

    def test_pe_inputs_includes_ssi_countable_resources(self):
        """Without it, msp_asset_eligible sees $0 and an over-asset applicant wrongly qualifies."""
        self.assertIn(member_deps.SsiCountableResourcesDependency, KsMsp.pe_inputs)


class TestKsMspKanCareAssetConsistency(TestCase):
    """KanCare and MSP both read ssi_countable_resources in one shared simulation, so they must
    screen assets identically — sending it from one but not the other corrupts that program's
    eligibility. These assertions fail if the two ever diverge."""

    def test_kancare_and_msp_agree_on_ssi_countable_resources(self):
        kancare_sends = member_deps.SsiCountableResourcesDependency in KsKanCare.pe_inputs
        msp_sends = member_deps.SsiCountableResourcesDependency in KsMsp.pe_inputs
        self.assertEqual(kancare_sends, msp_sends)

    def test_both_send_ssi_countable_resources(self):
        self.assertIn(member_deps.SsiCountableResourcesDependency, KsKanCare.pe_inputs)
        self.assertIn(member_deps.SsiCountableResourcesDependency, KsMsp.pe_inputs)

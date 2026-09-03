"""KS Medicaid tests."""

from programs.programs.cross_white_label.medicaid.ks import KsKanCare
from programs.framework.pe_dependencies.household import KsStateCodeDependency
from unittest.mock import MagicMock
from programs.programs.cross_white_label.medicaid.base import Medicaid
from unittest.mock import Mock
from django.test import TestCase
from programs.framework.pe_dependencies import member as member_deps
from programs.framework.pe_dependencies import member

MAGI = 3_648
AGED = 20_508
DISABLED = 32_460


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

    def _pe(self, calc, medicaid=0, category="NONE", abd=False):
        """Stand in for PolicyEngine's answer about one member.

        Both variables have to be modelled, not just the one a scenario is about: ``medicaid``
        and ``medicaid_category`` are read together, and ``member_value`` consults the ABD flag
        only for the members the ordinary pathway does not price.
        """
        calc.get_member_variable = Mock(return_value=medicaid)

        def dependency_value(dependency, member_id):
            if dependency is member_deps.MedicaidSeniorOrDisabled:
                return abd
            if dependency is member_deps.MedicaidCategory:
                return category
            raise AssertionError(f"unexpected dependency read: {dependency}")

        calc.get_member_dependency_value = Mock(side_effect=dependency_value)

    def _magi_eligible(self, calc, category):
        """PE finds the member MAGI-eligible in ``category`` (non-senior, non-disabled path)."""
        self._pe(calc, medicaid=1, category=category)

    def _magi_ineligible(self, calc):
        """PE returns the member ineligible on the MAGI path."""
        self._pe(calc, medicaid=0, category="NONE")

    def _abd(self, calc, qualifies):
        """PE finds the member eligible on the ABD pathway, or not.

        specs/ks.md records that PE returns ``SSI_RECIPIENT`` for every KS ABD scenario, so an
        ABD-eligible member is medicaid-eligible in PE's eyes too; an ineligible one is neither.
        ``SSI_RECIPIENT`` carries no aged/disabled distinction of its own, which is exactly why
        the value tier comes from the member's own age and disability flags.
        """
        if qualifies:
            self._pe(calc, medicaid=1, category="SSI_RECIPIENT", abd=True)
        else:
            self._pe(calc, medicaid=0, category="NONE", abd=False)

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

    # --- Scenario 7 / 7b: senior 65+ on the ABD pathway -> AGED value tier ---
    # The ABD asset gate itself lives in PolicyEngine (msp_asset_eligible /
    # is_optional_senior_or_disabled_asset_eligible), so it is verified end-to-end by the
    # spec's live-PE run, not here. This asserts only MFB's value routing: once PE finds a
    # non-disabled senior ABD-eligible, the value is the AGED tier.
    def test_s7_senior_abd_eligible_gets_aged_value(self):
        calc = self._make_calculator()
        self._abd(calc, True)
        self.assertEqual(calc.member_value(self._make_member(age=66, is_disabled=False)), AGED)

    def test_s7_senior_abd_ineligible_gets_zero(self):
        """When PE finds the senior ABD-ineligible (e.g. assets over the limit, Scenario 7),
        the value is $0."""
        calc = self._make_calculator()
        self._abd(calc, False)
        self.assertEqual(calc.member_value(self._make_member(age=66, is_disabled=False)), 0)

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


class TestKsKanCareWiring(TestCase):
    """KsKanCare registration and KS-specific pe_inputs handling."""

    def test_is_subclass_of_medicaid(self):
        self.assertTrue(issubclass(KsKanCare, Medicaid))

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

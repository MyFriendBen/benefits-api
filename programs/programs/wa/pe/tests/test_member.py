"""
Unit tests for WA member-level PolicyEngine calculator classes.

These tests verify WA-specific calculator wiring and custom eligibility logic:
- WaSsi calculator registration
- WaAppleHealthMedicaid registration, wiring, and member_value() overrides:
  - Foster care categorical Medicaid (42 U.S.C. § 1396a(a)(10)(A)(i)(I))
  - Medicare exclusion for ACA expansion (42 CFR § 435.119(b)(3))
  - Premium CHIP tier for uninsured children (WAC 182-505-0215)
- WA-specific pe_inputs (WaStateCodeDependency)
- Federal Ssi / Medicaid inputs are inherited

The eligibility math itself (FBR-minus-countable-income, the
$20 + $65 + 1/2 income exclusion stack, SGA cutoff, ISM (VTR/PMV) reductions,
and spousal/parental deeming) lives in PolicyEngine and is tested by
PolicyEngine's own test suite — not duplicated here. See
`programs/programs/wa/ssi/spec.md` for the 15 reference scenarios that the
end-to-end validation suite (`validations/.../wa_ssi.json`) exercises against
PolicyEngine via `python manage.py validate --program wa_ssi`.
"""

from unittest.mock import Mock, MagicMock

from django.test import TestCase

from programs.programs.federal.pe.member import Medicaid, Ssi
from programs.programs.policyengine.calculators.dependencies import (
    member as member_deps,
)
from programs.programs.policyengine.calculators.dependencies.household import (
    WaStateCodeDependency,
)
from programs.programs.wa.pe import wa_member_calculators, wa_pe_calculators
from programs.programs.wa.pe.member import WaAppleHealthMedicaid, WaSsi


class TestWaAppleHealthMedicaid(TestCase):
    """Tests for WaAppleHealthMedicaid calculator class wiring and member_value() overrides."""

    # ------------------------------------------------------------------
    # Wiring tests
    # ------------------------------------------------------------------

    def test_is_subclass_of_medicaid(self):
        """WaAppleHealthMedicaid extends the federal Medicaid calculator."""
        self.assertTrue(issubclass(WaAppleHealthMedicaid, Medicaid))

    def test_is_registered_in_wa_member_calculators(self):
        """Registered as `wa_apple_health_medicaid` in the WA member-level subset."""
        self.assertIn("wa_apple_health_medicaid", wa_member_calculators)
        self.assertEqual(wa_member_calculators["wa_apple_health_medicaid"], WaAppleHealthMedicaid)

    def test_is_registered_in_wa_pe_calculators(self):
        """Registered in the combined WA PE calculators dict."""
        self.assertIn("wa_apple_health_medicaid", wa_pe_calculators)
        self.assertEqual(wa_pe_calculators["wa_apple_health_medicaid"], WaAppleHealthMedicaid)

    def test_pe_inputs_includes_wa_state_code(self):
        """WA state code is added on top of the federal Medicaid inputs."""
        self.assertIn(WaStateCodeDependency, WaAppleHealthMedicaid.pe_inputs)

    def test_pe_inputs_includes_all_parent_inputs(self):
        """All federal Medicaid inputs flow through unchanged."""
        for parent_input in Medicaid.pe_inputs:
            self.assertIn(parent_input, WaAppleHealthMedicaid.pe_inputs)

    def test_pe_inputs_adds_exactly_one_input(self):
        """Only WaStateCodeDependency is added beyond the parent inputs."""
        self.assertEqual(len(WaAppleHealthMedicaid.pe_inputs), len(Medicaid.pe_inputs) + 1)

    def test_pe_outputs_inherited_from_medicaid(self):
        """pe_outputs are unchanged from the federal parent."""
        self.assertEqual(WaAppleHealthMedicaid.pe_outputs, Medicaid.pe_outputs)

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
        self.assertEqual(set(WaAppleHealthMedicaid.medicaid_categories.keys()), expected_keys)

    def test_medicaid_categories_values_are_monthly(self):
        """Spot-check that category values are the KFF 2023 monthly figures."""
        cats = WaAppleHealthMedicaid.medicaid_categories
        self.assertEqual(cats["ADULT"], 471)
        self.assertEqual(cats["OLDER_CHILD"], 233)
        self.assertEqual(cats["AGED"], 1921)
        self.assertEqual(cats["DISABLED"], 2627)
        self.assertEqual(cats["PREGNANT"], 445)
        self.assertEqual(cats["NONE"], 0)

    # ------------------------------------------------------------------
    # Helper: build a mock calculator
    # ------------------------------------------------------------------

    def _make_calculator(self, household_size=1, gross_income=0):
        """Return a WaAppleHealthMedicaid instance with mocked screen/program/sim."""
        mock_screen = Mock()
        mock_screen.household_size = household_size
        mock_screen.calc_gross_income = Mock(return_value=gross_income)
        calc = WaAppleHealthMedicaid(mock_screen, Mock(), Mock())
        calc._sim = MagicMock()
        calc.screen = mock_screen
        return calc

    def _make_member(
        self,
        age=35,
        relationship="headOfHousehold",
        has_medicare=False,
        has_none_insurance=False,
        is_disabled=False,
    ):
        """Return a mock HouseholdMember."""
        m = Mock()
        m.id = 1
        m.relationship = relationship
        m.calc_age = Mock(return_value=age)
        m.has_disability = Mock(return_value=is_disabled)

        def _has_insurance_types(types, strict=True):
            if types == ("medicare",):
                return has_medicare
            if types == ("none",):
                return has_none_insurance
            return False

        m.has_insurance_types = Mock(side_effect=_has_insurance_types)
        return m

    # ------------------------------------------------------------------
    # Foster care categorical tests
    # ------------------------------------------------------------------

    def test_foster_child_age_9_is_eligible_regardless_of_income(self):
        """Foster child ≤20 gets OLDER_CHILD bucket annual value, bypassing income test."""
        calc = self._make_calculator(household_size=2, gross_income=120_000)
        member = self._make_member(age=9, relationship="fosterChild")

        result = calc.member_value(member)

        expected = WaAppleHealthMedicaid.medicaid_categories["OLDER_CHILD"] * 12  # $2,796
        self.assertEqual(result, expected)

    def test_foster_child_age_20_is_eligible(self):
        """Age 20 is still within the ≤20 foster care categorical window."""
        calc = self._make_calculator()
        member = self._make_member(age=20, relationship="fosterChild")

        self.assertEqual(calc.member_value(member), 233 * 12)

    def test_foster_child_age_21_is_not_eligible(self):
        """Age 21 exceeds the categorical window — falls through to standard logic."""
        calc = self._make_calculator()
        member = self._make_member(age=21, relationship="fosterChild")
        calc.get_member_variable = Mock(return_value=0)
        calc.get_member_dependency_value = Mock(return_value=False)

        self.assertEqual(calc.member_value(member), 0)

    def test_non_foster_child_does_not_trigger_categorical(self):
        """A regular child relationship does not get categorical eligibility."""
        calc = self._make_calculator()
        member = self._make_member(age=9, relationship="child")
        calc.get_member_variable = Mock(return_value=0)
        calc.get_member_dependency_value = Mock(return_value=False)

        # Should fall through to standard PE (returns 0 since PE says ineligible)
        self.assertEqual(calc.member_value(member), 0)

    # ------------------------------------------------------------------
    # Medicare exclusion tests
    # ------------------------------------------------------------------

    def test_medicare_adult_under_65_not_disabled_returns_zero(self):
        """Medicare-entitled adult under 65 without disability is ineligible for expansion."""
        calc = self._make_calculator()
        member = self._make_member(age=55, has_medicare=True, is_disabled=False)

        result = calc.member_value(member)

        self.assertEqual(result, 0)

    def test_medicare_adult_65_plus_routes_to_abd_pathway(self):
        """Medicare-entitled adult 65+ should route to ABD and get AGED bucket if qualifying."""
        calc = self._make_calculator()
        member = self._make_member(age=70, has_medicare=True)
        calc.get_member_dependency_value = Mock(return_value=True)

        result = calc.member_value(member)

        expected = WaAppleHealthMedicaid.medicaid_categories["AGED"] * 12  # $23,052
        self.assertEqual(result, expected)
        calc.get_member_dependency_value.assert_called_once_with(member_deps.MedicaidSeniorOrDisabled, member.id)

    def test_medicare_adult_65_plus_abd_not_qualifying_returns_zero(self):
        """Medicare-entitled senior who fails ABD income test returns 0."""
        calc = self._make_calculator()
        member = self._make_member(age=70, has_medicare=True)
        calc.get_member_dependency_value = Mock(return_value=False)

        self.assertEqual(calc.member_value(member), 0)

    def test_medicare_adult_with_disability_routes_to_disabled_bucket(self):
        """Medicare-entitled disabled adult gets DISABLED bucket via ABD pathway."""
        calc = self._make_calculator()
        member = self._make_member(age=50, has_medicare=True, is_disabled=True)
        calc.get_member_dependency_value = Mock(return_value=True)

        result = calc.member_value(member)

        expected = WaAppleHealthMedicaid.medicaid_categories["DISABLED"] * 12  # $31,524
        self.assertEqual(result, expected)

    def test_medicare_disabled_not_qualifying_abd_returns_zero(self):
        """Medicare-entitled disabled adult who fails ABD returns 0."""
        calc = self._make_calculator()
        member = self._make_member(age=50, has_medicare=True, is_disabled=True)
        calc.get_member_dependency_value = Mock(return_value=False)

        self.assertEqual(calc.member_value(member), 0)

    # ------------------------------------------------------------------
    # Standard PE pathway tests
    # ------------------------------------------------------------------

    def test_standard_adult_delegates_to_parent(self):
        """Non-Medicare adult with qualifying income delegates to the parent Medicaid class."""
        calc = self._make_calculator()
        member = self._make_member(age=35)
        # Simulate parent returning the ADULT bucket
        calc.get_member_variable = Mock(return_value=1)
        calc.get_member_dependency_value = Mock(return_value="ADULT")

        result = calc.member_value(member)

        expected = WaAppleHealthMedicaid.medicaid_categories["ADULT"] * 12  # $5,652
        self.assertEqual(result, expected)

    def test_standard_adult_ineligible_via_pe_returns_zero(self):
        """Non-Medicare adult above 138% FPL with PE returning 0 gets 0."""
        calc = self._make_calculator()
        member = self._make_member(age=35)
        calc.get_member_variable = Mock(return_value=0)
        calc.get_member_dependency_value = Mock(return_value=False)

        self.assertEqual(calc.member_value(member), 0)

    # ------------------------------------------------------------------
    # Premium CHIP tier tests
    # ------------------------------------------------------------------

    def test_premium_chip_uninsured_child_in_range_is_eligible(self):
        """Uninsured child <19 with income between free and premium ceiling qualifies."""
        # HH3 at $72,000/yr — above free tier (~$58,738 at 215%) but below premium ceiling ($86,604 at 317%)
        calc = self._make_calculator(household_size=3, gross_income=72_000)
        member = self._make_member(age=7, relationship="child", has_none_insurance=True)
        # PE says ineligible (above free tier)
        calc.get_member_variable = Mock(return_value=0)
        calc.get_member_dependency_value = Mock(return_value=False)

        result = calc.member_value(member)

        expected = WaAppleHealthMedicaid.medicaid_categories["OLDER_CHILD"] * 12  # $2,796
        self.assertEqual(result, expected)

    def test_premium_chip_child_with_employer_insurance_returns_zero(self):
        """Child with employer insurance in premium income range is not eligible."""
        calc = self._make_calculator(household_size=3, gross_income=72_000)
        member = self._make_member(age=7, relationship="child", has_none_insurance=False)
        calc.get_member_variable = Mock(return_value=0)
        calc.get_member_dependency_value = Mock(return_value=False)

        self.assertEqual(calc.member_value(member), 0)

    def test_premium_chip_child_above_ceiling_returns_zero(self):
        """Uninsured child with income above the premium ceiling is not eligible."""
        # HH3 ceiling is $86,604 — income is $90,000
        calc = self._make_calculator(household_size=3, gross_income=90_000)
        member = self._make_member(age=7, relationship="child", has_none_insurance=True)
        calc.get_member_variable = Mock(return_value=0)
        calc.get_member_dependency_value = Mock(return_value=False)

        self.assertEqual(calc.member_value(member), 0)

    def test_premium_chip_adult_does_not_qualify(self):
        """Adults ≥19 do not enter the premium CHIP fallback."""
        calc = self._make_calculator(household_size=3, gross_income=72_000)
        member = self._make_member(age=19, relationship="headOfHousehold")
        calc.get_member_variable = Mock(return_value=0)
        calc.get_member_dependency_value = Mock(return_value=False)

        self.assertEqual(calc.member_value(member), 0)

    def test_premium_chip_child_at_ceiling_boundary_is_eligible(self):
        """Income exactly at the ceiling boundary qualifies (≤ ceiling)."""
        calc = self._make_calculator(household_size=3, gross_income=86_604)
        member = self._make_member(age=7, relationship="child", has_none_insurance=True)
        calc.get_member_variable = Mock(return_value=0)
        calc.get_member_dependency_value = Mock(return_value=False)

        expected = WaAppleHealthMedicaid.medicaid_categories["OLDER_CHILD"] * 12
        self.assertEqual(calc.member_value(member), expected)

    # ------------------------------------------------------------------
    # _premium_chip_ceiling() tests
    # ------------------------------------------------------------------

    def test_premium_chip_ceiling_hh3(self):
        """HH3 ceiling matches the hardcoded HCA 2026 value."""
        self.assertEqual(WaAppleHealthMedicaid._premium_chip_ceiling(3), 86_604)

    def test_premium_chip_ceiling_hh1(self):
        """HH1 ceiling matches the hardcoded HCA 2026 value."""
        self.assertEqual(WaAppleHealthMedicaid._premium_chip_ceiling(1), 50_591)

    def test_premium_chip_ceiling_hh8_extrapolated(self):
        """HH8 is extrapolated: HH7 base + 1 × additional-member increment."""
        expected = 158_627 + 18_006
        self.assertEqual(WaAppleHealthMedicaid._premium_chip_ceiling(8), expected)

    def test_premium_chip_ceiling_hh10_extrapolated(self):
        """HH10 is extrapolated: HH7 base + 3 × additional-member increment."""
        expected = 158_627 + (3 * 18_006)
        self.assertEqual(WaAppleHealthMedicaid._premium_chip_ceiling(10), expected)

    def test_premium_chip_ceiling_zero_returns_none(self):
        """Household size 0 returns None (invalid)."""
        self.assertIsNone(WaAppleHealthMedicaid._premium_chip_ceiling(0))

    def test_premium_chip_ceiling_negative_returns_none(self):
        """Negative household size returns None."""
        self.assertIsNone(WaAppleHealthMedicaid._premium_chip_ceiling(-1))


class TestWaSsi(TestCase):
    """Tests for WaSsi calculator class wiring."""

    def test_exists_and_is_subclass_of_ssi(self):
        """WaSsi extends the federal Ssi PolicyEngine calculator."""
        self.assertTrue(issubclass(WaSsi, Ssi))

    def test_pe_name_is_ssi(self):
        """pe_name is inherited from Ssi and resolves to PolicyEngine's `ssi` variable."""
        self.assertEqual(WaSsi.pe_name, "ssi")

    def test_is_registered_in_wa_pe_calculators(self):
        """WaSsi is registered in the WA PE calculators dictionary as `wa_ssi`."""
        self.assertIn("wa_ssi", wa_pe_calculators)
        self.assertEqual(wa_pe_calculators["wa_ssi"], WaSsi)

    def test_is_registered_in_wa_member_calculators(self):
        """WaSsi is registered in the WA member-level subset (not SPM/tax)."""
        self.assertIn("wa_ssi", wa_member_calculators)
        self.assertEqual(wa_member_calculators["wa_ssi"], WaSsi)

    def test_pe_inputs_includes_wa_state_code_dependency(self):
        """The WA state code is added on top of the federal Ssi inputs."""
        self.assertIn(WaStateCodeDependency, WaSsi.pe_inputs)

    def test_wa_state_code_dependency_is_configured_correctly(self):
        """Sanity-check the dependency itself."""
        self.assertEqual(WaStateCodeDependency.state, "WA")
        self.assertEqual(WaStateCodeDependency.field, "state_code")

    def test_pe_inputs_includes_all_parent_inputs(self):
        """All federal Ssi inputs flow through to WaSsi unchanged."""
        for parent_input in Ssi.pe_inputs:
            self.assertIn(parent_input, WaSsi.pe_inputs)

    def test_pe_inputs_has_more_than_parent(self):
        """WaSsi adds exactly one input on top of the parent (the WA state code)."""
        self.assertEqual(len(WaSsi.pe_inputs), len(Ssi.pe_inputs) + 1)

    def test_pe_outputs_inherited_from_ssi(self):
        """Output is the federal SSI dollar value (no override needed)."""
        self.assertEqual(WaSsi.pe_outputs, Ssi.pe_outputs)

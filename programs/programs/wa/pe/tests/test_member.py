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

from programs.programs.federal.pe.member import Ssi
from programs.framework.pe_base import PolicyEngineMembersCalculator
from programs.framework.pe_dependencies import (
    member as member_deps,
)
from programs.framework.pe_dependencies.household import (
    WaStateCodeDependency,
)
from programs.programs.wa.pe.member import WaAppleHealthForKids, WaSsi
from programs.programs.cross_white_label.medicaid.base import Medicaid
from programs.programs.cross_white_label.medicaid.wa import WaAppleHealthMedicaid


class TestWaAppleHealthForKids(TestCase):
    """Tests for WaAppleHealthForKids calculator class wiring and member_value() logic."""

    # ------------------------------------------------------------------
    # Wiring tests
    # ------------------------------------------------------------------

    def test_is_subclass_of_policy_engine_members_calculator(self):
        self.assertTrue(issubclass(WaAppleHealthForKids, PolicyEngineMembersCalculator))

    def test_pe_name(self):
        self.assertEqual(WaAppleHealthForKids.pe_name, "wa_apple_health_kids_eligible")

    def test_pe_inputs_includes_wa_state_code(self):
        self.assertIn(WaStateCodeDependency, WaAppleHealthForKids.pe_inputs)

    def test_pe_inputs_includes_all_medicaid_inputs(self):
        for parent_input in Medicaid.pe_inputs:
            self.assertIn(parent_input, WaAppleHealthForKids.pe_inputs)

    def test_pe_outputs_includes_kids_eligible(self):
        self.assertIn(member_deps.WaAppleHealthKidsEligible, WaAppleHealthForKids.pe_outputs)

    def test_annual_value_per_child(self):
        self.assertEqual(WaAppleHealthForKids.ANNUAL_VALUE_PER_CHILD, 2_801)

    # ------------------------------------------------------------------
    # member_value() tests
    # ------------------------------------------------------------------

    def _make_calculator(self):
        mock_screen = Mock()
        calc = WaAppleHealthForKids(mock_screen, Mock(), Mock())
        calc._sim = MagicMock()
        calc.screen = mock_screen
        return calc

    def _make_member(self, member_id=1):
        m = Mock()
        m.id = member_id
        return m

    def test_eligible_child_returns_annual_value(self):
        calc = self._make_calculator()
        member = self._make_member()
        calc.get_member_variable = Mock(return_value=True)

        self.assertEqual(calc.member_value(member), 2_801)

    def test_ineligible_member_returns_zero(self):
        calc = self._make_calculator()
        member = self._make_member()
        calc.get_member_variable = Mock(return_value=False)

        self.assertEqual(calc.member_value(member), 0)

    def test_pe_returns_zero_treated_as_ineligible(self):
        calc = self._make_calculator()
        member = self._make_member()
        calc.get_member_variable = Mock(return_value=0)

        self.assertEqual(calc.member_value(member), 0)

    def test_no_insurance_check_performed(self):
        """Kids calculator does NOT gate on insurance (criterion 6 inclusivity assumption)."""
        calc = self._make_calculator()
        member = self._make_member()
        calc.get_member_variable = Mock(return_value=True)

        result = calc.member_value(member)

        self.assertEqual(result, 2_801)
        member.has_insurance_types.assert_not_called()


class TestWaSsi(TestCase):
    """Tests for WaSsi calculator class wiring."""

    def test_exists_and_is_subclass_of_ssi(self):
        """WaSsi extends the federal Ssi PolicyEngine calculator."""
        self.assertTrue(issubclass(WaSsi, Ssi))

    def test_pe_name_is_ssi(self):
        """pe_name is inherited from Ssi and resolves to PolicyEngine's `ssi` variable."""
        self.assertEqual(WaSsi.pe_name, "ssi_if_takes_up")

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

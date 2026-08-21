"""WA tests."""

from unittest.mock import MagicMock
from programs.programs.cross_white_label.medicaid.base import Medicaid
from unittest.mock import Mock
from programs.framework.pe_base import PolicyEngineMembersCalculator
from django.test import TestCase
from programs.programs.cross_white_label.medicaid.chip.wa import WaAppleHealthForKids
from programs.framework.pe_dependencies.household import WaStateCodeDependency
from programs.framework.pe_dependencies import member as member_deps
from programs.framework.pe_dependencies import member


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

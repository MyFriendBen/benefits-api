from django.test import TestCase
from unittest.mock import Mock

from programs.programs.wa import wa_calculators
from programs.programs.wa.wap.calculator import WaWap
from programs.programs.calc import Eligibility, MemberEligibility


def make_member(insurance_medicaid: bool = False, insurance_chp: bool = False):
    member = Mock()
    member.age = 40

    def has_insurance(name: str):
        if name == "wa_apple_health_medicaid":
            return insurance_medicaid
        if name == "wa_apple_health_for_kids":
            return insurance_chp
        return False

    member.has_insurance = Mock(side_effect=has_insurance)
    return member


def make_calculator(
    yearly_income: int = 10_000,
    fpl_limit: int = 15_960,
    has_wa_snap: bool = False,
    has_wa_tanf: bool = False,
    has_wa_ssi: bool = False,
    has_wa_hcv: bool = False,
    members=None,
):
    mock_screen = Mock()
    mock_screen.calc_gross_income = Mock(return_value=yearly_income)
    mock_screen.household_members.all = Mock(return_value=members or [make_member()])

    def benefit_side_effect(name: str):
        return {
            "wa_snap": has_wa_snap,
            "wa_tanf": has_wa_tanf,
            "wa_ssi": has_wa_ssi,
            "wa_hcv": has_wa_hcv,
        }.get(name, False)

    mock_screen.has_benefit = Mock(side_effect=benefit_side_effect)

    mock_program = Mock()
    mock_program.year.get_limit = Mock(return_value=fpl_limit)

    mock_missing_deps = Mock()
    mock_missing_deps.has.return_value = False

    return WaWap(mock_screen, mock_program, {}, mock_missing_deps)


class TestWaWapClassAttributes(TestCase):
    def test_is_registered(self) -> None:
        self.assertIn("wa_wap", wa_calculators)
        self.assertEqual(wa_calculators["wa_wap"], WaWap)

    def test_fpl_percent(self) -> None:
        self.assertEqual(WaWap.fpl_percent, 2.0)

    def test_amount(self) -> None:
        self.assertEqual(WaWap.amount, 7_669)


class TestWaWapHouseholdEligibility(TestCase):
    # fpl_limit=15_960 → 200% FPL = 31_920

    def _run(self, yearly_income, **kwargs):
        calc = make_calculator(yearly_income=yearly_income, **kwargs)
        e = Eligibility()
        me = MemberEligibility(make_member())
        me.eligible = True
        e.add_member_eligibility(me)
        calc.household_eligible(e)
        return e.eligible

    # --- Income pathway ---

    def test_income_below_limit_eligible(self) -> None:
        self.assertTrue(self._run(20_000))

    def test_income_at_limit_eligible(self) -> None:
        # exactly at 200% FPL: 2.0 * 15_960 = 31_920
        self.assertTrue(self._run(31_920))

    def test_income_above_limit_ineligible(self) -> None:
        self.assertFalse(self._run(31_921))

    def test_income_well_above_limit_ineligible(self) -> None:
        self.assertFalse(self._run(80_000))

    def test_zero_income_eligible(self) -> None:
        self.assertTrue(self._run(0))

    # --- Categorical pathway: screen-level (Step 8 current benefits) ---

    def test_snap_bypasses_income(self) -> None:
        self.assertTrue(self._run(50_000, has_wa_snap=True))

    def test_tanf_bypasses_income(self) -> None:
        self.assertTrue(self._run(50_000, has_wa_tanf=True))

    def test_ssi_bypasses_income(self) -> None:
        self.assertTrue(self._run(50_000, has_wa_ssi=True))

    def test_hcv_bypasses_income(self) -> None:
        self.assertTrue(self._run(50_000, has_wa_hcv=True))

    def test_no_categorical_no_income_ineligible(self) -> None:
        self.assertFalse(self._run(40_000))

    # --- Categorical pathway: member-level insurance (Step 5) ---

    def test_apple_health_medicaid_bypasses_income(self) -> None:
        # Apple Health (adult Medicaid) selected on Step 5 triggers categorical eligibility
        members = [make_member(insurance_medicaid=True)]
        self.assertTrue(self._run(50_000, members=members))

    def test_apple_health_for_kids_bypasses_income(self) -> None:
        # Apple Health for Kids (CHIP) selected on Step 5 triggers categorical eligibility
        members = [make_member(insurance_chp=True)]
        self.assertTrue(self._run(50_000, members=members))

    def test_child_apple_health_for_kids_triggers_household_eligibility(self) -> None:
        # Any member with Apple Health for Kids qualifies the whole household
        members = [make_member(), make_member(insurance_chp=True)]
        self.assertTrue(self._run(50_000, members=members))

    def test_no_apple_health_high_income_ineligible(self) -> None:
        members = [make_member(insurance_medicaid=False, insurance_chp=False)]
        self.assertFalse(self._run(50_000, members=members))


class TestWaWapValue(TestCase):
    def test_eligible_household_value_7669(self) -> None:
        calc = make_calculator(yearly_income=10_000)
        result = calc.calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 7_669)

    def test_ineligible_household_value_0(self) -> None:
        calc = make_calculator(yearly_income=80_000)
        result = calc.calc()
        self.assertFalse(result.eligible)
        self.assertEqual(result.value, 0)

    def test_categorical_eligible_value_7669(self) -> None:
        calc = make_calculator(yearly_income=50_000, has_wa_snap=True)
        result = calc.calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 7_669)

    def test_multi_member_household_value_7669(self) -> None:
        # Household-level program: value is flat 7_669 regardless of member count
        members = [make_member(), make_member(), make_member()]
        calc = make_calculator(yearly_income=10_000, members=members)
        result = calc.calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 7_669)

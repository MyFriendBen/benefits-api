from django.test import TestCase
from unittest.mock import Mock

from programs.programs.wa import wa_calculators
from programs.programs.wa.wap.calculator import WaWap
from programs.programs.calc import Eligibility, MemberEligibility


def make_member():
    member = Mock()
    member.age = 40
    return member


def make_calculator(yearly_income=10_000, fpl_limit=15_960, has_snap=False, has_tanf=False, has_ssi=False,
                    has_section_8=False, has_medicaid=False, members=None):
    mock_screen = Mock()
    mock_screen.calc_gross_income = Mock(return_value=yearly_income)
    mock_screen.household_members.all = Mock(return_value=members or [make_member()])

    def benefit_side_effect(name):
        return {
            "snap": has_snap,
            "tanf": has_tanf,
            "ssi": has_ssi,
            "section_8": has_section_8,
            "medicaid": has_medicaid,
        }.get(name, False)

    mock_screen.has_benefit = Mock(side_effect=benefit_side_effect)

    mock_program = Mock()
    mock_program.year.get_limit = Mock(return_value=fpl_limit)

    mock_missing_deps = Mock()
    mock_missing_deps.has.return_value = False

    return WaWap(mock_screen, mock_program, {}, mock_missing_deps)


class TestWaWapClassAttributes(TestCase):
    def test_is_registered(self):
        self.assertIn("wa_wap", wa_calculators)
        self.assertEqual(wa_calculators["wa_wap"], WaWap)

    def test_fpl_percent(self):
        self.assertEqual(WaWap.fpl_percent, 2.0)

    def test_amount(self):
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

    def test_income_below_limit_eligible(self):
        self.assertTrue(self._run(20_000))

    def test_income_at_limit_eligible(self):
        # exactly at 200% FPL: 2.0 * 15_960 = 31_920
        self.assertTrue(self._run(31_920))

    def test_income_above_limit_ineligible(self):
        self.assertFalse(self._run(31_921))

    def test_income_well_above_limit_ineligible(self):
        self.assertFalse(self._run(80_000))

    def test_zero_income_eligible(self):
        self.assertTrue(self._run(0))

    def test_snap_bypasses_income(self):
        # income above FPL but SNAP → eligible
        self.assertTrue(self._run(50_000, has_snap=True))

    def test_tanf_bypasses_income(self):
        self.assertTrue(self._run(50_000, has_tanf=True))

    def test_ssi_bypasses_income(self):
        self.assertTrue(self._run(50_000, has_ssi=True))

    def test_section_8_bypasses_income(self):
        self.assertTrue(self._run(50_000, has_section_8=True))

    def test_medicaid_bypasses_income(self):
        self.assertTrue(self._run(50_000, has_medicaid=True))

    def test_no_categorical_no_income_ineligible(self):
        self.assertFalse(self._run(40_000))


class TestWaWapValue(TestCase):
    def test_eligible_household_value_7669(self):
        calc = make_calculator(yearly_income=10_000)
        result = calc.calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 7_669)

    def test_ineligible_household_value_0(self):
        calc = make_calculator(yearly_income=80_000)
        result = calc.calc()
        self.assertFalse(result.eligible)
        self.assertEqual(result.value, 0)

    def test_categorical_eligible_value_7669(self):
        calc = make_calculator(yearly_income=50_000, has_snap=True)
        result = calc.calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 7_669)

    def test_multi_member_household_value_7669(self):
        # Household-level program: value is flat 7_669 regardless of member count
        members = [make_member(), make_member(), make_member()]
        calc = make_calculator(yearly_income=10_000, members=members)
        result = calc.calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 7_669)

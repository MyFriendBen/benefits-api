"""
Unit tests for KsWorkingHealthy calculator — one test per spec.md Test Scenario.

Working Healthy eligibility (KEESM §2664):
- Age 16-64
- Qualifying disability (long_term_disability / visually_impaired)
- Currently employed, gross monthly earned income > $65
- Countable income <= 300% FPL (assistance-plan size), awd_medicaid disregards
- Countable resources <= $15,000 (flat)
- Insurance none/employer/private; not an SSI recipient
- KS residency handled by white-label routing (Scenario 17 not a calculator test)

Benefit value: $30,192/year per eligible member (KFF; see calculator note — value
method flagged for sign-off before activation).
"""

from django.test import TestCase
from unittest.mock import Mock

from programs.programs.ks import ks_calculators
from programs.programs.ks.working_healthy.calculator import KsWorkingHealthy
from programs.programs.calc import ProgramCalculator, Eligibility, MemberEligibility

VALUE_PER_MEMBER = 30_192

# 2026 FPL used in tests (single-person). 300% of this is the income ceiling.
FPL_1 = 15_960


def make_member(
    age=40,
    long_term_disability=True,
    visually_impaired=False,
    monthly_earned=1_800,
    monthly_unearned=0,
    monthly_ssi=0,
    insurance_types=("none",),
    married_to=None,
    relationship="headOfHousehold",
):
    member = Mock()
    member.age = age
    member.long_term_disability = long_term_disability
    member.visually_impaired = visually_impaired
    member.relationship = relationship

    def calc_income(period, types):
        factor = 1 if period == "monthly" else 12
        earned = monthly_earned * factor
        unearned = monthly_unearned * factor
        ssi = monthly_ssi * factor
        # SSI is unearned income: it's part of the "unearned" total and is also
        # queryable on its own via ["sSI"] (matches the real income model).
        if types == ["sSI"]:
            return ssi
        if types == ["earned"]:
            return earned
        if types == ["unearned"]:
            return unearned + ssi
        return earned + unearned + ssi

    member.calc_gross_income = Mock(side_effect=calc_income)
    member.insurance = Mock()
    member.insurance.has_insurance_types = Mock(side_effect=lambda types: any(t in insurance_types for t in types))
    member.is_married = Mock(return_value={"is_married": married_to is not None, "married_to": married_to})
    return member


def make_calculator(members=None, household_assets=5_000, fpl_limit=FPL_1, medicaid_eligible_data=False):
    if members is None:
        members = [make_member()]

    mock_program = Mock()
    mock_program.year.get_limit = Mock(return_value=fpl_limit)

    mock_screen = Mock()
    mock_screen.household_size = len(members)
    mock_screen.household_assets = household_assets
    mock_screen.household_members.all = Mock(return_value=members)

    data = {}
    if medicaid_eligible_data:
        med = Mock()
        med.eligible = True
        data["medicaid"] = med

    mock_missing_deps = Mock()
    mock_missing_deps.has.return_value = False

    return KsWorkingHealthy(mock_screen, mock_program, data, mock_missing_deps)


def run(calc):
    """Run full eligibility + value; return (eligible, total_value)."""
    e = calc.eligible()
    calc.value(e)
    return e.eligible, e.value


class TestClassAttributes(TestCase):
    def test_is_subclass(self):
        self.assertTrue(issubclass(KsWorkingHealthy, ProgramCalculator))

    def test_registered(self):
        self.assertIn("ks_working_healthy", ks_calculators)
        self.assertEqual(ks_calculators["ks_working_healthy"], KsWorkingHealthy)

    def test_constants(self):
        self.assertEqual(KsWorkingHealthy.min_age, 16)
        self.assertEqual(KsWorkingHealthy.max_age, 64)
        self.assertEqual(KsWorkingHealthy.max_income_percent, 3.0)
        self.assertEqual(KsWorkingHealthy.resource_limit, 15_000)
        self.assertEqual(KsWorkingHealthy.member_amount, VALUE_PER_MEMBER)


class TestSpecScenarios(TestCase):
    def test_scenario_1_clearly_eligible(self):
        calc = make_calculator([make_member(age=40, monthly_earned=1_800)], household_assets=5_000)
        eligible, value = run(calc)
        self.assertTrue(eligible)
        self.assertEqual(value, VALUE_PER_MEMBER)

    def test_scenario_2_minimally_eligible(self):
        calc = make_calculator([make_member(age=16, monthly_earned=200)], household_assets=500)
        eligible, value = run(calc)
        self.assertTrue(eligible)
        self.assertEqual(value, VALUE_PER_MEMBER)

    def test_scenario_3_not_working_ineligible(self):
        # SSDI (unearned) only, no earned income -> fails employment requirement
        calc = make_calculator([make_member(age=40, monthly_earned=0, monthly_unearned=1_200)])
        eligible, _ = run(calc)
        self.assertFalse(eligible)

    def test_scenario_4_not_disabled_ineligible(self):
        calc = make_calculator([make_member(age=40, long_term_disability=False, visually_impaired=False)])
        eligible, _ = run(calc)
        self.assertFalse(eligible)

    def test_scenario_5_income_just_under_limit_eligible(self):
        # $7,900/mo -> countable ($94,800-65)*0.5 = $47,368 < 300% FPL ($47,880)
        calc = make_calculator([make_member(age=44, monthly_earned=7_900)])
        eligible, value = run(calc)
        self.assertTrue(eligible)
        self.assertEqual(value, VALUE_PER_MEMBER)

    def test_scenario_6_income_over_limit_ineligible(self):
        # $8,500/mo -> countable ($102,000-65)*0.5 = $50,968 > $47,880
        calc = make_calculator([make_member(age=44, monthly_earned=8_500)])
        eligible, _ = run(calc)
        self.assertFalse(eligible)

    def test_scenario_7_resources_exactly_limit_eligible(self):
        calc = make_calculator([make_member(age=40, monthly_earned=1_800)], household_assets=15_000)
        eligible, value = run(calc)
        self.assertTrue(eligible)
        self.assertEqual(value, VALUE_PER_MEMBER)

    def test_scenario_8_resources_over_limit_ineligible(self):
        calc = make_calculator([make_member(age=40, monthly_earned=1_800)], household_assets=20_000)
        eligible, _ = run(calc)
        self.assertFalse(eligible)

    def test_scenario_9_already_on_medicaid_ineligible(self):
        # insurance = medicaid -> fails insurance-type check
        calc = make_calculator(
            [make_member(age=39, monthly_earned=1_200, insurance_types=("medicaid",))], household_assets=3_000
        )
        eligible, _ = run(calc)
        self.assertFalse(eligible)

    def test_scenario_10_age_16_eligible(self):
        calc = make_calculator([make_member(age=16, monthly_earned=800)], household_assets=1_000)
        eligible, value = run(calc)
        self.assertTrue(eligible)
        self.assertEqual(value, VALUE_PER_MEMBER)

    def test_scenario_11_age_15_ineligible(self):
        calc = make_calculator([make_member(age=15, monthly_earned=800)], household_assets=1_000)
        eligible, _ = run(calc)
        self.assertFalse(eligible)

    def test_scenario_12_age_64_eligible(self):
        calc = make_calculator([make_member(age=64, monthly_earned=1_200)])
        eligible, value = run(calc)
        self.assertTrue(eligible)
        self.assertEqual(value, VALUE_PER_MEMBER)

    def test_scenario_13_age_65_ineligible(self):
        calc = make_calculator([make_member(age=65, monthly_earned=1_200)])
        eligible, _ = run(calc)
        self.assertFalse(eligible)

    def test_scenario_14_multi_member_both_eligible(self):
        p1 = make_member(age=42, monthly_earned=1_200, relationship="headOfHousehold")
        p2 = make_member(age=35, monthly_earned=950, relationship="spouse")
        # mark them married to each other for plan-size (2-person -> higher ceiling, still eligible)
        p1.is_married = Mock(return_value={"is_married": True, "married_to": p2})
        p2.is_married = Mock(return_value={"is_married": True, "married_to": p1})
        calc = make_calculator([p1, p2], household_assets=8_000, fpl_limit=FPL_1)
        # 2-person plan ceiling: use a 2-person FPL for get_limit
        calc.program.year.get_limit = Mock(return_value=21_640)
        eligible, value = run(calc)
        self.assertTrue(eligible)
        self.assertEqual(value, 2 * VALUE_PER_MEMBER)

    def test_scenario_15_ssi_recipient_ineligible(self):
        calc = make_calculator([make_member(age=40, monthly_earned=1_200, monthly_ssi=700)], household_assets=2_000)
        eligible, _ = run(calc)
        self.assertFalse(eligible)

    def test_scenario_16_earnings_below_floor_ineligible(self):
        # $50/mo gross earned <= $65 floor
        calc = make_calculator([make_member(age=40, monthly_earned=50)], household_assets=2_000)
        eligible, _ = run(calc)
        self.assertFalse(eligible)

    # Scenario 17 (non-KS resident) is enforced by white-label routing, not the
    # calculator, so there is no calculator-level unit test for it.

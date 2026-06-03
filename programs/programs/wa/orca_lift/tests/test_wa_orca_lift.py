from django.test import TestCase
from unittest.mock import Mock

from programs.programs.wa import wa_calculators
from programs.programs.wa.orca_lift.calculator import WaOrcaLift
from programs.programs.calc import Eligibility, MemberEligibility


def make_member(age=35, birth_year_month=None, yearly_income=24_000, insurance_medicaid=False, insurance_chp=False):
    member = Mock()
    member.age = age
    member.birth_year_month = birth_year_month

    def calc_age():
        return age

    member.calc_age = Mock(side_effect=calc_age)

    def calc_gross_income(freq, types, **kwargs):
        if freq == "yearly":
            return yearly_income
        return yearly_income / 12

    member.calc_gross_income = Mock(side_effect=calc_gross_income)

    def has_benefit(name):
        if name == "wa_apple_health_medicaid":
            return insurance_medicaid
        if name == "wa_apple_health_for_kids":
            return insurance_chp
        return False

    member.has_insurance = Mock(side_effect=has_benefit)
    return member


def make_calculator(
    has_wa_snap=False,
    has_wa_wic=False,
    members=None,
    yearly_income=24_000,
    household_size=1,
    fpl_annual=15_960,
):
    mock_screen = Mock()

    def has_benefit(name):
        return {
            "wa_snap": has_wa_snap,
            "wa_wic": has_wa_wic,
        }.get(name, False)

    mock_screen.has_benefit = Mock(side_effect=has_benefit)
    mock_screen.household_size = household_size

    def calc_gross_income(freq, types, **kwargs):
        if freq == "yearly":
            return yearly_income
        return yearly_income / 12

    mock_screen.calc_gross_income = Mock(side_effect=calc_gross_income)

    if members is None:
        members = [make_member(age=35, yearly_income=yearly_income)]
    mock_screen.household_members.all.return_value = members

    mock_program = Mock()
    mock_program.year.get_limit = Mock(return_value=fpl_annual)

    mock_missing_deps = Mock()
    mock_missing_deps.has.return_value = False

    return WaOrcaLift(mock_screen, mock_program, {}, mock_missing_deps)


class TestWaOrcaLiftClassAttributes(TestCase):
    def test_is_registered(self):
        self.assertIn("wa_orca_lift", wa_calculators)
        self.assertEqual(wa_calculators["wa_orca_lift"], WaOrcaLift)

    def test_min_max_age(self):
        self.assertEqual(WaOrcaLift.min_age, 19)
        self.assertEqual(WaOrcaLift.max_age, 64)

    def test_fpl_percent(self):
        self.assertEqual(WaOrcaLift.fpl_percent, 2.0)

    def test_member_amount(self):
        self.assertEqual(WaOrcaLift.member_amount, 864)


class TestWaOrcaLiftMemberEligibility(TestCase):
    def _run(self, member):
        calc = make_calculator()
        e = MemberEligibility(member)
        calc.member_eligible(e)
        return e.eligible

    def test_age_35_eligible(self):
        self.assertTrue(self._run(make_member(age=35)))

    def test_min_age_19_eligible(self):
        self.assertTrue(self._run(make_member(age=19)))

    def test_max_age_64_eligible(self):
        self.assertTrue(self._run(make_member(age=64)))

    def test_age_18_ineligible(self):
        self.assertFalse(self._run(make_member(age=18)))

    def test_age_65_ineligible(self):
        self.assertFalse(self._run(make_member(age=65)))

    def test_age_none_ineligible(self):
        member = make_member(age=None)
        member.calc_age = Mock(return_value=None)
        self.assertFalse(self._run(member))

    def test_uses_calc_age_over_age_field(self):
        # birth_year_month present — calc_age() should be called
        member = make_member(age=70)
        member.birth_year_month = object()  # not None
        member.calc_age = Mock(return_value=40)
        self.assertTrue(self._run(member))

    def test_age_zero_ineligible(self):
        self.assertFalse(self._run(make_member(age=0)))


class TestWaOrcaLiftHouseholdEligibility(TestCase):
    def _run_household(self, calc, eligible_member_ages=None):
        """Helper that runs the full eligible() flow and returns Eligibility."""
        if eligible_member_ages is None:
            eligible_member_ages = [35]
        members = [make_member(age=a) for a in eligible_member_ages]
        calc.screen.household_members.all.return_value = members
        return calc.eligible()

    # --- Income pathway ---

    def test_income_below_fpl_eligible(self):
        # $24,000/yr < 200% FPL ($31,920 for size 1)
        calc = make_calculator(yearly_income=24_000, fpl_annual=15_960)
        e = self._run_household(calc)
        self.assertTrue(e.eligible)

    def test_income_above_fpl_ineligible(self):
        # $54,000/yr > 200% FPL ($31,920 for size 1)
        calc = make_calculator(yearly_income=54_000, fpl_annual=15_960)
        e = self._run_household(calc)
        self.assertFalse(e.eligible)

    def test_income_exactly_at_fpl_eligible(self):
        # $31,920/yr == 200% FPL ($31,920) — boundary inclusive
        calc = make_calculator(yearly_income=31_920, fpl_annual=15_960)
        e = self._run_household(calc)
        self.assertTrue(e.eligible)

    def test_income_one_dollar_over_fpl_ineligible(self):
        # $31,933/yr > 200% FPL by $13 (simulating $2,661/month * 12)
        calc = make_calculator(yearly_income=31_932, fpl_annual=15_960)
        e = self._run_household(calc)
        self.assertFalse(e.eligible)

    # --- Categorical pathway: screen-level (Step 8 current benefits) ---

    def test_snap_bypasses_income(self):
        calc = make_calculator(has_wa_snap=True, yearly_income=60_000, fpl_annual=15_960)
        e = self._run_household(calc)
        self.assertTrue(e.eligible)

    def test_wic_bypasses_income(self):
        calc = make_calculator(has_wa_wic=True, yearly_income=60_000, fpl_annual=15_960)
        e = self._run_household(calc)
        self.assertTrue(e.eligible)

    # --- Categorical pathway: member-level insurance (Step 5) ---

    def test_member_apple_health_medicaid_bypasses_income(self):
        # Apple Health (adult Medicaid) selected on Step 5 triggers categorical eligibility
        members = [make_member(age=35, insurance_medicaid=True)]
        calc = make_calculator(yearly_income=60_000, fpl_annual=15_960, members=members)
        e = calc.eligible()
        self.assertTrue(e.eligible)

    def test_member_apple_health_for_kids_bypasses_income(self):
        # Apple Health for Kids (CHIP) selected on Step 5 triggers categorical eligibility
        members = [make_member(age=35, insurance_chp=True)]
        calc = make_calculator(yearly_income=60_000, fpl_annual=15_960, members=members)
        e = calc.eligible()
        self.assertTrue(e.eligible)

    def test_member_no_apple_health_high_income_ineligible(self):
        # No categorical benefit, income too high
        members = [make_member(age=35, insurance_medicaid=False, insurance_chp=False)]
        calc = make_calculator(yearly_income=60_000, fpl_annual=15_960, members=members)
        e = calc.eligible()
        self.assertFalse(e.eligible)

    def test_child_apple_health_for_kids_triggers_household_eligibility(self):
        # Child's Apple Health for Kids insurance makes the household categorically eligible;
        # the 35yo parent passes the age gate and receives the benefit
        members = [make_member(age=35), make_member(age=8, insurance_chp=True)]
        calc = make_calculator(yearly_income=60_000, fpl_annual=15_960, members=members)
        e = calc.eligible()
        self.assertTrue(e.eligible)

    # --- Age gate ---

    def test_no_member_19_64_ineligible_even_with_snap(self):
        # Household has SNAP and low income but no one aged 19–64 → ineligible
        members = [make_member(age=70), make_member(age=12), make_member(age=8)]
        calc = make_calculator(has_wa_snap=True, members=members, yearly_income=10_000, fpl_annual=15_960)
        e = calc.eligible()
        self.assertFalse(e.eligible)

    def test_no_member_19_64_ineligible_even_with_low_income(self):
        members = [make_member(age=70), make_member(age=15)]
        calc = make_calculator(members=members, yearly_income=10_000, fpl_annual=15_960)
        e = calc.eligible()
        self.assertFalse(e.eligible)


class TestWaOrcaLiftValue(TestCase):
    def test_single_eligible_adult_value(self):
        # Scenario 1: single adult aged 35, income eligible
        calc = make_calculator(yearly_income=24_000, fpl_annual=15_960)
        calc.screen.household_members.all.return_value = [make_member(age=35)]
        result = calc.calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 864)

    def test_two_eligible_adults_value_doubles(self):
        # Scenario 4: two adults aged 19–64 → value = 2 × $864
        members = [make_member(age=30), make_member(age=28)]
        calc = make_calculator(has_wa_snap=True, members=members, yearly_income=54_000, fpl_annual=15_960)
        result = calc.calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 1_728)

    def test_mixed_household_value_counts_only_19_64(self):
        # Scenario 3: household has 30yo, 65yo, 17yo, 8yo — only 30yo counted
        members = [
            make_member(age=30),
            make_member(age=65),
            make_member(age=17),
            make_member(age=8),
        ]
        calc = make_calculator(has_wa_snap=True, members=members, yearly_income=72_000, fpl_annual=15_960)
        result = calc.calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 864)

    def test_ineligible_household_has_zero_value(self):
        calc = make_calculator(yearly_income=60_000, fpl_annual=15_960)
        calc.screen.household_members.all.return_value = [make_member(age=35)]
        result = calc.calc()
        self.assertFalse(result.eligible)
        self.assertEqual(result.value, 0)

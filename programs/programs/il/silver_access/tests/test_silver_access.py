from django.test import TestCase
from unittest.mock import Mock, MagicMock

from programs.programs.calc import Eligibility, MemberEligibility
from programs.programs.il import il_calculators
from programs.programs.il.silver_access.calculator import IlSilverAccess


def make_insurance(none=False, private=False, medicaid=False, medicare=False, employer=False, va=False):
    ins = Mock()
    ins.has_insurance_types = Mock(
        side_effect=lambda types, strict=True: any(
            {
                "none": none,
                "private": private,
                "medicaid": medicaid,
                "medicare": medicare,
                "employer": employer,
                "va": va,
            }.get(t, False)
            for t in types
        )
    )
    return ins


def make_member(age=40, insurance=None):
    m = Mock()
    m.age = age
    m.insurance = insurance or make_insurance(none=True)
    return m


def make_calculator(county="DuPage", household_size=1, gross_income=30_000, members=None):
    screen = Mock()
    screen.county = county
    screen.household_size = household_size
    screen.calc_gross_income = Mock(return_value=gross_income)
    screen.household_members.all = Mock(return_value=members or [make_member()])

    program = Mock()
    fpl = Mock()
    # 2026 FPL values: HH1=$15,960, HH2=$21,640, HH3=$27,320
    fpl_table = {1: 15_960, 2: 21_640, 3: 27_320, 4: 33_000}
    fpl.get_limit = Mock(side_effect=lambda size: fpl_table.get(size, 15_960 + (size - 1) * 5_680))
    program.year = fpl

    missing_deps = Mock()
    missing_deps.has.return_value = False

    return IlSilverAccess(screen, program, {}, missing_deps)


class TestIlSilverAccessRegistration(TestCase):
    def test_registered_in_il_calculators(self):
        self.assertIn("il_silver_access", il_calculators)
        self.assertIs(il_calculators["il_silver_access"], IlSilverAccess)

    def test_class_attributes(self):
        self.assertEqual(IlSilverAccess.member_amount, 1_800)
        self.assertEqual(IlSilverAccess.fpl_percent, 2.5)
        self.assertEqual(IlSilverAccess.medicaid_fpl_percent, 1.38)
        self.assertEqual(IlSilverAccess.medicare_age, 65)
        self.assertEqual(IlSilverAccess.eligible_county, "DuPage")


class TestIlSilverAccessMemberEligibility(TestCase):
    def _check_member(self, member, expected_eligible):
        calc = make_calculator()
        e = MemberEligibility(member)
        calc.member_eligible(e)
        self.assertEqual(e.eligible, expected_eligible)

    def test_scenario1_none_insurance_eligible(self):
        # Scenario 1: insurance none → eligible
        m = make_member(age=40, insurance=make_insurance(none=True))
        self._check_member(m, True)

    def test_scenario4_medicaid_insurance_ineligible(self):
        # Scenario 4: Medicaid coverage → ineligible
        m = make_member(age=37, insurance=make_insurance(medicaid=True))
        self._check_member(m, False)

    def test_scenario5_medicare_insurance_ineligible(self):
        # Scenario 5: Medicare coverage → ineligible
        m = make_member(age=67, insurance=make_insurance(medicare=True))
        self._check_member(m, False)

    def test_scenario10_employer_insurance_ineligible(self):
        # Scenario 10: employer coverage → ineligible
        m = make_member(age=40, insurance=make_insurance(employer=True))
        self._check_member(m, False)

    def test_scenario11_age_66_no_medicare_reported_ineligible(self):
        # Scenario 11: age 66, no Medicare reported → excluded by age-65 rule
        m = make_member(age=66, insurance=make_insurance(none=True))
        self._check_member(m, False)

    def test_scenario13_private_insurance_eligible(self):
        # Scenario 13: private insurance (Marketplace plan) → eligible
        m = make_member(age=42, insurance=make_insurance(private=True))
        self._check_member(m, True)

    def test_scenario14_va_insurance_ineligible(self):
        # Scenario 14: VA coverage → ineligible
        m = make_member(age=40, insurance=make_insurance(va=True))
        self._check_member(m, False)

    def test_age_64_under_medicare_age_eligible(self):
        m = make_member(age=64, insurance=make_insurance(none=True))
        self._check_member(m, True)

    def test_age_65_at_medicare_age_ineligible(self):
        m = make_member(age=65, insurance=make_insurance(none=True))
        self._check_member(m, False)

    def test_age_none_passes_age_check(self):
        m = make_member(age=None, insurance=make_insurance(none=True))
        self._check_member(m, True)


class TestIlSilverAccessHouseholdEligibility(TestCase):
    def _run(self, county="DuPage", household_size=1, gross_income=30_000):
        calc = make_calculator(county=county, household_size=household_size, gross_income=gross_income)
        e = Eligibility()
        # Seed one eligible member so the household condition is meaningful
        me = MemberEligibility(make_member())
        e.add_member_eligibility(me)
        calc.household_eligible(e)
        return e.eligible

    def test_scenario1_dupage_eligible(self):
        # Scenario 1: DuPage county, $30,000 → eligible
        self.assertTrue(self._run(county="DuPage", gross_income=30_000))

    def test_scenario2_income_above_250_fpl_ineligible(self):
        # Scenario 2: $42,000 > $39,900 (HH1 250% FPL) → ineligible
        self.assertFalse(self._run(gross_income=42_000))

    def test_scenario3_income_exactly_at_250_fpl_eligible(self):
        # Scenario 3: $39,900 == HH1 250% FPL boundary → eligible
        self.assertTrue(self._run(gross_income=39_900))

    def test_scenario6_cook_county_ineligible(self):
        # Scenario 6: Cook County → ineligible
        self.assertFalse(self._run(county="Cook"))

    def test_scenario12_below_medicaid_threshold_ineligible(self):
        # Scenario 12: $9,600 < $22,025 (HH1 138% FPL) → excluded by Medicaid income check
        self.assertFalse(self._run(gross_income=9_600))

    def test_income_above_medicaid_threshold_eligible(self):
        # $23,000 > $22,025 and ≤ $39,900 → eligible
        self.assertTrue(self._run(gross_income=23_000))


class TestIlSilverAccessCalc(TestCase):
    def test_scenario1_eligible_single_adult(self):
        # Scenario 1: single eligible adult → $1,800/year
        calc = make_calculator(county="DuPage", household_size=1, gross_income=30_000)
        result = calc.calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 1_800)

    def test_scenario2_income_too_high_ineligible(self):
        # Scenario 2: $42,000 > 250% FPL → ineligible
        calc = make_calculator(county="DuPage", household_size=1, gross_income=42_000)
        result = calc.calc()
        self.assertFalse(result.eligible)

    def test_scenario3_boundary_income_eligible(self):
        # Scenario 3: income exactly at 250% FPL → eligible
        calc = make_calculator(county="DuPage", household_size=1, gross_income=39_900)
        result = calc.calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 1_800)

    def test_scenario4_medicaid_enrollment_ineligible(self):
        # Scenario 4: member enrolled in Medicaid → ineligible
        m = make_member(age=37, insurance=make_insurance(medicaid=True))
        calc = make_calculator(county="DuPage", household_size=1, gross_income=18_000, members=[m])
        result = calc.calc()
        self.assertFalse(result.eligible)

    def test_scenario5_medicare_enrollment_ineligible(self):
        # Scenario 5: age 67, Medicare → ineligible
        m = make_member(age=67, insurance=make_insurance(medicare=True))
        calc = make_calculator(county="DuPage", household_size=1, gross_income=16_800, members=[m])
        result = calc.calc()
        self.assertFalse(result.eligible)

    def test_scenario6_wrong_county_ineligible(self):
        # Scenario 6: Cook County → ineligible
        calc = make_calculator(county="Cook", household_size=1, gross_income=24_000)
        result = calc.calc()
        self.assertFalse(result.eligible)

    def test_scenario7_married_couple_both_eligible(self):
        # Scenario 7: two eligible spouses → $3,600/year
        m1 = make_member(age=46, insurance=make_insurance(none=True))
        m2 = make_member(age=43, insurance=make_insurance(none=True))
        calc = make_calculator(county="DuPage", household_size=2, gross_income=48_000, members=[m1, m2])
        result = calc.calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 3_600)

    def test_scenario8_mixed_household_one_eligible(self):
        # Scenario 8: HOH eligible, spouse and child on Medicaid → $1,800/year
        head = make_member(age=41, insurance=make_insurance(none=True))
        spouse = make_member(age=38, insurance=make_insurance(medicaid=True))
        child = make_member(age=12, insurance=make_insurance(medicaid=True))
        calc = make_calculator(county="DuPage", household_size=3, gross_income=54_000, members=[head, spouse, child])
        result = calc.calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 1_800)

    def test_scenario10_employer_coverage_ineligible(self):
        # Scenario 10: employer insurance → ineligible
        m = make_member(age=40, insurance=make_insurance(employer=True))
        calc = make_calculator(county="DuPage", household_size=1, gross_income=33_600, members=[m])
        result = calc.calc()
        self.assertFalse(result.eligible)

    def test_scenario11_age_66_excluded_by_age_rule(self):
        # Scenario 11: age 66, no Medicare reported → excluded by age-65 rule
        m = make_member(age=66, insurance=make_insurance(none=True))
        calc = make_calculator(county="DuPage", household_size=1, gross_income=24_000, members=[m])
        result = calc.calc()
        self.assertFalse(result.eligible)

    def test_scenario12_medicaid_eligible_not_enrolled_ineligible(self):
        # Scenario 12: income below 138% FPL, no Medicaid reported → excluded by Medicaid income check
        m = make_member(age=34, insurance=make_insurance(none=True))
        calc = make_calculator(county="DuPage", household_size=1, gross_income=9_600, members=[m])
        result = calc.calc()
        self.assertFalse(result.eligible)

    def test_scenario13_lpr_eligible(self):
        # Scenario 13: LPR adult, income above Medicaid threshold → eligible
        m = make_member(age=42, insurance=make_insurance(none=True))
        calc = make_calculator(county="DuPage", household_size=1, gross_income=26_400, members=[m])
        result = calc.calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 1_800)

    def test_scenario14_va_coverage_ineligible(self):
        # Scenario 14: VA coverage → ineligible
        m = make_member(age=40, insurance=make_insurance(va=True))
        calc = make_calculator(county="DuPage", household_size=1, gross_income=33_600, members=[m])
        result = calc.calc()
        self.assertFalse(result.eligible)

"""
Unit tests for KsK40h calculator — one test per spec.md Test Scenario (1-20).

Kansas Homestead Property Tax Refund (K-40H):
- Categorical path: age 55+ entire year (birth_year <= claim_year-56) / disability
  / dependent child under 18 entire year / veteran-income proxy
- Household income (K-40H adjusted) <= $43,389
- Owns & occupies (rent expense -> ineligible; else homeowner)
- Refund = allowed property tax (min(propertyTax, $700), default $700) x table %,
  refunds under $5 not issued

All scenarios use claim year 2025 rules. The calculator resolves claim year from
program.year.period (set to 2026 in config, but tests pin 2025 to match the spec's
birth-year math).
"""

from django.test import TestCase
from unittest.mock import Mock

from programs.programs.ks import ks_calculators
from programs.programs.ks.k40h.calculator import KsK40h
from programs.programs.calc import ProgramCalculator


def make_member(
    birth_year=1958,
    age=68,
    relationship="headOfHousehold",
    disabled=False,
    visually_impaired=False,
    long_term_disability=False,
    income=None,  # dict of {type: annual_amount}
):
    income = income or {}
    member = Mock()
    member.birth_year = birth_year
    member.age = age
    member.relationship = relationship
    member.disabled = disabled
    member.visually_impaired = visually_impaired
    member.long_term_disability = long_term_disability

    def calc_income(frequency, types, exclude=[]):
        # yearly amounts stored in `income`
        if types == ["all"]:
            return sum(v for t, v in income.items() if t not in exclude)
        return sum(income.get(t, 0) for t in types)

    member.calc_gross_income = Mock(side_effect=calc_income)
    return member


def make_calculator(members=None, rent=0, mortgage=0, property_tax=0, claim_year=2025):
    if members is None:
        members = [make_member()]

    mock_program = Mock()
    mock_program.year.period = str(claim_year)

    mock_screen = Mock()
    mock_screen.household_size = len(members)
    mock_screen.household_members.all = Mock(return_value=members)

    expenses = {"rent": rent, "mortgage": mortgage, "propertyTax": property_tax}
    mock_screen.has_expense = Mock(side_effect=lambda types: any(expenses.get(t, 0) > 0 for t in types))
    mock_screen.calc_expenses = Mock(side_effect=lambda freq, types: sum(expenses.get(t, 0) for t in types))

    mock_missing_deps = Mock()
    mock_missing_deps.has.return_value = False

    return KsK40h(mock_screen, mock_program, {}, mock_missing_deps)


def run(calc):
    e = calc.eligible()
    calc.value(e)
    return e.eligible, e.value


class TestClassAttributes(TestCase):
    def test_is_subclass(self):
        self.assertTrue(issubclass(KsK40h, ProgramCalculator))

    def test_registered(self):
        self.assertIn("ks_k40h", ks_calculators)
        self.assertEqual(ks_calculators["ks_k40h"], KsK40h)

    def test_constants(self):
        self.assertEqual(KsK40h.income_limit, 43_389)
        self.assertEqual(KsK40h.max_property_tax, 700)
        self.assertEqual(KsK40h.min_refund, 5)


class TestSpecScenarios(TestCase):
    def test_s1_senior_ss_golden_path(self):
        m = make_member(birth_year=1958, age=68, income={"sSRetirement": 16_800})
        eligible, value = run(make_calculator([m]))
        self.assertTrue(eligible)
        self.assertEqual(value, 616)  # 50%*16800=8400 -> 88%; 700*.88

    def test_s2_renter_ineligible(self):
        m = make_member(birth_year=1956, age=70, income={"sSRetirement": 14_400})
        eligible, _ = run(make_calculator([m], rent=800 * 12))
        self.assertFalse(eligible)

    def test_s3_dependent_child_near_limit(self):
        p1 = make_member(birth_year=1983, age=42, income={"wages": 27_600})
        p2 = make_member(birth_year=1986, age=40, relationship="spouse", income={"wages": 14_400})
        child = make_member(birth_year=2012, age=14, relationship="child")
        eligible, value = run(make_calculator([p1, p2, child], mortgage=900 * 12))
        self.assertTrue(eligible)
        self.assertEqual(value, 35)  # income 42000 -> 5%; 700*.05

    def test_s4_income_just_below_limit(self):
        m = make_member(birth_year=1957, age=69, income={"pension": 43_200})
        eligible, value = run(make_calculator([m]))
        self.assertTrue(eligible)
        self.assertEqual(value, 35)

    def test_s5_income_exactly_at_limit(self):
        m = make_member(birth_year=1955, age=70, income={"pension": 43_389})
        eligible, value = run(make_calculator([m]))
        self.assertTrue(eligible)
        self.assertEqual(value, 35)

    def test_s6_income_just_above_limit(self):
        m = make_member(birth_year=1957, age=69, income={"pension": 43_500})
        eligible, _ = run(make_calculator([m]))
        self.assertFalse(eligible)

    def test_s7_age_boundary_born_dec_1969(self):
        m = make_member(birth_year=1969, age=56, income={"sSRetirement": 14_400})
        eligible, value = run(make_calculator([m]))
        self.assertTrue(eligible)
        self.assertEqual(value, 644)  # 50%*14400=7200 -> 92%; 700*.92

    def test_s8_age_boundary_born_mar_1970_ineligible(self):
        # born 1970 -> not 55 the entire 2025; no other path -> ineligible
        m = make_member(birth_year=1970, age=56, income={"wages": 18_000})
        eligible, _ = run(make_calculator([m], mortgage=750 * 12))
        self.assertFalse(eligible)

    def test_s9_disability_path_ssdi_excluded(self):
        m = make_member(birth_year=1986, age=39, disabled=True, income={"sSDisability": 16_800})
        eligible, value = run(make_calculator([m]))
        self.assertTrue(eligible)
        self.assertEqual(value, 700)  # SSDI excluded -> income 0 -> 100%

    def test_s10_senior_couple_50pct_ss(self):
        p1 = make_member(birth_year=1955, age=71, income={"sSRetirement": 18_000})
        p2 = make_member(birth_year=1958, age=68, relationship="spouse", income={"sSRetirement": 15_600})
        eligible, value = run(make_calculator([p1, p2]))
        self.assertTrue(eligible)
        self.assertEqual(value, 385)  # 50%*33600=16800 -> 55%; 700*.55

    def test_s11_property_tax_below_cap(self):
        m = make_member(birth_year=1958, age=68, income={"sSRetirement": 16_800})
        eligible, value = run(make_calculator([m], property_tax=50 * 12))
        self.assertTrue(eligible)
        self.assertEqual(value, 528)  # income 8400 -> 88%; min(600,700)=600; 600*.88

    def test_s12_veteran_proxy_path(self):
        m = make_member(birth_year=1981, age=45, income={"veteran": 12_000})
        eligible, value = run(make_calculator([m]))
        self.assertTrue(eligible)
        self.assertEqual(value, 532)  # income 12000 -> 76%; 700*.76

    def test_s13_child_turned_18_during_year_ineligible(self):
        p1 = make_member(birth_year=1981, age=44, income={"wages": 24_000})
        child = make_member(birth_year=2007, age=19, relationship="child")
        eligible, _ = run(make_calculator([p1, child], mortgage=850 * 12))
        self.assertFalse(eligible)

    def test_s14_no_categorical_path_ineligible(self):
        m = make_member(birth_year=1976, age=50, income={"wages": 21_600})
        eligible, _ = run(make_calculator([m], mortgage=800 * 12))
        self.assertFalse(eligible)

    def test_s15_sub_5_refund_not_issued(self):
        # income 43200 -> 5%; propertyTax $96/yr -> min(96,700)=96; 96*.05=4.8 < $5
        m = make_member(birth_year=1957, age=69, income={"pension": 43_200})
        eligible, value = run(make_calculator([m], property_tax=8 * 12))
        # refund below floor -> value 0 (ineligible / no payable value)
        self.assertEqual(value, 0)

    def test_s16_surviving_spouse_sssurvivor_ssi_50pct(self):
        m = make_member(
            birth_year=1975,
            age=51,
            income={"veteran": 6_000, "sSSurvivor": 9_600, "sSI": 4_800},
        )
        eligible, value = run(make_calculator([m]))
        self.assertTrue(eligible)
        # 6000 + 0.5*9600 + 0.5*4800 = 6000+4800+2400 = 13200 -> 68%; 700*.68
        self.assertEqual(value, 476)

    def test_s17_child_support_and_gifts_excluded(self):
        m = make_member(
            birth_year=1960,
            age=65,
            income={"wages": 4_800, "childSupport": 21_600, "gifts": 3_600},
        )
        eligible, value = run(make_calculator([m]))
        self.assertTrue(eligible)
        self.assertEqual(value, 700)  # only 4800 wages -> 100%

    def test_s18_visually_impaired_path(self):
        m = make_member(birth_year=1986, age=40, visually_impaired=True, income={"wages": 12_600})
        eligible, value = run(make_calculator([m]))
        self.assertTrue(eligible)
        self.assertEqual(value, 504)  # income 12600 -> 72%; 700*.72

    def test_s19_dependent_child_income_excluded(self):
        p1 = make_member(birth_year=1965, age=60, income={"wages": 6_000})
        child = make_member(birth_year=2009, age=16, relationship="child", income={"wages": 3_600})
        eligible, value = run(make_calculator([p1, child]))
        self.assertTrue(eligible)
        self.assertEqual(value, 700)  # child wages excluded -> 6000 -> 100%

    def test_s20_long_term_disability_path(self):
        m = make_member(birth_year=1990, age=35, long_term_disability=True, income={"wages": 14_400})
        eligible, value = run(make_calculator([m]))
        self.assertTrue(eligible)
        self.assertEqual(value, 448)  # income 14400 -> 64%; 700*.64

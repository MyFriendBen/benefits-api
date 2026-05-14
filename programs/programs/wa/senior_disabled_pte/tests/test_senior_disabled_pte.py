from django.test import TestCase
from unittest.mock import Mock

from programs.programs.wa import wa_calculators
from programs.programs.wa.senior_disabled_pte.calculator import WaSeniorDisabledPte
from programs.programs.calc import ProgramCalculator, Eligibility, MemberEligibility


def make_member(age=70, long_term_disability=False, disabled=False, veteran=False):
    member = Mock()
    member.age = age
    member.long_term_disability = long_term_disability
    member.disabled = disabled
    member.veteran = veteran
    return member


def make_calculator(county="King County", household_income=14_400, property_tax_expense=1_200):
    mock_screen = Mock()
    mock_screen.county = county
    mock_screen.calc_gross_income = Mock(return_value=household_income)
    mock_screen.calc_expenses = Mock(return_value=property_tax_expense)

    mock_program = Mock()
    mock_missing_deps = Mock()
    mock_missing_deps.has.return_value = False

    return WaSeniorDisabledPte(mock_screen, mock_program, {}, mock_missing_deps)


class TestClassAttributes(TestCase):
    def test_is_registered_in_wa_calculators(self):
        self.assertIn("wa_senior_disabled_pte", wa_calculators)
        self.assertEqual(wa_calculators["wa_senior_disabled_pte"], WaSeniorDisabledPte)

    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(WaSeniorDisabledPte, ProgramCalculator))

    def test_min_age_is_61(self):
        self.assertEqual(WaSeniorDisabledPte.min_age, 61)

    def test_king_county_threshold_3(self):
        self.assertEqual(WaSeniorDisabledPte.COUNTY_THRESHOLDS["King County"][2], 84_000)

    def test_spokane_county_threshold_3(self):
        self.assertEqual(WaSeniorDisabledPte.COUNTY_THRESHOLDS["Spokane County"][2], 50_000)

    def test_chelan_county_threshold_3(self):
        self.assertEqual(WaSeniorDisabledPte.COUNTY_THRESHOLDS["Chelan County"][2], 48_000)

    def test_all_39_counties_present(self):
        self.assertEqual(len(WaSeniorDisabledPte.COUNTY_THRESHOLDS), 39)


class TestMemberEligibility(TestCase):
    def _run(self, member):
        calc = make_calculator()
        e = MemberEligibility(member)
        calc.member_eligible(e)
        return e.eligible

    # Age pathway
    def test_age_67_eligible(self):
        self.assertTrue(self._run(make_member(age=67)))

    def test_age_61_boundary_eligible(self):
        self.assertTrue(self._run(make_member(age=61)))

    def test_age_60_ineligible(self):
        self.assertFalse(self._run(make_member(age=60)))

    def test_age_none_ineligible(self):
        self.assertFalse(self._run(make_member(age=None)))

    # Disability-retirement pathway
    def test_under_61_long_term_disability_eligible(self):
        self.assertTrue(self._run(make_member(age=45, long_term_disability=True)))

    def test_under_61_disabled_only_ineligible(self):
        self.assertFalse(self._run(make_member(age=45, disabled=True)))

    # Disabled-veteran pathway
    def test_veteran_with_long_term_disability_eligible(self):
        self.assertTrue(self._run(make_member(age=45, veteran=True, long_term_disability=True)))

    def test_veteran_with_disabled_eligible(self):
        self.assertTrue(self._run(make_member(age=45, veteran=True, disabled=True)))

    def test_veteran_without_disability_ineligible(self):
        self.assertFalse(self._run(make_member(age=45, veteran=True)))

    # No pathway
    def test_age_45_no_pathway_ineligible(self):
        self.assertFalse(self._run(make_member(age=45)))


class TestHouseholdEligibility(TestCase):
    def _run(self, county, household_income):
        calc = make_calculator(county=county, household_income=household_income)
        member = make_member(age=67)
        e = Eligibility()
        me = MemberEligibility(member)
        me.eligible = True
        e.add_member_eligibility(me)
        calc.household_eligible(e)
        return e.eligible

    def test_king_county_below_threshold_eligible(self):
        self.assertTrue(self._run("King County", 14_400))

    def test_king_county_at_threshold_3_eligible(self):
        self.assertTrue(self._run("King County", 84_000))

    def test_king_county_above_threshold_3_ineligible(self):
        self.assertFalse(self._run("King County", 84_001))

    def test_spokane_county_below_threshold_eligible(self):
        self.assertTrue(self._run("Spokane County", 30_000))

    def test_spokane_county_above_threshold_3_ineligible(self):
        self.assertFalse(self._run("Spokane County", 50_001))

    def test_unknown_county_uses_default_threshold(self):
        self.assertTrue(self._run("Unknown County", 40_000))
        self.assertFalse(self._run("Unknown County", 40_001))


class TestBenefitValue(TestCase):
    def test_household_value_returns_property_tax_expense(self):
        calc = make_calculator(property_tax_expense=1_200)
        self.assertEqual(calc.household_value(), 1_200)

    def test_household_value_zero_when_no_property_tax(self):
        calc = make_calculator(property_tax_expense=0)
        self.assertEqual(calc.household_value(), 0)

    def test_member_value_always_zero(self):
        calc = make_calculator()
        member = make_member(age=67)
        self.assertEqual(calc.member_value(member), 0)


class TestEndToEnd(TestCase):
    def _make_full_calc(self, members, county="King County", household_income=14_400, property_tax=1_200):
        mock_screen = Mock()
        mock_screen.county = county
        mock_screen.calc_gross_income = Mock(return_value=household_income)
        mock_screen.calc_expenses = Mock(return_value=property_tax)
        mock_screen.household_members.all = Mock(return_value=members)

        mock_program = Mock()
        mock_missing_deps = Mock()
        mock_missing_deps.has.return_value = False

        return WaSeniorDisabledPte(mock_screen, mock_program, {}, mock_missing_deps)

    def test_eligible_senior_golden_path(self):
        calc = self._make_full_calc([make_member(age=67)], household_income=14_400, property_tax=1_200)
        result = calc.calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 1_200)

    def test_ineligible_age_60_no_pathway(self):
        calc = self._make_full_calc([make_member(age=60)], household_income=14_400)
        result = calc.calc()
        self.assertFalse(result.eligible)

    def test_eligible_veteran_with_disability(self):
        calc = self._make_full_calc(
            [make_member(age=45, veteran=True, long_term_disability=True)],
            county="Spokane County",
            household_income=30_000,
            property_tax=1_200,
        )
        result = calc.calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 1_200)

    def test_ineligible_income_above_threshold(self):
        calc = self._make_full_calc([make_member(age=68)], household_income=85_000)
        result = calc.calc()
        self.assertFalse(result.eligible)

    def test_eligible_multi_member_household(self):
        members = [make_member(age=67), make_member(age=64)]
        calc = self._make_full_calc(members, household_income=57_600, property_tax=2_400)
        result = calc.calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 2_400)

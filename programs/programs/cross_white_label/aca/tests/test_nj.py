"""
NJ ACA Premium Tax Credit (``NjAca``): one test per Test Scenario in the NJ spec
(``programs/cross_white_label/aca/nj/aca_nj_spec.md`` in program-ops), then NJ's benchmark
premium and the paths no scenario reaches.

Every scenario is screened between November 1, 2026 and October 31, 2027 (coverage year 2027),
so the reference date is pinned inside that window. NJ Medicaid and NJ CHIP results are passed
in, as the screener does, rather than calculated: scenarios 4 and 7 are adults NJ FamilyCare
covers, and scenario 13's child is one NJ CHIP covers.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from programs.framework.base import Eligibility, MemberEligibility
from programs.programs.cross_white_label.aca.nj import NjAca
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from programs.util import UpstreamAbsentError
from screener.models import HouseholdMember, Screen


def covers(*members: HouseholdMember) -> Eligibility:
    """An upstream program's result that finds exactly ``members`` eligible."""
    result = Eligibility()
    for member in members:
        result.add_member_eligibility(MemberEligibility(member))

    return result


def nj_familycare(medicaid: tuple = (), chip: tuple = ()) -> dict[str, Eligibility]:
    """NJ Medicaid's and NJ CHIP's results; nobody is covered unless named."""
    return {"nj_medicaid": covers(*medicaid), "nj_chip": covers(*chip)}


class NjAcaTestCase(CustomCalculatorTestCase):
    calculator_class = NjAca
    white_label_code = "nj"
    state_code = "NJ"
    fpl_year = "2026"
    default_zipcode = "07102"
    default_county = "Essex County"
    reference_date = date(2026, 11, 15)

    def calculate_nj(self, screen: Screen, medicaid: tuple = (), chip: tuple = ()) -> Eligibility:
        return self.calculate(screen, data=nj_familycare(medicaid, chip))

    def member_result(self, e: Eligibility, member: HouseholdMember) -> MemberEligibility:
        return next(member_e for member_e in e.eligible_members if member_e.member.id == member.id)

    def single_adult(self, age: int = 40, wages: int = 40_000) -> tuple[Screen, HouseholdMember]:
        screen = self.make_screen(household_size=1)
        head = self.add_member(screen, age=age, yearly_income=wages)
        return screen, head


class TestNjAcaRegistration(NjAcaTestCase):
    def test_program_code(self):
        self.assertEqual(NjAca.program_code, "nj_aca_ptc")

    def test_reads_nj_familycare_medicaid_and_chip(self):
        self.assertEqual(NjAca.medicaid_chip_program_codes, ("nj_medicaid", "nj_chip"))
        self.assertEqual(NjAca.gates_on, ("nj_medicaid", "nj_chip"))


class TestNjAcaScenarios(NjAcaTestCase):
    def test_scenario_1_single_adult_at_250_percent(self):
        screen, _ = self.single_adult(wages=40_000)

        e = self.calculate_nj(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 3_073)

    def test_scenario_2_single_adult_exactly_at_400_percent(self):
        screen, _ = self.single_adult(wages=63_840)

        e = self.calculate_nj(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 13)

    def test_scenario_3_single_adult_one_dollar_over_400_percent(self):
        screen, _ = self.single_adult(wages=63_841)

        e = self.calculate_nj(screen)

        self.assertFalse(e.eligible)

    def test_scenario_4_single_adult_one_dollar_under_the_poverty_line(self):
        screen, head = self.single_adult(wages=15_959)

        e = self.calculate_nj(screen, medicaid=(head,))

        self.assertFalse(e.eligible)
        self.assertFalse(self.member_result(e, head).eligible)

    def test_scenario_5_family_of_three_exactly_at_400_percent(self):
        screen = self.make_screen(household_size=3)
        self.add_member(screen, age=40, yearly_income=109_280)
        self.add_member(screen, relationship="spouse", age=40)
        self.add_member(screen, relationship="child", age=10)

        e = self.calculate_nj(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 5_819)

    def test_scenario_6_family_of_three_one_dollar_over_400_percent(self):
        screen = self.make_screen(household_size=3)
        self.add_member(screen, age=40, yearly_income=109_281)
        self.add_member(screen, relationship="spouse", age=40)
        self.add_member(screen, relationship="child", age=10)

        e = self.calculate_nj(screen)

        self.assertFalse(e.eligible)

    def test_scenario_7_single_adult_nj_familycare_would_cover(self):
        screen, head = self.single_adult(wages=18_000)

        e = self.calculate_nj(screen, medicaid=(head,))

        self.assertFalse(e.eligible)
        self.assertFalse(self.member_result(e, head).eligible)

    def test_scenario_8_single_adult_reporting_medicaid(self):
        screen, head = self.single_adult(wages=40_000)
        self.add_insurance(head, medicaid=True, none=False)

        e = self.calculate_nj(screen)

        self.assertFalse(e.eligible)

    def test_scenario_9_adult_aged_66_drawing_social_security_retirement(self):
        screen = self.make_screen(household_size=1)
        head = self.add_member(screen, age=66, yearly_income=20_000)
        self.add_income(head, 20_000, income_type="sSRetirement", frequency="yearly")

        e = self.calculate_nj(screen)

        self.assertFalse(e.eligible)

    def test_scenario_10_adult_under_65_drawing_social_security_disability(self):
        screen = self.make_screen(household_size=1)
        head = self.add_member(screen, age=50, yearly_income=20_000)
        self.add_income(head, 15_000, income_type="sSDisability", frequency="yearly")

        e = self.calculate_nj(screen)

        self.assertFalse(e.eligible)

    def test_scenario_11_single_adult_enrolled_in_job_based_coverage(self):
        screen, head = self.single_adult(wages=40_000)
        self.add_insurance(head, employer=True, none=False)

        e = self.calculate_nj(screen)

        self.assertFalse(e.eligible)

    def test_scenario_12_couple_where_only_the_spouse_has_job_based_coverage(self):
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, age=40, yearly_income=50_000)
        spouse = self.add_member(screen, relationship="spouse", age=40)
        self.add_insurance(spouse, employer=True, none=False)

        e = self.calculate_nj(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 2_562)
        self.assertTrue(self.member_result(e, head).eligible)
        self.assertFalse(self.member_result(e, spouse).eligible)

    def test_scenario_13_parent_and_child_nj_chip_would_cover(self):
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, age=40, yearly_income=50_000)
        child = self.add_member(screen, relationship="child", age=10)

        e = self.calculate_nj(screen, chip=(child,))

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 2_562)
        self.assertTrue(self.member_result(e, head).eligible)
        # The spec's Kills: the household is eligible either way, so only Person 2's own
        # result catches an NJ CHIP left out of the list.
        self.assertFalse(self.member_result(e, child).eligible)

    def test_scenario_14_adult_aged_62_drawing_social_security_retirement(self):
        screen = self.make_screen(household_size=1)
        head = self.add_member(screen, age=62, yearly_income=20_000)
        self.add_income(head, 20_000, income_type="sSRetirement", frequency="yearly")

        e = self.calculate_nj(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 11_231)


class TestNjAcaBenchmarkPremium(NjAcaTestCase):
    def test_base_rate_times_the_age_factor(self):
        screen, head = self.single_adult(age=40)

        calculator = self.make_calculator(screen, data=nj_familycare())

        self.assertEqual(calculator.benchmark_premium([head]), Decimal("426.25") * Decimal("1.278"))

    def test_age_factors_at_the_table_edges(self):
        self.assertEqual(NjAca.age_rating_factor(0), Decimal("0.765"))
        self.assertEqual(NjAca.age_rating_factor(14), Decimal("0.765"))
        self.assertEqual(NjAca.age_rating_factor(15), Decimal("0.833"))
        self.assertEqual(NjAca.age_rating_factor(63), Decimal("2.952"))
        self.assertEqual(NjAca.age_rating_factor(64), Decimal("3.000"))
        self.assertEqual(NjAca.age_rating_factor(80), Decimal("3.000"))

    def test_only_the_three_oldest_dependent_children_under_20_are_priced(self):
        screen = self.make_screen(household_size=6)
        head = self.add_member(screen, age=40, yearly_income=60_000)
        spouse = self.add_member(screen, relationship="spouse", age=40)
        children = [self.add_member(screen, relationship="child", age=age) for age in (10, 10, 16, 17)]

        calculator = self.make_calculator(screen, data=nj_familycare())

        # 0.885 (17) + 0.859 (16) + 0.765 (one of the 10-year-olds)
        expected = Decimal("426.25") * (Decimal("1.278") * 2 + Decimal("2.509"))
        self.assertEqual(calculator.benchmark_premium([head, spouse, *children]), expected)

    def test_a_dependent_aged_20_is_priced_as_an_adult(self):
        screen = self.make_screen(household_size=5)
        head = self.add_member(screen, age=40, yearly_income=60_000)
        children = [self.add_member(screen, relationship="child", age=age) for age in (10, 10, 10)]
        student = self.add_member(screen, relationship="child", age=20, student=True)

        calculator = self.make_calculator(screen, data=nj_familycare())

        expected = Decimal("426.25") * (Decimal("1.278") + Decimal("0.765") * 3 + Decimal("0.970"))
        self.assertEqual(calculator.benchmark_premium([head, *children, student]), expected)

    def test_age_rating_needs_an_age(self):
        with self.assertRaises(ValueError):
            NjAca.age_rating_factor(None)


class TestNjAcaGates(NjAcaTestCase):
    def test_left_out_when_nj_medicaid_was_not_calculated(self):
        """NJ Medicaid is a PolicyEngine program, so while its row is switched off it isn't
        calculated, and this program is left out rather than guessed at."""
        screen, _ = self.single_adult()

        with self.assertRaises(UpstreamAbsentError):
            self.calculate(screen, data={"nj_chip": covers()})

    def test_left_out_when_nj_chip_was_not_calculated(self):
        screen, _ = self.single_adult()

        with self.assertRaises(UpstreamAbsentError):
            self.calculate(screen, data={"nj_medicaid": covers()})


class TestNjAcaOutsideTheScenarios(NjAcaTestCase):
    def test_a_member_turning_65_mid_year_on_retirement_income_counts_until_that_month(self):
        """Monthly path: in the coverage family for January–May only."""
        screen = self.make_screen(household_size=1)
        head = self.add_member(screen, age=None, birth_year_month=date(1962, 6, 1), yearly_income=20_000)
        self.add_income(head, 20_000, income_type="sSRetirement", frequency="yearly")

        e = self.calculate_nj(screen)

        # $40,000 is 250%, so 8.66%: $3,464 a year, $289 a month. Age 64 prices at 3.000:
        # $426.25 × 3.000 = $1,278.75, $1,279 a month. Five months of $1,279 − $289.
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 5 * (1_279 - 289))

    def test_a_member_turning_65_mid_year_without_retirement_income_counts_all_year(self):
        screen = self.make_screen(household_size=1)
        self.add_member(screen, age=None, birth_year_month=date(1962, 6, 1), yearly_income=40_000)

        e = self.calculate_nj(screen)

        # Full-year path: $1,278.75 × 12 = $15,345, less $3,464.
        self.assertEqual(e.value, 15_345 - 3_464)

    def test_an_eligible_household_whose_contribution_exceeds_the_benchmark_gets_nothing(self):
        """Age 21 at 400%: $426.25 × 12 = $5,115 against a $6,524 contribution."""
        screen, _ = self.single_adult(age=21, wages=63_840)

        e = self.calculate_nj(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 0)

    def test_a_domestic_partner_is_left_out_with_their_income(self):
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, age=40, yearly_income=40_000)
        partner = self.add_member(screen, relationship="domesticPartner", age=40, yearly_income=40_000)

        e = self.calculate_nj(screen)

        # Scenario 1's household: the partner adds neither a person nor income.
        self.assertEqual(e.value, 3_073)
        self.assertTrue(self.member_result(e, head).eligible)
        self.assertFalse(self.member_result(e, partner).eligible)

    def test_a_roommate_is_not_in_the_coverage_family(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, age=40, yearly_income=40_000)
        roommate = self.add_member(screen, relationship="roommate", age=40, yearly_income=40_000)

        e = self.calculate_nj(screen)

        self.assertEqual(e.value, 3_073)
        self.assertFalse(self.member_result(e, roommate).eligible)

    def test_reporting_va_or_medicare_takes_a_member_out(self):
        for coverage in ("va", "medicare", "chp"):
            with self.subTest(coverage=coverage):
                screen, head = self.single_adult()
                self.add_insurance(head, none=False, **{coverage: True})

                self.assertFalse(self.calculate_nj(screen).eligible)


class TestNjAcaCoverageYear(NjAcaTestCase):
    reference_date = None

    def coverage_year_on(self, day: date) -> int:
        with patch.object(Screen, "get_reference_date", lambda _self: day):
            screen, _ = self.single_adult()
            return self.make_calculator(screen, data=nj_familycare()).coverage_year()

    def test_open_enrollment_starts_next_years_coverage(self):
        self.assertEqual(self.coverage_year_on(date(2026, 10, 31)), 2026)
        self.assertEqual(self.coverage_year_on(date(2026, 11, 1)), 2027)
        self.assertEqual(self.coverage_year_on(date(2027, 10, 31)), 2027)

    def test_a_poverty_guideline_for_another_coverage_year_is_reported(self):
        """Before November 1, 2026 the coverage year is 2026, which uses the 2025 guideline;
        the record carries the 2026 one."""
        with patch.object(Screen, "get_reference_date", lambda _self: date(2026, 10, 15)):
            screen, _ = self.single_adult()
            with patch("programs.programs.cross_white_label.aca.mfb_base.capture_message") as report:
                self.calculate_nj(screen)

        report.assert_called()
        self.assertIn("2026 poverty guideline for coverage year 2026", report.call_args.args[0])

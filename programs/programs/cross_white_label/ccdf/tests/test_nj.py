"""
Unit tests for NJ CCAP (``NjCcap``).

One test per scenario in ``programs/cross_white_label/ccdf/nj/ccdf_nj_spec.md`` section 8 (in
program-ops), then tests for the branches the scenarios do not reach. The base's own rules are
tested in ``test_base.py``.

The spec states monthly values to the cent. The calculator returns whole dollars a year, so
each scenario asserts the spec's monthly figure times 12, rounded half up.

Not tested, because nothing in the calculator evaluates them: residency (the white label),
the child's immigration status (the program record), and the protective services route.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from programs.framework.base import PaymentUnit, ProgramCalculator
from programs.framework.registry import build
from programs.programs.cross_white_label.ccdf.base import Ccdf
from programs.programs.cross_white_label.ccdf.nj import NjCcap
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from screener.models import HouseholdMember, IncomeStream, Screen

# NJ Income Eligibility Schedule 2026-2027, by household size: (100% of FPL, 200% of FPL).
NJ_SCHEDULE = {
    1: (15_960, 31_920),
    2: (21_640, 43_280),
    3: (27_320, 54_640),
    4: (33_000, 66_000),
    5: (38_680, 77_360),
    6: (44_360, 88_720),
    7: (50_040, 100_080),
    8: (55_720, 111_440),
    9: (61_400, 122_800),
    10: (67_080, 134_160),
    11: (72_760, 145_520),
    12: (78_440, 156_880),
}


def annual(monthly: str) -> int:
    """The spec's monthly value as the whole dollars a year the calculator returns."""
    return int((Decimal(monthly) * 12).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def add_hourly(member: HouseholdMember, rate: int, hours: int, income_type: str = "wages") -> IncomeStream:
    stream = IncomeStream.objects.create(
        screen=member.screen,
        household_member=member,
        type=income_type,
        amount=rate,
        frequency="hourly",
        hours_worked=hours,
    )
    member.has_income = True
    member.save(update_fields=["has_income"])
    return stream


class NjCcapTestCase(CustomCalculatorTestCase):
    calculator_class = NjCcap
    white_label_code = "nj"
    state_code = "NJ"
    fpl_year = "2026"
    default_zipcode = "07102"
    default_county = "Essex County"
    stores_age = False
    reference_date = date(2026, 11, 15)

    def worker(self, screen: Screen, age: int = 38, rate: int = 15, hours: int = 40) -> HouseholdMember:
        head = self.add_member(screen, "headOfHousehold", age)
        add_hourly(head, rate, hours)
        return head

    def full_time_student(self, screen: Screen, yearly_income: int = 0, age: int = 28) -> HouseholdMember:
        return self.add_member(
            screen, "headOfHousehold", age, yearly_income=yearly_income, student=True, student_full_time=True
        )

    def worker_with_child(self, child_age: float, parent_age: int = 29) -> Screen:
        screen = self.make_screen(household_size=2)
        self.worker(screen, age=parent_age)
        self.add_member(screen, "child", child_age)
        return screen

    def assert_eligible(self, screen: Screen, monthly: str) -> None:
        e = self.calculate(screen)
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, annual(monthly))

    def assert_ineligible(self, screen: Screen) -> None:
        e = self.calculate(screen)
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)


class TestClassAttributes(NjCcapTestCase):
    def test_registered_under_nj_ccap(self) -> None:
        self.assertIs(build("programs.programs", ProgramCalculator).get("nj_ccap"), NjCcap)

    def test_on_the_federal_base(self) -> None:
        self.assertTrue(issubclass(NjCcap, Ccdf))

    def test_paid_to_the_household(self) -> None:
        self.assertEqual(NjCcap.payment_unit, PaymentUnit.HOUSEHOLD)

    def test_does_not_read_the_college_student_answer(self) -> None:
        # NJ's school branch reads `student_full_time`, so a blank `student` must not drop it.
        self.assertNotIn("student", NjCcap.dependencies)
        self.assertEqual(set(NjCcap.dependencies), set(Ccdf.dependencies) - {"student"})

    def test_leaves_out_room_rent_and_cash_assistance(self) -> None:
        self.assertEqual(set(NjCcap.income_exclusions), {"boarder", "cashAssistance", "cashAssistanceOther"})


class TestSpecScenarios(NjCcapTestCase):
    def test_scenario_1_single_parent_working_35_hours_with_a_preschooler(self) -> None:
        screen = self.make_screen(household_size=2)
        self.worker(screen, age=30, rate=18, hours=35)
        self.add_member(screen, "child", 4)

        self.assert_eligible(screen, "1156.04")

    def test_scenario_2_child_aged_12(self) -> None:
        screen = self.make_screen(household_size=2)
        self.worker(screen)
        self.add_member(screen, "child", 12)

        self.assert_eligible(screen, "1089.14")

    def test_scenario_3_child_aged_13(self) -> None:
        screen = self.make_screen(household_size=2)
        self.worker(screen, age=40)
        self.add_member(screen, "child", 13)

        self.assert_ineligible(screen)

    def test_scenario_4_one_child_income_at_the_limit_for_two(self) -> None:
        screen = self.make_screen(household_size=2)
        self.full_time_student(screen, yearly_income=43_280)
        self.add_member(screen, "child", 6)

        self.assert_eligible(screen, "1049.27")

    def test_scenario_5_income_one_dollar_over_the_limit_for_two(self) -> None:
        screen = self.make_screen(household_size=2)
        self.full_time_student(screen, yearly_income=43_281)
        self.add_member(screen, "child", 6)

        self.assert_ineligible(screen)

    def test_scenario_6_two_children_income_at_the_limit_for_four(self) -> None:
        screen = self.make_screen(household_size=4)
        self.full_time_student(screen, yearly_income=66_000, age=35)
        self.add_member(screen, "spouse", 33)
        self.add_member(screen, "child", 8)
        self.add_member(screen, "child", 10)

        self.assert_eligible(screen, "2057.08")

    def test_scenario_7_income_one_dollar_over_the_limit_for_four(self) -> None:
        screen = self.make_screen(household_size=4)
        self.full_time_student(screen, yearly_income=66_001, age=35)
        self.add_member(screen, "spouse", 33)
        self.add_member(screen, "child", 8)
        self.add_member(screen, "child", 10)

        self.assert_ineligible(screen)

    def test_scenario_8_assets_at_the_limit(self) -> None:
        screen = self.make_screen(household_size=2, household_assets=1_000_000)
        self.worker(screen)
        self.add_member(screen, "child", 6)

        self.assert_eligible(screen, "1089.14")

    def test_scenario_9_assets_one_dollar_over(self) -> None:
        screen = self.make_screen(household_size=2, household_assets=1_000_001)
        self.worker(screen)
        self.add_member(screen, "child", 6)

        self.assert_ineligible(screen)

    def test_scenario_10_working_exactly_30_hours(self) -> None:
        screen = self.make_screen(household_size=2)
        self.worker(screen, hours=30)
        self.add_member(screen, "child", 6)

        self.assert_eligible(screen, "1115.24")

    def test_scenario_11_working_29_hours_and_nothing_else(self) -> None:
        screen = self.make_screen(household_size=2)
        self.worker(screen, hours=29)
        self.add_member(screen, "child", 6)

        self.assert_ineligible(screen)

    def test_scenario_12_full_time_student_with_no_income(self) -> None:
        screen = self.make_screen(household_size=2)
        self.full_time_student(screen, age=26)
        self.add_member(screen, "child", 6)

        self.assert_eligible(screen, "1193.54")

    def test_scenario_13_income_at_the_poverty_level_for_two(self) -> None:
        screen = self.make_screen(household_size=2)
        self.full_time_student(screen, yearly_income=21_640)
        self.add_member(screen, "child", 6)

        self.assert_eligible(screen, "1193.54")

    def test_scenario_14_income_one_dollar_over_the_poverty_level_for_two(self) -> None:
        screen = self.make_screen(household_size=2)
        self.full_time_student(screen, yearly_income=21_641)
        self.add_member(screen, "child", 6)

        self.assert_eligible(screen, "1121.40")

    def test_scenario_15_job_training_with_no_income(self) -> None:
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", 26, student_job_training_program=True)
        self.add_member(screen, "child", 6)

        self.assert_eligible(screen, "1193.54")

    def test_scenario_16_paid_a_salary_not_by_the_hour(self) -> None:
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", 38, yearly_income=30_000)
        self.add_member(screen, "child", 6)

        self.assert_eligible(screen, "1093.54")

    def test_scenario_17_part_time_work_plus_part_time_study(self) -> None:
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", 30, student=True, student_full_time=False)
        add_hourly(head, 15, 20)
        self.add_member(screen, "child", 6)

        self.assert_ineligible(screen)

    def test_scenario_18_two_parents_only_one_active(self) -> None:
        screen = self.make_screen(household_size=3)
        self.worker(screen, age=30)
        self.add_member(screen, "spouse", 29)
        self.add_member(screen, "child", 6)

        self.assert_eligible(screen, "1089.14")

    def test_scenario_19_infant(self) -> None:
        self.assert_eligible(self.worker_with_child(6 / 12), "1487.26")

    def test_scenario_20_toddler(self) -> None:
        self.assert_eligible(self.worker_with_child(24 / 12), "1313.14")

    def test_scenario_21_two_part_time_jobs_adding_up_to_30_hours(self) -> None:
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", 38)
        add_hourly(head, 15, 15)
        add_hourly(head, 15, 15)
        self.add_member(screen, "child", 6)

        self.assert_eligible(screen, "1115.24")

    def test_scenario_22_over_the_limit_only_because_of_cash_assistance(self) -> None:
        screen = self.make_screen(household_size=2)
        head = self.worker(screen)
        self.add_income(head, 1_500, "cashAssistance")
        self.add_member(screen, "child", 6)

        self.assert_eligible(screen, "1089.14")

    def test_scenario_23_seventeen_months_last_month_of_infant(self) -> None:
        self.assert_eligible(self.worker_with_child(17 / 12), "1487.26")

    def test_scenario_24_eighteen_months_first_month_of_toddler(self) -> None:
        self.assert_eligible(self.worker_with_child(18 / 12), "1313.14")

    def test_scenario_25_twenty_nine_months_last_month_of_toddler(self) -> None:
        self.assert_eligible(self.worker_with_child(29 / 12), "1313.14")

    def test_scenario_26_thirty_months_first_month_of_preschool(self) -> None:
        self.assert_eligible(self.worker_with_child(30 / 12), "1161.26")

    def test_scenario_27_age_5_takes_the_school_age_rate(self) -> None:
        self.assert_eligible(self.worker_with_child(5, parent_age=35), "1089.14")


class TestIncomeLimit(NjCcapTestCase):
    def test_matches_the_schedule_at_every_size(self) -> None:
        for size, (_, limit) in NJ_SCHEDULE.items():
            with self.subTest(size=size):
                calculator = self.make_calculator(self.make_screen(household_size=size))
                self.assertEqual(calculator.income_limit(), limit)

    def test_adds_11360_for_each_person_past_12(self) -> None:
        calculator = self.make_calculator(self.make_screen(household_size=14))

        self.assertEqual(calculator.income_limit(), 156_880 + 2 * 11_360)

    def test_leaves_out_room_rent_and_other_cash_assistance(self) -> None:
        for income_type in ("boarder", "cashAssistanceOther"):
            with self.subTest(income_type=income_type):
                screen = self.make_screen(household_size=2)
                head = self.worker(screen)
                self.add_income(head, 2_000, income_type)
                self.add_member(screen, "child", 6)

                self.assert_eligible(screen, "1089.14")

    def test_counts_other_unearned_income(self) -> None:
        screen = self.make_screen(household_size=2)
        head = self.worker(screen)
        self.add_income(head, 1_000, "sSI")
        self.add_member(screen, "child", 6)

        self.assert_ineligible(screen)


class TestParentActivity(NjCcapTestCase):
    def test_hourly_wages_and_self_employment_add_up(self) -> None:
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", 38)
        add_hourly(head, 15, 20)
        add_hourly(head, 15, 10, "selfEmployment")
        self.add_member(screen, "child", 6)

        self.assertTrue(self.calculate(screen).eligible)

    def test_self_employment_not_paid_by_the_hour(self) -> None:
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", 38, monthly_income=2_000, income_type="selfEmployment")
        self.add_member(screen, "child", 6)

        self.assertTrue(self.calculate(screen).eligible)

    def test_a_college_student_below_full_time_does_not_count(self) -> None:
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", 26, student=True, student_full_time=False)
        self.add_member(screen, "child", 6)

        self.assert_ineligible(screen)

    def test_unanswered_school_and_training_do_not_count(self) -> None:
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", 26, student_full_time=None, student_job_training_program=None)
        self.add_member(screen, "child", 6)

        self.assert_ineligible(screen)

    def test_hours_of_another_adult_do_not_add_to_the_heads(self) -> None:
        screen = self.make_screen(household_size=3)
        self.worker(screen, hours=20)
        roommate = self.add_member(screen, "roommate", 30)
        add_hourly(roommate, 15, 20)
        self.add_member(screen, "child", 6)

        self.assert_ineligible(screen)

    def test_the_heads_spouse_alone_can_meet_it(self) -> None:
        screen = self.make_screen(household_size=3)
        self.add_member(screen, "headOfHousehold", 30)
        spouse = self.add_member(screen, "spouse", 30)
        add_hourly(spouse, 15, 40)
        self.add_member(screen, "child", 6)

        self.assert_eligible(screen, "1089.14")


class TestCopay(NjCcapTestCase):
    def test_waiver_matches_the_schedule_at_every_size(self) -> None:
        for size, (poverty_level, _) in NJ_SCHEDULE.items():
            with self.subTest(size=size):
                calculator = self.make_calculator(self.make_screen(household_size=size))
                calculator.countable_income = lambda level=poverty_level: Decimal(level)
                self.assertEqual(calculator.family_copayment([None]), 0)

                calculator.countable_income = lambda level=poverty_level: Decimal(level + 1)
                self.assertEqual(calculator.family_copayment([None]), Decimal("0.04") * (poverty_level + 1) / 12)

    def test_waiver_is_tested_on_the_income_the_limit_counts(self) -> None:
        screen = self.make_screen(household_size=2)
        head = self.full_time_student(screen, yearly_income=21_640)
        self.add_income(head, 1_000, "cashAssistance")
        self.add_member(screen, "child", 6)

        self.assert_eligible(screen, "1193.54")

    def test_only_eligible_children_count_toward_the_two_child_rate(self) -> None:
        screen = self.make_screen(household_size=3)
        self.worker(screen)
        self.add_member(screen, "child", 6)
        self.add_member(screen, "child", 14)

        # One child under 13, so 4% of 31,320 a year, not 6%.
        self.assert_eligible(screen, "1089.14")

    def test_two_children_in_different_bands(self) -> None:
        screen = self.make_screen(household_size=3)
        self.worker(screen)
        self.add_member(screen, "child", 1)
        self.add_member(screen, "child", 6)

        # 1,591.66 + 1,193.54 - 6% of 31,320 / 12 = 2,785.20 - 156.60.
        self.assert_eligible(screen, "2628.60")

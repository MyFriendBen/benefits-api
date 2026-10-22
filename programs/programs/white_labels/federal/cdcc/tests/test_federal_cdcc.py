"""Federal CDCC scenarios, one per spec section 8 scenario, plus the code-level structure around
them.

Ages are the member's age today, so members are built from an age and the clock is left
alone: `add_member` derives the birth month against the same reference date the calculator
reads.

Section 4's `citizen_or_resident_alien` has no scenario: it is enforced by the program record
(`legal_status_required`), which the calculator never reads.
"""

from typing import Optional
from unittest.mock import patch

from programs.framework.base import Eligibility
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from programs.programs.white_labels.federal.cdcc.calculator import FederalCdcc
from screener.models import HouseholdMember, Screen

TAX_YEAR = 2026


class FederalCdccTestCase(CustomCalculatorTestCase):
    calculator_class = FederalCdcc
    white_label_code = "federal"
    state_code = ""
    fpl_year = str(TAX_YEAR)
    # The calculator reads age only through `calc_age()`.
    stores_age = False

    def member(
        self,
        screen: Screen,
        relationship: str,
        age: int,
        income: Optional[dict[str, int]] = None,
        **kwargs,
    ) -> HouseholdMember:
        """A member of `age` today, with yearly income by type."""
        member = self.add_member(screen, relationship, age=age, **kwargs)
        for income_type, amount in (income or {}).items():
            self.add_income(member, amount, income_type, "yearly")

        return member

    def care(self, member: HouseholdMember, monthly: int, expense_type: str = "childCare") -> None:
        self.add_expense(member, monthly, expense_type, "monthly")

    def assert_eligible(self, e: Eligibility, value: int) -> None:
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, value)

    def assert_ineligible(self, e: Eligibility) -> None:
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)


class TestRegistration(FederalCdccTestCase):
    def test_program_code_is_the_prefixed_federal_name(self):
        """The registry resolves a calculator by matching `program_code` to
        `Program.name_abbreviated`, so the federal row's prefixed name has to be here."""
        self.assertEqual(FederalCdcc.program_code, "federal_cdcc")

    def test_a_tax_year_with_no_parameters_uses_the_latest_and_reports_it(self):
        """A rollover the parameters weren't updated for must not raise: an exception from
        a displayed program fails the whole results page, in every white label."""
        screen = self.make_screen(household_size=2)
        head = self.member(screen, "headOfHousehold", 30, income={"wages": 24_000})
        self.member(screen, "child", 5)
        self.care(head, 300)
        calculator = self.make_calculator(screen)

        self.program.year.period = "2031"
        try:
            with patch("programs.programs.white_labels.federal.cdcc.calculator.capture_message") as report:
                e = calculator.calc()
        finally:
            self.program.year.period = self.fpl_year

        self.assert_eligible(e, 1_350)
        report.assert_called_once()
        self.assertIn("2031", report.call_args.args[0])

    def test_an_age_only_household_with_no_flags_is_still_priced(self):
        """The Colorado tax-credit apps send age alone, with no birth month and no disability
        or student answers. A null flag must read as false, not drop the program."""
        screen = self.make_screen(household_size=2)
        flags = dict(
            disabled=None,
            long_term_disability=None,
            visually_impaired=None,
            student=None,
            student_full_time=None,
        )
        head = self.member(screen, "headOfHousehold", None, income={"wages": 24_000}, **flags)
        child = self.member(screen, "child", None, **flags)
        for member, age in ((head, 30), (child, 5)):
            member.age = age
            member.birth_year_month = None
            member.save(update_fields=["age", "birth_year_month"])
        self.care(head, 300)

        self.assert_eligible(self.calculate(screen), 1_350)

    def test_a_household_with_no_head_is_ineligible(self):
        screen = self.make_screen(household_size=1)
        child = self.member(screen, "child", 5)
        self.care(child, 300)

        self.assert_ineligible(self.calculate(screen))


class TestScenarios(FederalCdccTestCase):
    def test_scenario_01_single_parent_clearing_every_rule(self):
        screen = self.make_screen(household_size=2)
        head = self.member(screen, "headOfHousehold", 30, income={"wages": 24_000})
        self.member(screen, "child", 5)
        self.care(head, 300)

        self.assert_eligible(self.calculate(screen), 1_350)

    def test_scenario_02_child_age_12_with_care_costs_below_the_dollar_limit(self):
        screen = self.make_screen(household_size=2)
        head = self.member(screen, "headOfHousehold", 30, income={"wages": 24_000})
        self.member(screen, "child", 12)
        self.care(head, 200)

        self.assert_eligible(self.calculate(screen), 1_080)

    def test_scenario_03_child_age_13_without_a_disability(self):
        screen = self.make_screen(household_size=2)
        head = self.member(screen, "headOfHousehold", 30, income={"wages": 24_000})
        self.member(screen, "child", 13)
        self.care(head, 300)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_04_disabled_child_age_15(self):
        screen = self.make_screen(household_size=2)
        head = self.member(screen, "headOfHousehold", 38, income={"wages": 36_000})
        self.member(screen, "child", 15, disabled=True)
        self.care(head, 300)

        self.assert_eligible(self.calculate(screen), 1_170)

    def test_scenario_05_disabled_spouse_as_the_qualifying_individual(self):
        screen = self.make_screen(household_size=2)
        head = self.member(screen, "headOfHousehold", 40, income={"wages": 30_000})
        self.member(screen, "spouse", 38, income={"wages": 12_000}, long_term_disability=True)
        self.care(head, 250, "dependentCare")

        self.assert_eligible(self.calculate(screen), 1_080)

    def test_scenario_06_spouse_without_a_disability_and_no_child(self):
        screen = self.make_screen(household_size=2)
        head = self.member(screen, "headOfHousehold", 40, income={"wages": 30_000})
        self.member(screen, "spouse", 38, income={"wages": 12_000})
        self.care(head, 250, "dependentCare")

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_07_unrelated_member_age_5(self):
        screen = self.make_screen(household_size=2)
        head = self.member(screen, "headOfHousehold", 30, income={"wages": 24_000})
        self.member(screen, "roommate", 5)
        self.care(head, 300)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_08_adult_parent_with_a_visual_impairment(self):
        screen = self.make_screen(household_size=2)
        head = self.member(screen, "headOfHousehold", 45, income={"wages": 30_000})
        self.member(screen, "parent", 70, visually_impaired=True)
        self.care(head, 250, "dependentCare")

        self.assert_eligible(self.calculate(screen), 1_260)

    def test_scenario_09_no_care_expenses(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 30, income={"wages": 24_000})
        self.member(screen, "child", 5)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_10_rent_but_no_care_expense(self):
        screen = self.make_screen(household_size=2)
        head = self.member(screen, "headOfHousehold", 30, income={"wages": 24_000})
        self.member(screen, "child", 5)
        self.add_expense(head, 800, "rent", "monthly")

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_11_pension_income_only(self):
        screen = self.make_screen(household_size=2)
        head = self.member(screen, "headOfHousehold", 55, income={"pension": 24_000})
        self.member(screen, "child", 5)
        self.care(head, 300)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_12_self_employment_income(self):
        screen = self.make_screen(household_size=2)
        head = self.member(screen, "headOfHousehold", 30, income={"selfEmployment": 27_000})
        self.member(screen, "child", 5)
        self.care(head, 300)

        self.assert_eligible(self.calculate(screen), 1_320)

    def test_scenario_13_spouse_is_a_full_time_student_with_no_earnings(self):
        screen = self.make_screen(household_size=3)
        head = self.member(screen, "headOfHousehold", 32, income={"wages": 40_000})
        self.member(screen, "spouse", 30, student=True, student_full_time=True)
        self.member(screen, "child", 5)
        self.care(head, 300)

        self.assert_eligible(self.calculate(screen), 1_110)

    def test_scenario_14_spouse_earns_less_than_the_dollar_limit(self):
        screen = self.make_screen(household_size=3)
        head = self.member(screen, "headOfHousehold", 35, income={"wages": 60_000})
        self.member(screen, "spouse", 34, income={"wages": 2_000})
        self.member(screen, "child", 5)
        self.care(head, 300)

        self.assert_eligible(self.calculate(screen), 700)

    def test_scenario_15_two_qualifying_children(self):
        screen = self.make_screen(household_size=3)
        head = self.member(screen, "headOfHousehold", 33, income={"wages": 30_000})
        self.member(screen, "child", 4)
        self.member(screen, "child", 7)
        self.care(head, 500)

        self.assert_eligible(self.calculate(screen), 2_520)

    def test_scenario_16_income_at_15_000(self):
        screen = self.make_screen(household_size=2)
        head = self.member(screen, "headOfHousehold", 30, income={"wages": 15_000})
        self.member(screen, "child", 5)
        self.care(head, 300)

        self.assert_eligible(self.calculate(screen), 1_500)

    def test_scenario_17_income_at_15_001(self):
        screen = self.make_screen(household_size=2)
        head = self.member(screen, "headOfHousehold", 30, income={"wages": 15_001})
        self.member(screen, "child", 5)
        self.care(head, 300)

        self.assert_eligible(self.calculate(screen), 1_470)

    def test_scenario_18_income_at_75_000(self):
        screen = self.make_screen(household_size=2)
        head = self.member(screen, "headOfHousehold", 30, income={"wages": 75_000})
        self.member(screen, "child", 5)
        self.care(head, 300)

        self.assert_eligible(self.calculate(screen), 1_050)

    def test_scenario_19_income_at_75_001(self):
        screen = self.make_screen(household_size=2)
        head = self.member(screen, "headOfHousehold", 30, income={"wages": 75_001})
        self.member(screen, "child", 5)
        self.care(head, 300)

        self.assert_eligible(self.calculate(screen), 1_020)

    def test_scenario_20_income_at_110_000(self):
        screen = self.make_screen(household_size=2)
        head = self.member(screen, "headOfHousehold", 30, income={"wages": 110_000})
        self.member(screen, "child", 5)
        self.care(head, 300)

        self.assert_eligible(self.calculate(screen), 600)

    def test_scenario_21_joint_income_at_100_000(self):
        screen = self.make_screen(household_size=3)
        head = self.member(screen, "headOfHousehold", 35, income={"wages": 60_000})
        self.member(screen, "spouse", 34, income={"wages": 40_000})
        self.member(screen, "child", 5)
        self.care(head, 300)

        self.assert_eligible(self.calculate(screen), 1_050)

    def test_scenario_22_joint_income_at_150_001(self):
        screen = self.make_screen(household_size=3)
        head = self.member(screen, "headOfHousehold", 38, income={"wages": 90_000})
        self.member(screen, "spouse", 37, income={"wages": 60_001})
        self.member(screen, "child", 5)
        self.care(head, 300)

        self.assert_eligible(self.calculate(screen), 1_020)

    def test_scenario_23_joint_income_at_206_001(self):
        screen = self.make_screen(household_size=3)
        head = self.member(screen, "headOfHousehold", 45, income={"wages": 120_000})
        self.member(screen, "spouse", 44, income={"wages": 86_001})
        self.member(screen, "child", 5)
        self.care(head, 300)

        self.assert_eligible(self.calculate(screen), 600)

    def test_scenario_24_joint_income_at_30_000(self):
        screen = self.make_screen(household_size=3)
        head = self.member(screen, "headOfHousehold", 38, income={"wages": 18_000})
        self.member(screen, "spouse", 36, income={"wages": 12_000})
        self.member(screen, "child", 5)
        self.care(head, 300)

        self.assert_eligible(self.calculate(screen), 1_260)

    def test_scenario_25_spouse_is_a_part_time_student_with_no_earnings(self):
        screen = self.make_screen(household_size=3)
        head = self.member(screen, "headOfHousehold", 32, income={"wages": 40_000})
        self.member(screen, "spouse", 30, student=True)
        self.member(screen, "child", 5)
        self.care(head, 300)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_26_disabled_spouse_with_no_earnings(self):
        screen = self.make_screen(household_size=2)
        head = self.member(screen, "headOfHousehold", 40, income={"wages": 30_000})
        self.member(screen, "spouse", 38, long_term_disability=True)
        self.care(head, 250, "dependentCare")

        self.assert_eligible(self.calculate(screen), 1_260)

    def test_scenario_27_single_filer_whose_low_wages_cap_the_credit(self):
        screen = self.make_screen(household_size=2)
        head = self.member(screen, "headOfHousehold", 30, income={"wages": 2_500})
        self.member(screen, "child", 5)
        self.care(head, 300)

        self.assert_eligible(self.calculate(screen), 1_250)

    def test_scenario_28_three_qualifying_children(self):
        screen = self.make_screen(household_size=4)
        head = self.member(screen, "headOfHousehold", 36, income={"wages": 60_000})
        for age in (3, 6, 9):
            self.member(screen, "child", age)
        self.care(head, 800)

        self.assert_eligible(self.calculate(screen), 2_100)

    def test_scenario_29_income_at_17_000(self):
        screen = self.make_screen(household_size=2)
        head = self.member(screen, "headOfHousehold", 30, income={"wages": 17_000})
        self.member(screen, "child", 5)
        self.care(head, 300)

        self.assert_eligible(self.calculate(screen), 1_470)

    def test_scenario_30_income_at_43_000(self):
        screen = self.make_screen(household_size=2)
        head = self.member(screen, "headOfHousehold", 30, income={"wages": 43_000})
        self.member(screen, "child", 5)
        self.care(head, 300)

        self.assert_eligible(self.calculate(screen), 1_080)

    def test_scenario_31_income_at_43_001(self):
        screen = self.make_screen(household_size=2)
        head = self.member(screen, "headOfHousehold", 30, income={"wages": 43_001})
        self.member(screen, "child", 5)
        self.care(head, 300)

        self.assert_eligible(self.calculate(screen), 1_050)

    def test_scenario_32_income_at_103_000(self):
        screen = self.make_screen(household_size=2)
        head = self.member(screen, "headOfHousehold", 30, income={"wages": 103_000})
        self.member(screen, "child", 5)
        self.care(head, 300)

        self.assert_eligible(self.calculate(screen), 630)

    def test_scenario_33_joint_income_at_156_000(self):
        screen = self.make_screen(household_size=3)
        head = self.member(screen, "headOfHousehold", 38, income={"wages": 96_000})
        self.member(screen, "spouse", 37, income={"wages": 60_000})
        self.member(screen, "child", 5)
        self.care(head, 300)

        self.assert_eligible(self.calculate(screen), 990)

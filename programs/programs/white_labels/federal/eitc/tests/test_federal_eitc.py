"""Federal EITC scenarios, one per spec §8, plus the EIC Table itself.

Every age in the spec is the member's age at the end of the 2025 tax year, so members are
built from a birth month and the clock is pinned: an age derived from today would put a
boundary member on the wrong side of it as the calendar moves.

§4's `citizen_or_resident_alien` has no scenario: it is `Enforced by: program-record`
(`legal_status_required`), which the calculator never reads.
"""

import csv
from datetime import date
from pathlib import Path
from typing import Optional
from unittest.mock import patch

from programs.framework.base import HOUSEHOLD, Eligibility
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from programs.programs.white_labels.federal.eitc.calculator import EITC_YEARS, FederalEitc, eic_table
from screener.models import HouseholdMember, Screen

TAX_YEAR = 2025


class FederalEitcTestCase(CustomCalculatorTestCase):
    calculator_class = FederalEitc
    white_label_code = "federal"
    state_code = ""
    fpl_year = str(TAX_YEAR)
    reference_date = date(2026, 3, 15)
    # The calculator reads age only through `calc_age()` and `age_at_end_of_year()`.
    stores_age = False

    def member(
        self,
        screen: Screen,
        relationship: str,
        age: int,
        month: int = 6,
        income: Optional[dict[str, int]] = None,
        **kwargs,
    ) -> HouseholdMember:
        """A member `age` at the end of the tax year, with yearly income by type."""
        member = self.add_member(
            screen, relationship, age=None, birth_year_month=date(TAX_YEAR - age, month, 1), **kwargs
        )
        for income_type, amount in (income or {}).items():
            self.add_income(member, amount, income_type, "yearly")

        return member

    def assert_eligible(self, e: Eligibility, value: int) -> None:
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, value)

    def assert_ineligible(self, e: Eligibility) -> None:
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)


class TestRegistration(FederalEitcTestCase):
    def test_program_code_is_the_prefixed_federal_name(self):
        """The registry resolves a calculator by matching `program_code` to
        `Program.name_abbreviated`, so the federal row's prefixed name has to be here."""
        self.assertEqual(FederalEitc.program_code, "federal_eitc")

    def test_the_credit_is_paid_to_the_household(self):
        """A qualifying child sizes the credit, but the filers claim it, so the results
        show the household as eligible rather than every member."""
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 41, income={"wages": 20_000})
        self.member(screen, "child", 8)

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.payment_unit, HOUSEHOLD)
        self.assertEqual([m.value for m in e.eligible_members], [0, 0])

    def test_a_tax_year_with_no_parameters_uses_the_latest_and_reports_it(self):
        """A rollover the parameters weren't updated for must not raise: an exception from
        a displayed program fails the whole results page, in every white label."""
        screen = self.make_screen(household_size=1)
        self.member(screen, "headOfHousehold", 30, income={"wages": 9_000})
        calculator = self.make_calculator(screen)

        self.program.year.period = "2026"
        try:
            with patch("programs.programs.white_labels.federal.eitc.calculator.capture_message") as report:
                e = calculator.calc()
        finally:
            self.program.year.period = self.fpl_year

        self.assert_eligible(e, 649)
        report.assert_called_once()
        self.assertIn("2026", report.call_args.args[0])


class TestEicTable(FederalEitcTestCase):
    """`eic_table` against every row of the 2025 EIC Table (Instructions for Form 1040
    (2025)), parsed into `eic_table_2025.csv`. Starred cells are the footnoted ranges at the
    foot of a column, checked separately below."""

    # (column's first footnoted dollar, children, joint, credit) from the table's footnotes.
    footnotes = [
        (19_100, 0, False, 0),
        (26_200, 0, True, 1),
        (50_400, 1, False, 3),
        (57_300, 2, False, 1),
        (57_550, 1, True, 0),
        (61_550, 3, False, 1),
        (64_400, 2, True, 3),
        (68_650, 3, True, 3),
    ]

    def test_every_row(self):
        columns = EITC_YEARS[TAX_YEAR].columns
        with open(Path(__file__).parent / "eic_table_2025.csv") as table:
            rows = list(csv.DictReader(table))

        self.assertEqual(len(rows), 1_374)
        for row in rows:
            low, high = int(row["at_least"]), int(row["less_than"])
            for joint in (False, True):
                for n in range(4):
                    expected = row[f"{'joint' if joint else 'single'}_{n}"]
                    if "*" in expected:
                        continue
                    for amount in (low, (low + high) // 2, high - 1, high - 0.01):
                        with self.subTest(amount=amount, n=n, joint=joint):
                            self.assertEqual(eic_table(amount, columns[(n, joint)]), int(expected))

    def test_footnoted_ranges(self):
        columns = EITC_YEARS[TAX_YEAR].columns
        for low, n, joint, credit in self.footnotes:
            column = columns[(n, joint)]
            with self.subTest(n=n, joint=joint):
                self.assertEqual(eic_table(low, column), credit)
                self.assertEqual(eic_table(column.limit - 1, column), credit)
                self.assertEqual(eic_table(column.limit, column), 0)

    def test_no_amount_has_no_credit(self):
        self.assertEqual(eic_table(0, EITC_YEARS[TAX_YEAR].columns[(1, False)]), 0)


class TestScenarios(FederalEitcTestCase):
    def test_scenario_01_single_parent_with_one_young_child(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 30, income={"wages": 20_000})
        self.member(screen, "child", 8)

        self.assert_eligible(self.calculate(screen), 4_328)

    def test_scenario_02_two_qualifying_children(self):
        screen = self.make_screen(household_size=3)
        self.member(screen, "headOfHousehold", 34, income={"wages": 20_000})
        self.member(screen, "child", 8)
        self.member(screen, "child", 5)

        self.assert_eligible(self.calculate(screen), 7_152)

    def test_scenario_03_four_qualifying_children(self):
        screen = self.make_screen(household_size=5)
        self.member(screen, "headOfHousehold", 38, income={"wages": 20_000})
        for age in (12, 9, 6, 3):
            self.member(screen, "child", age)

        self.assert_eligible(self.calculate(screen), 8_046)

    def test_scenario_04_married_couple_one_child_below_the_joint_phase_out_start(self):
        screen = self.make_screen(household_size=3)
        self.member(screen, "headOfHousehold", 33, income={"wages": 28_000})
        self.member(screen, "spouse", 31)
        self.member(screen, "child", 4)

        self.assert_eligible(self.calculate(screen), 4_328)

    def test_scenario_05_single_parent_one_child_in_the_phase_out(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 33, income={"wages": 28_000})
        self.member(screen, "child", 4)

        self.assert_eligible(self.calculate(screen), 3_581)

    def test_scenario_06_earnings_in_the_phase_in(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 27, income={"wages": 5_000})
        self.member(screen, "child", 2)

        self.assert_eligible(self.calculate(screen), 1_709)

    def test_scenario_07_agi_above_earned_income(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 36, income={"wages": 20_000, "unemployment": 15_000})
        self.member(screen, "child", 7)

        self.assert_eligible(self.calculate(screen), 2_462)

    def test_scenario_08_agi_one_dollar_under_the_one_child_limit(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 41, income={"wages": 40_000, "unemployment": 10_433})
        self.member(screen, "child", 10)

        self.assert_eligible(self.calculate(screen), 3)

    def test_scenario_09_agi_at_the_one_child_limit(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 41, income={"wages": 40_000, "unemployment": 10_434})
        self.member(screen, "child", 10)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_10_agi_one_dollar_under_the_two_child_limit(self):
        screen = self.make_screen(household_size=3)
        self.member(screen, "headOfHousehold", 39, income={"wages": 45_000, "unemployment": 12_309})
        self.member(screen, "child", 11)
        self.member(screen, "child", 7)

        self.assert_eligible(self.calculate(screen), 1)

    def test_scenario_11_agi_at_the_two_child_limit(self):
        screen = self.make_screen(household_size=3)
        self.member(screen, "headOfHousehold", 39, income={"wages": 45_000, "unemployment": 12_310})
        self.member(screen, "child", 11)
        self.member(screen, "child", 7)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_12_child_support_left_out_of_agi(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 37, income={"wages": 40_000, "childSupport": 12_000})
        self.member(screen, "child", 9)

        self.assert_eligible(self.calculate(screen), 1_663)

    def test_scenario_13_investment_income_at_the_limit(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 45, income={"wages": 20_000, "investment": 11_950})
        self.member(screen, "child", 13)

        self.assert_eligible(self.calculate(screen), 2_950)

    def test_scenario_14_investment_income_one_dollar_over_the_limit(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 45, income={"wages": 20_000, "investment": 11_951})
        self.member(screen, "child", 13)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_15_rental_income_over_the_limit(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 52, income={"wages": 20_000, "rental": 12_000})
        self.member(screen, "child", 14)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_16_no_earned_income(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 35, income={"unemployment": 15_000})
        self.member(screen, "child", 6)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_17_no_child_filer_25(self):
        screen = self.make_screen(household_size=1)
        self.member(screen, "headOfHousehold", 25, income={"wages": 9_000})

        self.assert_eligible(self.calculate(screen), 649)

    def test_scenario_18_no_child_filer_24(self):
        screen = self.make_screen(household_size=1)
        self.member(screen, "headOfHousehold", 24, income={"wages": 9_000})

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_19_no_child_filer_64(self):
        screen = self.make_screen(household_size=1)
        self.member(screen, "headOfHousehold", 64, income={"wages": 9_000})

        self.assert_eligible(self.calculate(screen), 649)

    def test_scenario_20_no_child_filer_65(self):
        screen = self.make_screen(household_size=1)
        self.member(screen, "headOfHousehold", 65, income={"wages": 9_000})

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_21_married_no_child_only_the_spouse_in_the_age_range(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 66, income={"wages": 15_000})
        self.member(screen, "spouse", 60)

        self.assert_eligible(self.calculate(screen), 649)

    def test_scenario_22_parent_under_25_with_a_child(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 22, income={"wages": 20_000})
        self.member(screen, "child", 3)

        self.assert_eligible(self.calculate(screen), 4_328)

    def test_scenario_23_child_18(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 45, income={"wages": 20_000})
        self.member(screen, "child", 18)

        self.assert_eligible(self.calculate(screen), 4_328)

    def test_scenario_24_child_19_not_a_student(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 45, income={"wages": 15_000})
        self.member(screen, "child", 19)

        self.assert_eligible(self.calculate(screen), 312)

    def test_scenario_25_full_time_student_23(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 50, income={"wages": 20_000})
        self.member(screen, "child", 23, student=True, student_full_time=True)

        self.assert_eligible(self.calculate(screen), 4_328)

    def test_scenario_26_full_time_student_24(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 50, income={"wages": 15_000})
        self.member(screen, "child", 24, student=True, student_full_time=True)

        self.assert_eligible(self.calculate(screen), 312)

    def test_scenario_27_disabled_adult_child(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 58, income={"wages": 20_000})
        self.member(screen, "child", 30, disabled=True)

        self.assert_eligible(self.calculate(screen), 4_328)

    def test_scenario_28_sibling_older_than_the_filer(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 21, income={"wages": 15_000})
        self.member(screen, "sisterOrBrother", 22, student=True, student_full_time=True)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_29_roommates_child(self):
        screen = self.make_screen(household_size=3)
        self.member(screen, "headOfHousehold", 29, income={"wages": 15_000})
        self.member(screen, "roommate", 27)
        self.member(screen, "roommate", 6)

        self.assert_eligible(self.calculate(screen), 312)

    def test_scenario_30_married_couple_spouses_wages_put_them_over_the_limit(self):
        screen = self.make_screen(household_size=3)
        self.member(screen, "headOfHousehold", 35, income={"wages": 20_000})
        self.member(screen, "spouse", 34, income={"wages": 40_000})
        self.member(screen, "child", 6)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_31_single_parent_living_with_a_working_roommate(self):
        screen = self.make_screen(household_size=3)
        self.member(screen, "headOfHousehold", 32, income={"wages": 20_000})
        self.member(screen, "child", 5)
        self.member(screen, "roommate", 40, income={"wages": 40_000})

        self.assert_eligible(self.calculate(screen), 4_328)

    def test_scenario_32_child_older_than_one_spouse_younger_than_the_other(self):
        screen = self.make_screen(household_size=3)
        self.member(screen, "headOfHousehold", 20, income={"wages": 20_000})
        self.member(screen, "spouse", 30)
        self.member(screen, "sisterOrBrother", 22, student=True, student_full_time=True)

        self.assert_eligible(self.calculate(screen), 4_328)

    def test_scenario_33_no_child_earnings_just_under_the_limit(self):
        screen = self.make_screen(household_size=1)
        self.member(screen, "headOfHousehold", 30, income={"wages": 19_101})

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_34_married_one_child_earnings_just_under_the_joint_limit(self):
        screen = self.make_screen(household_size=3)
        self.member(screen, "headOfHousehold", 40, income={"wages": 57_551})
        self.member(screen, "spouse", 38)
        self.member(screen, "child", 10)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_35_child_recorded_as_another_relative(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 40, income={"wages": 15_000})
        self.member(screen, "relatedOther", 8)

        self.assert_eligible(self.calculate(screen), 312)

    def test_scenario_36_child_born_later_in_the_filers_birth_year(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 22, month=3, income={"wages": 20_000})
        self.member(screen, "sisterOrBrother", 22, month=9, student=True, student_full_time=True)

        self.assert_eligible(self.calculate(screen), 4_328)

    def test_scenario_37_child_born_in_the_filers_birth_month(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 22, month=3, income={"wages": 15_000})
        self.member(screen, "sisterOrBrother", 22, month=3, student=True, student_full_time=True)

        self.assert_ineligible(self.calculate(screen))

    def test_a_child_born_after_the_tax_year_is_not_counted(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 30, income={"wages": 9_000})
        self.member(screen, "child", -1, month=2)

        self.assert_eligible(self.calculate(screen), 649)

    def test_a_disabled_child_born_after_the_tax_year_is_not_counted(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 22, income={"wages": 20_000})
        self.member(screen, "child", -1, month=2, disabled=True)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_38_agi_past_the_phase_out_start_earned_income_gives_the_smaller_amount(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 31, income={"wages": 3_000, "unemployment": 22_000})
        self.member(screen, "child", 6)

        self.assert_eligible(self.calculate(screen), 1_029)

    def test_scenario_39_single_parent_with_wages_and_social_security_retirement(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 63, income={"wages": 20_000, "sSRetirement": 10_000})
        self.member(screen, "child", 12)

        self.assert_eligible(self.calculate(screen), 4_328)

    def test_scenario_40_no_child_agi_in_the_tables_zero_band_earnings_below_it(self):
        screen = self.make_screen(household_size=1)
        self.member(screen, "headOfHousehold", 30, income={"wages": 18_000, "unemployment": 1_101})

        self.assert_eligible(self.calculate(screen), 0)


class TestAgeOnlyHouseholds(FederalEitcTestCase):
    """The Colorado tax-credit apps send `age` with no birth month, and no disability or
    student answers."""

    def test_a_child_is_counted_by_age(self):
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", age=30, stored_age=True, screener_defaults=False)
        self.add_member(screen, "child", age=8, stored_age=True, screener_defaults=False)
        self.add_income(head, 20_000, "wages", "yearly")

        self.assert_eligible(self.calculate(screen), 4_328)

"""Federal CTC scenarios, one per spec section 8, plus the tax computation and the structural rules.

Every age in the spec is the member's age at the end of the 2025 tax year, so members are
built from a birth month and the clock is pinned: an age derived from today would put a
boundary member on the wrong side of it as the calendar moves. Members built in the same
year share a birth month, so two members of the same age are not younger than each other.

Section 4's `child_citizenship` and `odc_citizenship` have no scenario: they are `Enforced by:
program-record` (`legal_status_required`), which the calculator never reads.
"""

from datetime import date
from decimal import Decimal
from typing import Optional
from unittest.mock import patch

from programs.framework.base import Eligibility
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from programs.programs.white_labels.federal.ctc.calculator import (
    CTC_YEARS,
    HEAD_OF_HOUSEHOLD,
    JOINT,
    SINGLE,
    FederalCtc,
    income_tax,
)
from screener.models import HouseholdMember, Screen

TAX_YEAR = 2025


class FederalCtcTestCase(CustomCalculatorTestCase):
    calculator_class = FederalCtc
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

    def assert_eligible(self, e: Eligibility, value: float) -> None:
        self.assertTrue(e.eligible)
        self.assertAlmostEqual(e.value, value, places=2)

    def assert_ineligible(self, e: Eligibility) -> None:
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)


class TestRegistration(FederalCtcTestCase):
    def test_program_code_is_the_prefixed_federal_name(self):
        """The registry resolves a calculator by matching `program_code` to
        `Program.name_abbreviated`, so the federal row's prefixed name has to be here."""
        self.assertEqual(FederalCtc.program_code, "federal_ctc")

    def test_dependencies_are_what_the_tax_credit_apps_send(self):
        """The Colorado tax-credit apps send age, relationship and income only; requiring a
        disability or student answer would drop the program from their results."""
        self.assertEqual(
            sorted(FederalCtc.dependencies), ["age", "income_amount", "income_frequency", "income_type", "relationship"]
        )

    def test_a_tax_year_with_no_parameters_uses_the_latest_and_reports_it(self):
        """A rollover the parameters weren't updated for must not raise: an exception from
        a displayed program fails the whole results page, in every white label."""
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 41, income={"wages": 40_000})
        self.member(screen, "child", 8)
        calculator = self.make_calculator(screen)

        self.program.year.period = "2026"
        try:
            with patch("programs.programs.white_labels.federal.ctc.calculator.capture_message") as report:
                e = calculator.calc()
        finally:
            self.program.year.period = self.fpl_year

        self.assert_eligible(e, 2_200)
        report.assert_called_once()
        self.assertIn("2026", report.call_args.args[0])


class TestIncomeTax(FederalCtcTestCase):
    """`income_tax` against published rows of the 2025 Tax Table and the Tax Computation Worksheet."""

    brackets = CTC_YEARS[TAX_YEAR].tax_brackets

    def test_tax_table_rows_are_priced_at_the_midpoint(self):
        # (taxable income, single, joint, head of household) from the published table.
        rows = [
            (0, 0, 0, 0),
            (10, 1, 1, 1),
            (20, 2, 2, 2),
            (37, 4, 4, 4),
            (1_060, 106, 106, 106),
            (3_025, 303, 303, 303),
            (16_375, 1_727, 1_638, 1_638),
            (99_975, 16_909, 11_823, 15_170),
        ]
        for amount, single, joint, head in rows:
            with self.subTest(amount=amount):
                self.assertEqual(income_tax(Decimal(amount), self.brackets[SINGLE]), single)
                self.assertEqual(income_tax(Decimal(amount), self.brackets[JOINT]), joint)
                self.assertEqual(income_tax(Decimal(amount), self.brackets[HEAD_OF_HOUSEHOLD]), head)

    def test_tax_computation_worksheet_from_100_000(self):
        # Section A, B and D rows: the rate times income less the worksheet's subtraction.
        self.assertEqual(income_tax(Decimal(100_000), self.brackets[SINGLE]), Decimal("16914.00"))
        self.assertEqual(income_tax(Decimal(100_000), self.brackets[JOINT]), Decimal("11828.00"))
        self.assertEqual(income_tax(Decimal(100_000), self.brackets[HEAD_OF_HOUSEHOLD]), Decimal("15175.00"))
        self.assertEqual(income_tax(Decimal(300_000), self.brackets[SINGLE]), Decimal("74547.25"))
        self.assertEqual(income_tax(Decimal(800_000), self.brackets[JOINT]), Decimal("220062.50"))

    def test_no_taxable_income_has_no_tax(self):
        self.assertEqual(income_tax(Decimal(-500), self.brackets[SINGLE]), 0)


class TestScenarios(FederalCtcTestCase):
    def test_scenario_01_married_couple_with_two_young_children(self):
        screen = self.make_screen(household_size=4)
        self.member(screen, "headOfHousehold", 38, income={"wages": 60_000})
        self.member(screen, "spouse", 36)
        self.member(screen, "child", 12)
        self.member(screen, "child", 8)

        self.assert_eligible(self.calculate(screen), 4_400)

    def test_scenario_02_child_at_the_age_limit(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 41, income={"wages": 40_000})
        self.member(screen, "child", 16)

        self.assert_eligible(self.calculate(screen), 2_200)

    def test_scenario_03_child_one_year_past_the_age_limit(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 44, income={"wages": 40_000})
        self.member(screen, "child", 17)

        self.assert_eligible(self.calculate(screen), 500)

    def test_scenario_04_housemates_child(self):
        screen = self.make_screen(household_size=3)
        self.member(screen, "headOfHousehold", 29, income={"wages": 45_000})
        self.member(screen, "roommate", 27, income={"wages": 30_000})
        self.member(screen, "roommate", 6)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_05_grandparent_claiming_a_grandchild_and_an_adult_child(self):
        screen = self.make_screen(household_size=3)
        self.member(screen, "headOfHousehold", 52, income={"wages": 55_000})
        self.member(screen, "child", 18)
        self.member(screen, "grandChild", 1)

        self.assert_eligible(self.calculate(screen), 2_700)

    def test_scenario_06_child_older_than_the_filer(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 16, income={"wages": 14_000})
        self.member(screen, "sisterOrBrother", 16)

        self.assert_eligible(self.calculate(screen), 0)

    def test_scenario_07_disabled_child_the_same_age_as_the_filer(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 16, income={"wages": 14_000})
        self.member(screen, "sisterOrBrother", 16, disabled=True, long_term_disability=True)

        self.assert_eligible(self.calculate(screen), 1_700)

    def test_scenario_08_joint_filer_exactly_at_the_phase_out_threshold(self):
        screen = self.make_screen(household_size=4)
        self.member(screen, "headOfHousehold", 45, income={"wages": 400_000})
        self.member(screen, "spouse", 43)
        self.member(screen, "child", 10)
        self.member(screen, "child", 7)

        self.assert_eligible(self.calculate(screen), 4_400)

    def test_scenario_09_joint_filer_into_the_phase_out(self):
        screen = self.make_screen(household_size=4)
        self.member(screen, "headOfHousehold", 45, income={"wages": 430_000})
        self.member(screen, "spouse", 43)
        self.member(screen, "child", 10)
        self.member(screen, "child", 7)

        self.assert_eligible(self.calculate(screen), 2_900)

    def test_scenario_10_single_filer_into_the_phase_out(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 39, income={"wages": 205_000})
        self.member(screen, "child", 11)

        self.assert_eligible(self.calculate(screen), 1_950)

    def test_scenario_11_earnings_at_the_refundable_credits_floor(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 31, income={"wages": 2_500})
        self.member(screen, "child", 5)

        self.assert_eligible(self.calculate(screen), 0)

    def test_scenario_12_three_children_on_low_earnings(self):
        screen = self.make_screen(household_size=4)
        self.member(screen, "headOfHousehold", 34, income={"wages": 20_000})
        self.member(screen, "child", 11)
        self.member(screen, "child", 8)
        self.member(screen, "child", 4)

        self.assert_eligible(self.calculate(screen), 2_625)

    def test_scenario_13_child_and_a_supported_parent(self):
        screen = self.make_screen(household_size=3)
        self.member(screen, "headOfHousehold", 48, income={"wages": 52_000})
        self.member(screen, "child", 13)
        self.member(screen, "parent", 74)

        self.assert_eligible(self.calculate(screen), 2_700)

    def test_scenario_14_child_earning_exactly_half_the_households_income(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 40, income={"wages": 40_000})
        self.member(screen, "child", 16, income={"wages": 40_000})

        self.assert_eligible(self.calculate(screen), 2_200)

    def test_scenario_15_child_earning_a_dollar_over_half_the_households_income(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 40, income={"wages": 40_000})
        self.member(screen, "child", 16, income={"wages": 40_001})

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_16_child_one_year_younger_than_the_filer(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 17, income={"wages": 14_000})
        self.member(screen, "sisterOrBrother", 16)

        self.assert_eligible(self.calculate(screen), 1_700)

    def test_scenario_17_child_younger_than_the_spouse_but_not_the_filer(self):
        screen = self.make_screen(household_size=3)
        self.member(screen, "headOfHousehold", 16, income={"wages": 14_000})
        self.member(screen, "spouse", 17)
        self.member(screen, "sisterOrBrother", 16)

        self.assert_eligible(self.calculate(screen), 1_700)

    def test_scenario_18_parent_just_under_the_income_limit(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 48, income={"wages": 52_000})
        self.member(screen, "parent", 74, income={"wages": 5_199})

        self.assert_eligible(self.calculate(screen), 500)

    def test_scenario_19_parent_at_the_income_limit(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 48, income={"wages": 52_000})
        self.member(screen, "parent", 74, income={"wages": 5_200})

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_20_single_filer_one_dollar_over_the_phase_out_threshold(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 39, income={"wages": 200_001})
        self.member(screen, "child", 11)

        self.assert_eligible(self.calculate(screen), 2_150)

    def test_scenario_21_earnings_just_above_the_refundable_credits_floor(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 31, income={"wages": 2_600})
        self.member(screen, "child", 5)

        self.assert_eligible(self.calculate(screen), 15)

    def test_scenario_22_an_other_dependent_and_no_tax(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 48, income={"wages": 20_000})
        self.member(screen, "parent", 74)

        self.assert_eligible(self.calculate(screen), 0)

    def test_scenario_23_single_filer_one_dollar_past_full_phase_out(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 39, income={"wages": 244_001})
        self.member(screen, "child", 11)

        self.assert_eligible(self.calculate(screen), 0)

    def test_scenario_24_eighteen_year_old_with_earnings(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 45, income={"wages": 40_000})
        self.member(screen, "child", 18, income={"wages": 5_200})

        self.assert_eligible(self.calculate(screen), 500)

    def test_scenario_25_nineteen_year_old_non_student_with_earnings(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 45, income={"wages": 40_000})
        self.member(screen, "child", 19, income={"wages": 5_200})

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_26_earnings_one_dollar_over_the_refundable_credits_floor(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 31, income={"wages": 2_501})
        self.member(screen, "child", 5)

        self.assert_eligible(self.calculate(screen), 0.15)


class TestStructure(FederalCtcTestCase):
    """Rules the spec states in sections 4 and 7 but no scenario reaches."""

    def test_the_credit_is_capped_at_tax_plus_the_refundable_part(self):
        """Two other dependents and no qualifying child: the $1,000 is nonrefundable, so only
        the $638 of income tax on $30,000 as head of household ($6,375 taxable) is paid."""
        screen = self.make_screen(household_size=3)
        self.member(screen, "headOfHousehold", 48, income={"wages": 30_000})
        self.member(screen, "child", 17)
        self.member(screen, "parent", 74)

        self.assert_eligible(self.calculate(screen), 638)

    def test_a_senior_filer_gets_the_higher_standard_deduction(self):
        """At 65 the head of household deduction is $25,625, so $26,000 leaves $375 taxable:
        $39 of tax and no qualifying child, so the $500 other-dependent credit pays $39."""
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 65, income={"wages": 26_000})
        self.member(screen, "parent", 90)

        self.assert_eligible(self.calculate(screen), 39)

    def test_a_student_child_under_24_is_an_other_dependent(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 50, income={"wages": 40_000})
        self.member(screen, "child", 22, student=True, income={"wages": 6_000})

        self.assert_eligible(self.calculate(screen), 500)

    def test_a_partner_is_never_a_dependent(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 30, income={"wages": 40_000})
        self.member(screen, "domesticPartner", 28)

        self.assert_ineligible(self.calculate(screen))

    def test_a_relatives_ssi_is_left_out_of_their_gross_income(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 48, income={"wages": 52_000})
        self.member(screen, "parent", 74, income={"sSI": 11_000})

        self.assert_eligible(self.calculate(screen), 500)

    def test_only_the_filers_income_counts(self):
        """A roommate's wages are off the return, so they neither taper the credit nor add tax."""
        screen = self.make_screen(household_size=3)
        self.member(screen, "headOfHousehold", 31, income={"wages": 2_600})
        self.member(screen, "child", 5)
        self.member(screen, "roommate", 40, income={"wages": 300_000})

        self.assert_eligible(self.calculate(screen), 15)


class TestAgeOnlyHouseholds(FederalCtcTestCase):
    """The Colorado tax-credit apps send `age` with no birth month, and no disability or
    student answers."""

    def test_a_child_is_counted_by_age(self):
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", age=45, stored_age=True, screener_defaults=False)
        self.add_member(screen, "child", age=8, stored_age=True, screener_defaults=False)
        self.add_income(head, 40_000, "wages", "yearly")

        self.assert_eligible(self.calculate(screen), 2_200)

    def test_a_child_the_filers_age_is_an_other_dependent(self):
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", age=16, stored_age=True, screener_defaults=False)
        self.add_member(screen, "sisterOrBrother", age=16, stored_age=True, screener_defaults=False)
        self.add_income(head, 14_000, "wages", "yearly")

        self.assert_eligible(self.calculate(screen), 0)

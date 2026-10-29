"""Federal CTC scenarios, one per spec section 8, plus the tax computation and the code-level rules.

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

    def test_scenario_14_child_earning_exactly_as_much_as_the_rest_of_the_household(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 40, income={"wages": 40_000})
        self.member(screen, "child", 16, income={"wages": 40_000})

        self.assert_eligible(self.calculate(screen), 2_200)

    def test_scenario_15_child_earning_a_dollar_more_than_the_rest_of_the_household(self):
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

    def test_scenario_21_an_other_dependent_and_no_tax(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 48, income={"wages": 20_000})
        self.member(screen, "parent", 74)

        self.assert_eligible(self.calculate(screen), 0)

    def test_scenario_22_single_filer_one_dollar_past_full_phase_out(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 39, income={"wages": 244_001})
        self.member(screen, "child", 11)

        self.assert_eligible(self.calculate(screen), 0)

    def test_scenario_23_eighteen_year_old_with_earnings(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 45, income={"wages": 40_000})
        self.member(screen, "child", 18, income={"wages": 5_200})

        self.assert_eligible(self.calculate(screen), 500)

    def test_scenario_24_nineteen_year_old_non_student_with_earnings(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 45, income={"wages": 40_000})
        self.member(screen, "child", 19, income={"wages": 5_200})

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_25_earnings_one_dollar_over_the_refundable_credits_floor(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 31, income={"wages": 2_501})
        self.member(screen, "child", 5)

        self.assert_eligible(self.calculate(screen), 0.15)

    def test_scenario_26_joint_filers_with_child_support_near_the_phase_out(self):
        screen = self.make_screen(household_size=4)
        self.member(screen, "headOfHousehold", 45, income={"wages": 395_000, "childSupport": 10_000})
        self.member(screen, "spouse", 43)
        self.member(screen, "child", 10)
        self.member(screen, "child", 7)

        self.assert_eligible(self.calculate(screen), 4_400)

    def test_scenario_27_supported_parent_living_on_social_security(self):
        screen = self.make_screen(household_size=3)
        self.member(screen, "headOfHousehold", 48, income={"wages": 52_000})
        self.member(screen, "child", 13)
        self.member(screen, "parent", 74, income={"sSRetirement": 14_000})

        self.assert_eligible(self.calculate(screen), 2_700)

    def test_scenario_28_joint_filers_whose_social_security_would_tip_the_phase_out(self):
        screen = self.make_screen(household_size=4)
        self.member(screen, "headOfHousehold", 45, income={"wages": 395_000, "sSRetirement": 10_000})
        self.member(screen, "spouse", 43)
        self.member(screen, "child", 10)
        self.member(screen, "child", 7)

        self.assert_eligible(self.calculate(screen), 4_400)

    def test_scenario_29_low_wage_head_on_social_security_disability_where_the_tax_cap_binds(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 40, income={"wages": 20_000, "sSDisability": 18_000})
        self.member(screen, "child", 8)

        self.assert_eligible(self.calculate(screen), 1_700)

    def test_scenario_30_filer_who_is_65_and_blind_claiming_a_parent(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 70, visually_impaired=True, income={"wages": 30_000})
        self.member(screen, "parent", 92)

        self.assert_eligible(self.calculate(screen), 239)

    def test_scenario_31_student_child_under_24_with_earnings(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 50, income={"wages": 40_000})
        self.member(screen, "child", 22, student=True, income={"wages": 6_000})

        self.assert_eligible(self.calculate(screen), 500)

    def test_scenario_32_domestic_partner_with_no_income(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 30, income={"wages": 40_000})
        self.member(screen, "domesticPartner", 28)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_33_supported_parent_living_on_ssi(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 48, income={"wages": 52_000})
        self.member(screen, "parent", 74, income={"sSI": 11_000})

        self.assert_eligible(self.calculate(screen), 500)

    def test_scenario_34_roommate_with_high_earnings(self):
        screen = self.make_screen(household_size=3)
        self.member(screen, "headOfHousehold", 31, income={"wages": 2_600})
        self.member(screen, "child", 5)
        self.member(screen, "roommate", 40, income={"wages": 300_000})

        self.assert_eligible(self.calculate(screen), 15)

    def test_scenario_35_child_living_on_ssi(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 31, income={"wages": 10_000})
        self.member(screen, "child", 12, income={"sSI": 12_000})

        self.assert_eligible(self.calculate(screen), 1_125)

    def test_scenario_36_disabled_adult_child_with_earnings(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 58, income={"wages": 40_000})
        self.member(screen, "child", 30, disabled=True, long_term_disability=True, income={"wages": 8_000})

        self.assert_eligible(self.calculate(screen), 500)

    def test_scenario_37_student_aged_24_with_earnings(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 52, income={"wages": 40_000})
        self.member(screen, "child", 24, student=True, income={"wages": 6_000})

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_38_sibling_marked_disabled_but_not_long_term(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 16, income={"wages": 14_000})
        self.member(screen, "sisterOrBrother", 16, disabled=True, long_term_disability=False)

        self.assert_eligible(self.calculate(screen), 0)


class TestBirthAfterTheTaxYear(FederalCtcTestCase):
    """A child born after the tax year wasn't alive in it, so isn't claimed for it."""

    def test_a_child_born_after_the_tax_year_is_not_a_dependent(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 30, income={"wages": 20_000})
        self.add_member(screen, "child", age=None, birth_year_month=date(TAX_YEAR + 1, 1, 1))

        self.assert_ineligible(self.calculate(screen))

    def test_a_child_born_in_december_of_the_tax_year_is_counted(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 30, income={"wages": 20_000})
        self.member(screen, "child", 0, month=12)

        self.assert_eligible(self.calculate(screen), 1_700)

    def test_a_newborn_does_not_stop_an_older_child_counting(self):
        screen = self.make_screen(household_size=3)
        self.member(screen, "headOfHousehold", 30, income={"wages": 40_000})
        self.member(screen, "child", 4)
        self.add_member(screen, "child", age=None, birth_year_month=date(TAX_YEAR + 1, 1, 1))

        self.assert_eligible(self.calculate(screen), 2_200)


class TestAgeOnlyHouseholds(FederalCtcTestCase):
    """The Colorado tax-credit apps send `age` with no birth month, and no disability or
    student answers."""

    def test_a_child_is_counted_by_age(self):
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", age=45, stored_age=True, screener_defaults=False)
        self.add_member(screen, "child", age=8, stored_age=True, screener_defaults=False)
        self.add_income(head, 40_000, "wages", "yearly")

        self.assert_eligible(self.calculate(screen), 2_200)

    def test_an_age_only_child_is_taken_at_the_reported_age(self):
        """A child reported as 17 is 17 for the tax year: an other dependent, not a qualifying child."""
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", age=45, stored_age=True, screener_defaults=False)
        self.add_member(screen, "child", age=17, stored_age=True, screener_defaults=False)
        self.add_income(head, 40_000, "wages", "yearly")

        self.assert_eligible(self.calculate(screen), 500)

    def test_an_age_only_nineteen_year_old_is_nineteen_for_the_tax_year(self):
        """Reported as 19, the child is past the under-19 path and at the relative income limit."""
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", age=45, stored_age=True, screener_defaults=False)
        child = self.add_member(screen, "child", age=19, stored_age=True, screener_defaults=False)
        self.add_income(head, 40_000, "wages", "yearly")
        self.add_income(child, 5_200, "wages", "yearly")

        self.assert_ineligible(self.calculate(screen))

    def test_a_disabled_member_with_no_age_is_not_a_qualifying_child(self):
        """Without an age the qualifying-child path cannot run, disabled or not; the member can
        only be a relative, and $6,000 is over the relative limit."""
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", age=45, stored_age=True, screener_defaults=False)
        child = self.add_member(
            screen,
            "child",
            age=None,
            stored_age=True,
            screener_defaults=False,
            disabled=True,
            long_term_disability=True,
        )
        self.add_income(head, 40_000, "wages", "yearly")
        self.add_income(child, 6_000, "wages", "yearly")

        self.assert_ineligible(self.calculate(screen))

    def test_a_child_the_filers_age_is_an_other_dependent(self):
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", age=16, stored_age=True, screener_defaults=False)
        self.add_member(screen, "sisterOrBrother", age=16, stored_age=True, screener_defaults=False)
        self.add_income(head, 14_000, "wages", "yearly")

        self.assert_eligible(self.calculate(screen), 0)

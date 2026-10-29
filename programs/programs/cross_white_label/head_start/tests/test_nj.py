"""
NJ Head Start (``NjHeadStart``): NJ's values, and one test per Test Scenario in the NJ spec
(``programs/cross_white_label/head_start/nj/head_start_nj_spec.md`` in program-ops).

The federal rules are tested against a stand-in state in ``test_mfb_base.py``; these run the
spec's households end to end through real screener rows.

The spec states values to the cent ($9,938.20); the base rounds a member's value to whole
dollars, so these expect $9,938 a child.

Scenarios 8, 9, 10 and 13 report SNAP, TANF, SSI or WIC as a current benefit. NJ has no
Program row for any of them yet, so the screener can't send these households today; the
tests seed a stand-in row with the right ``base_program`` so the rule is covered once it can.
"""

from datetime import date

import programs.framework.eligibility_messages as messages
from programs.framework.base import Eligibility
from programs.programs.cross_white_label.head_start.mfb_base import MfbHeadStart
from programs.programs.cross_white_label.head_start.nj import NjHeadStart
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from screener.models import Screen
from screener.serializers import _write_current_benefits
from screener.tests.helpers import seed_program

VALUE_PER_CHILD = 9_938


class NjHeadStartTestCase(CustomCalculatorTestCase):
    calculator_class = NjHeadStart
    white_label_code = "nj"
    state_code = "NJ"
    fpl_year = "2026"
    default_zipcode = "08608"
    default_county = "Mercer County"
    # The next October 1 cutoff is 2027-10-01, which scenarios 16-18 date birth months against.
    reference_date = date(2026, 10, 15)

    def household(self, size: int, head_wages: int = 0, head_age: int = 30) -> Screen:
        """A screen of `size` whose head earns `head_wages` a year. The test adds the rest."""
        screen = self.make_screen(household_size=size)
        self.add_member(screen, "headOfHousehold", head_age, yearly_income=head_wages)

        return screen

    def receive(self, screen: Screen, base_program: str) -> None:
        name = f"nj_{base_program}_stand_in"
        seed_program(self.white_label, name, base_program=base_program)
        _write_current_benefits(screen, [name])
        screen.invalidate_current_benefits_cache()

    def assert_eligible(self, eligibility: Eligibility, children: int = 1) -> None:
        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, children * VALUE_PER_CHILD)

    def assert_ineligible(self, eligibility: Eligibility) -> None:
        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.value, 0)


class TestNjValues(NjHeadStartTestCase):
    def test_extends_the_mfb_base(self):
        self.assertTrue(issubclass(NjHeadStart, MfbHeadStart))

    def test_program_code(self):
        self.assertEqual(NjHeadStart.program_code, "nj_head_start")

    def test_school_age_dates(self):
        self.assertEqual(NjHeadStart.school_eligibility_cutoff_date, (10, 1))
        self.assertEqual(NjHeadStart.compulsory_school_age, 6)

    def test_value_terms(self):
        """$292.30/week x 34 weeks (1,020 annual hours / 30-hour week) = $9,938.20."""
        self.assertEqual(NjHeadStart.weekly_price, 292.30)
        self.assertEqual(NjHeadStart.program_weeks, 1_020 // 30)

    def test_gates_on_no_state_program(self):
        self.assertEqual(NjHeadStart.gates_on_any, ())


class TestIncomePovertyLine(NjHeadStartTestCase):
    def test_scenario_1_well_under_the_income_line(self):
        screen = self.household(2, head_wages=12_000)
        self.add_member(screen, "child", 4)

        self.assert_eligible(self.calculate(screen))

    def test_scenario_2_household_of_2_at_the_poverty_guideline(self):
        screen = self.household(2, head_wages=21_640)
        self.add_member(screen, "child", 4)

        eligibility = self.calculate(screen)

        self.assert_eligible(eligibility)
        self.assertEqual(eligibility.pass_messages, [messages.income(21_640, 21_640)])

    def test_scenario_3_household_of_2_one_dollar_over(self):
        screen = self.household(2, head_wages=21_641)
        self.add_member(screen, "child", 4)

        eligibility = self.calculate(screen)

        self.assert_ineligible(eligibility)
        self.assertEqual(eligibility.fail_messages, [messages.income(21_641, 21_640)])

    def test_scenario_4_household_of_4_at_the_poverty_guideline(self):
        screen = self.household(4, head_wages=33_000, head_age=32)
        self.add_member(screen, "spouse", 31)
        self.add_member(screen, "child", 4)
        self.add_member(screen, "child", 1)

        self.assert_eligible(self.calculate(screen))

    def test_scenario_5_household_of_4_one_dollar_over(self):
        screen = self.household(4, head_wages=33_001, head_age=32)
        self.add_member(screen, "spouse", 31)
        self.add_member(screen, "child", 4)
        self.add_member(screen, "child", 1)

        eligibility = self.calculate(screen)

        self.assert_ineligible(eligibility)
        self.assertEqual(eligibility.fail_messages, [messages.income(33_001, 33_000)])

    def test_scenario_6_high_rent_brings_income_under_the_line(self):
        """$24,000 - ($9,600 - 0.30 x $24,000) = $21,600, under $21,640."""
        screen = self.household(2, head_wages=24_000)
        self.add_member(screen, "child", 4)
        self.add_expense(screen.get_head(), 800, "rent")

        eligibility = self.calculate(screen)

        self.assert_eligible(eligibility)
        self.assertEqual(eligibility.pass_messages, [messages.income(21_600, 21_640)])

    def test_scenario_7_high_rent_not_quite_enough(self):
        """$24,100 - ($9,600 - 0.30 x $24,100) = $21,730, over $21,640."""
        screen = self.household(2, head_wages=24_100)
        self.add_member(screen, "child", 4)
        self.add_expense(screen.get_head(), 800, "rent")

        eligibility = self.calculate(screen)

        self.assert_ineligible(eligibility)
        self.assertEqual(eligibility.fail_messages, [messages.income(21_730, 21_640)])


class TestPublicAssistance(NjHeadStartTestCase):
    def over_income_household(self) -> Screen:
        screen = self.household(2, head_wages=40_000)
        self.add_member(screen, "child", 4)

        return screen

    def test_scenario_8_receiving_snap(self):
        screen = self.over_income_household()
        self.receive(screen, "snap")

        eligibility = self.calculate(screen)

        self.assert_eligible(eligibility)
        self.assertEqual(eligibility.pass_messages, [messages.presumed_eligibility()])

    def test_scenario_9_receiving_tanf(self):
        screen = self.over_income_household()
        self.receive(screen, "tanf")

        self.assert_eligible(self.calculate(screen))

    def test_scenario_10_receiving_ssi_as_a_current_benefit(self):
        screen = self.over_income_household()
        self.receive(screen, "ssi")

        self.assert_eligible(self.calculate(screen))

    def test_scenario_11_ssi_reported_as_income(self):
        screen = self.household(3, head_wages=40_000)
        self.add_member(screen, "child", 6, monthly_income=900, income_type="sSI")
        self.add_member(screen, "child", 4)

        self.assert_eligible(self.calculate(screen))

    def test_scenario_12_cash_assistance_reported_as_income(self):
        screen = self.over_income_household()
        self.add_income(screen.get_head(), 300, "cashAssistance")

        self.assert_eligible(self.calculate(screen))

    def test_scenario_13_wic_only(self):
        screen = self.over_income_household()
        self.receive(screen, "wic")

        eligibility = self.calculate(screen)

        self.assert_ineligible(eligibility)
        self.assertEqual(eligibility.fail_messages, [messages.income(40_000, 21_640)])


class TestFosterCare(NjHeadStartTestCase):
    def test_scenario_14_foster_child_over_income(self):
        screen = self.household(2, head_wages=60_000, head_age=45)
        self.add_member(screen, "fosterChild", 4)

        self.assert_eligible(self.calculate(screen))

    def test_scenario_15_grandchild_over_income(self):
        screen = self.household(2, head_wages=60_000, head_age=60)
        self.add_member(screen, "grandChild", 4)

        eligibility = self.calculate(screen)

        self.assert_ineligible(eligibility)
        self.assertEqual(eligibility.fail_messages, [messages.income(60_000, 21_640)])


class TestAgePreschool(NjHeadStartTestCase):
    def child_born(self, birth_year_month: date) -> Screen:
        screen = self.household(2, head_wages=12_000)
        self.add_member(screen, "child", None, birth_year_month=birth_year_month)

        return screen

    def test_scenario_16_turns_3_in_september_of_the_next_cutoff_year(self):
        """Born September 2024: 2 today, 3 by 2027-10-01."""
        self.assert_eligible(self.calculate(self.child_born(date(2024, 9, 1))))

    def test_scenario_17_turns_3_in_october_of_the_next_cutoff_year(self):
        """Born October 2024, dated to October 1: 3 on the cutoff day itself."""
        self.assert_eligible(self.calculate(self.child_born(date(2024, 10, 1))))

    def test_scenario_18_turns_3_in_november_of_the_next_cutoff_year(self):
        """Born November 2024: still 2 on 2027-10-01."""
        self.assert_ineligible(self.calculate(self.child_born(date(2024, 11, 1))))

    def test_scenario_19_five_year_old(self):
        screen = self.household(2, head_wages=12_000)
        self.add_member(screen, "child", 5)

        self.assert_eligible(self.calculate(screen))

    def test_scenario_20_six_year_old(self):
        screen = self.household(2, head_wages=12_000)
        self.add_member(screen, "child", 6)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_21_two_preschoolers_and_an_older_sibling(self):
        screen = self.household(4, head_wages=15_000)
        self.add_member(screen, "child", 3)
        self.add_member(screen, "child", 4)
        self.add_member(screen, "child", 7)

        self.assert_eligible(self.calculate(screen), children=2)

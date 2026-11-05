"""
NJ Early Head Start (``NjEarlyHeadStart``): NJ's values, and one test per Test Scenario in the
NJ spec (``programs/cross_white_label/early_head_start/nj/early_head_start_nj_spec.md`` in
program-ops).

The federal rules are tested against stand-in states in ``test_mfb_base.py``; these run the
spec's households end to end through real screener rows.

Each member's value is rounded half-up to whole dollars, as the spec states: $16,909 (from
$16,909.14), $15,059 ($15,059.48) and $13,446 ($13,445.80).

Scenarios 7 and 10 report SSI or WIC as a current benefit. NJ's SSI is the ``federal_ssi``
row and NJ has no WIC row, so the tests seed a stand-in row with the right ``base_program``.
"""

from datetime import date
from decimal import Decimal

import programs.framework.eligibility_messages as messages
from programs.framework.base import Eligibility
from programs.programs.cross_white_label.early_head_start.mfb_base import MfbEarlyHeadStart
from programs.programs.cross_white_label.early_head_start.nj import NjEarlyHeadStart
from programs.programs.testing_fixtures.custom_calculator import (
    CustomCalculatorTestCase,
    eligible_result,
    ineligible_result,
)
from screener.models import HouseholdMember, Screen
from screener.serializers import _write_current_benefits
from screener.tests.helpers import seed_program

INFANT = 16_909
TODDLER = 15_059
OLDEST = 13_446


def months(n: int) -> float:
    return n / 12


class NjEarlyHeadStartTestCase(CustomCalculatorTestCase):
    calculator_class = NjEarlyHeadStart
    white_label_code = "nj"
    state_code = "NJ"
    fpl_year = "2026"
    default_zipcode = "08608"
    default_county = "Mercer County"
    # Pinned so a child's age in months, and so their rate band, can't shift with the calendar.
    reference_date = date(2026, 11, 2)

    def household(self, size: int, head_wages: int = 0, head_age: int = 30, pregnant: bool = False) -> Screen:
        """A screen of `size` whose head earns `head_wages` a year. The test adds the rest."""
        screen = self.make_screen(household_size=size)
        self.add_member(screen, "headOfHousehold", head_age, yearly_income=head_wages, pregnant=pregnant)

        return screen

    def parent_and_child(self, child_age: float, head_wages: int = 12_000) -> Screen:
        screen = self.household(2, head_wages=head_wages)
        self.add_member(screen, "child", child_age)

        return screen

    def receive(self, screen: Screen, base_program: str) -> None:
        name = f"nj_{base_program}_stand_in"
        seed_program(self.white_label, name, base_program=base_program)
        _write_current_benefits(screen, [name])
        screen.invalidate_current_benefits_cache()

    def assert_eligible(self, eligibility: Eligibility, value: int = INFANT) -> None:
        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, value)

    def assert_ineligible(self, eligibility: Eligibility) -> None:
        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.value, 0)


class TestNjValues(NjEarlyHeadStartTestCase):
    def test_extends_the_mfb_base(self):
        self.assertTrue(issubclass(NjEarlyHeadStart, MfbEarlyHeadStart))

    def test_program_code(self):
        self.assertEqual(NjEarlyHeadStart.program_code, "nj_early_head_start")

    def test_value_terms(self):
        """NJ's center rates by band, over 46 weeks (1,380 annual hours / 30-hour week)."""
        self.assertEqual(
            NjEarlyHeadStart.weekly_prices,
            ((0, Decimal("367.59")), (18, Decimal("327.38")), (30, Decimal("292.30"))),
        )
        self.assertEqual(NjEarlyHeadStart.program_weeks, 46)

    def test_gates_on_federal_ssi_only(self):
        self.assertEqual(NjEarlyHeadStart.gates_on_any, ("federal_ssi",))
        self.assertEqual(NjEarlyHeadStart.gates_on, ())

    def test_children_are_built_at_the_months_the_scenarios_state(self):
        screen = self.parent_and_child(months(17))
        child = screen.household_members.get(relationship="child")

        self.assertEqual(child.birth_year_month, date(2025, 6, 1))
        self.assertEqual(HouseholdMember.objects.get(pk=child.pk).calc_age(), 1)


class TestIncomePovertyLine(NjEarlyHeadStartTestCase):
    def test_scenario_1_parent_and_a_10_month_old_well_under_the_line(self):
        self.assert_eligible(self.calculate(self.parent_and_child(months(10))))

    def test_scenario_2_household_of_2_at_the_poverty_guideline(self):
        eligibility = self.calculate(self.parent_and_child(months(10), head_wages=21_640))

        self.assert_eligible(eligibility)
        self.assertEqual(eligibility.pass_messages, [messages.income(21_640, 21_640)])

    def test_scenario_3_household_of_2_one_dollar_over(self):
        eligibility = self.calculate(self.parent_and_child(months(10), head_wages=21_641))

        self.assert_ineligible(eligibility)
        self.assertEqual(eligibility.fail_messages, [messages.income(21_641, 21_640)])

    def test_scenario_4_household_of_4_at_the_poverty_guideline(self):
        screen = self.household(4, head_wages=33_000, head_age=32)
        self.add_member(screen, "spouse", 31)
        self.add_member(screen, "child", 6)
        self.add_member(screen, "child", months(10))

        self.assert_eligible(self.calculate(screen))

    def test_scenario_5_household_of_4_one_dollar_over(self):
        screen = self.household(4, head_wages=33_001, head_age=32)
        self.add_member(screen, "spouse", 31)
        self.add_member(screen, "child", 6)
        self.add_member(screen, "child", months(10))

        eligibility = self.calculate(screen)

        self.assert_ineligible(eligibility)
        self.assertEqual(eligibility.fail_messages, [messages.income(33_001, 33_000)])

    def test_scenario_6_high_rent_brings_counted_income_under_the_line(self):
        """$24,000 - ($9,600 - 0.30 x $24,000) = $21,600, under $21,640."""
        screen = self.parent_and_child(months(10), head_wages=24_000)
        self.add_expense(screen.get_head(), 800, "rent")

        eligibility = self.calculate(screen)

        self.assert_eligible(eligibility)
        self.assertEqual(eligibility.pass_messages, [messages.income(21_600, 21_640)])


class TestPublicAssistance(NjEarlyHeadStartTestCase):
    def over_income_household(self) -> Screen:
        return self.parent_and_child(months(10), head_wages=40_000)

    def test_scenario_7_ssi_reported_as_a_current_benefit(self):
        screen = self.over_income_household()
        self.receive(screen, "ssi")

        eligibility = self.calculate(screen)

        self.assert_eligible(eligibility)
        self.assertEqual(eligibility.pass_messages, [messages.presumed_eligibility()])

    def test_scenario_8_cash_assistance_income_with_no_benefit_ticked(self):
        screen = self.over_income_household()
        self.add_income(screen.get_head(), 3_000, "cashAssistance", frequency="yearly")

        self.assert_eligible(self.calculate(screen))

    def test_scenario_9_ssi_income_with_no_benefit_ticked(self):
        screen = self.over_income_household()
        self.add_income(screen.get_head(), 10_000, "sSI", frequency="yearly")

        self.assert_eligible(self.calculate(screen))

    def test_scenario_10_wic_reported_income_over_the_line(self):
        screen = self.over_income_household()
        self.receive(screen, "wic")

        eligibility = self.calculate(screen)

        self.assert_ineligible(eligibility)
        self.assertEqual(eligibility.fail_messages, [messages.income(40_000, 21_640)])

    def test_scenario_22_roommate_on_ssi_family_income_over_the_line(self):
        """Asserts the household-level approximation `public_assistance_family_unit`."""
        screen = self.household(3, head_wages=40_000)
        self.add_member(screen, "child", months(10))
        self.add_member(screen, "roommate", 50, yearly_income=10_000, income_type="sSI")

        self.assert_eligible(self.calculate(screen))

    def test_eligible_for_federal_ssi_qualifies(self):
        """`federal_ssi` stands in for `{ssi_program_code}`; SNAP and TANF have none in NJ."""
        screen = self.over_income_household()

        self.assert_eligible(self.calculate(screen, data={"federal_ssi": eligible_result()}))

    def test_ineligible_for_federal_ssi_does_not_qualify(self):
        screen = self.over_income_household()

        self.assert_ineligible(self.calculate(screen, data={"federal_ssi": ineligible_result()}))


class TestFosterCare(NjEarlyHeadStartTestCase):
    def test_scenario_11_foster_child_household_income_over_the_line(self):
        screen = self.household(2, head_wages=90_000, head_age=45)
        self.add_member(screen, "fosterChild", months(24))

        self.assert_eligible(self.calculate(screen), value=TODDLER)

    def test_scenario_12_grandchild_not_in_foster_care(self):
        screen = self.household(2, head_wages=90_000, head_age=60)
        self.add_member(screen, "grandChild", 2)

        eligibility = self.calculate(screen)

        self.assert_ineligible(eligibility)
        self.assertEqual(eligibility.fail_messages, [messages.income(90_000, 21_640)])


class TestAgeAndBands(NjEarlyHeadStartTestCase):
    def test_scenario_13_child_of_35_months(self):
        self.assert_eligible(self.calculate(self.parent_and_child(months(35))), value=OLDEST)

    def test_scenario_14_child_of_3(self):
        self.assert_ineligible(self.calculate(self.parent_and_child(3)))

    def test_scenario_15_child_of_18_months(self):
        self.assert_eligible(self.calculate(self.parent_and_child(months(18))), value=TODDLER)

    def test_scenario_16_child_of_30_months(self):
        self.assert_eligible(self.calculate(self.parent_and_child(months(30))), value=OLDEST)

    def test_scenario_20_child_of_17_months(self):
        self.assert_eligible(self.calculate(self.parent_and_child(months(17))), value=INFANT)

    def test_scenario_21_child_of_29_months(self):
        self.assert_eligible(self.calculate(self.parent_and_child(months(29))), value=TODDLER)


class TestPregnant(NjEarlyHeadStartTestCase):
    def test_scenario_17_pregnant_woman_with_no_children(self):
        screen = self.household(1, head_wages=12_000, head_age=26, pregnant=True)

        self.assert_eligible(self.calculate(screen))

    def test_scenario_18_adult_who_is_not_pregnant(self):
        screen = self.household(1, head_wages=12_000, head_age=26)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_19_pregnant_mother_and_a_10_month_old(self):
        screen = self.household(2, head_wages=12_000, head_age=28, pregnant=True)
        self.add_member(screen, "child", months(10))

        self.assert_eligible(self.calculate(screen), value=2 * INFANT)

    def test_scenario_23_pregnant_woman_alone_at_the_1_person_guideline(self):
        screen = self.household(1, head_wages=15_960, head_age=26, pregnant=True)

        eligibility = self.calculate(screen)

        self.assert_eligible(eligibility)
        self.assertEqual(eligibility.pass_messages, [messages.income(15_960, 15_960)])

    def test_scenario_24_pregnant_woman_alone_one_dollar_over(self):
        screen = self.household(1, head_wages=15_961, head_age=26, pregnant=True)

        eligibility = self.calculate(screen)

        self.assert_ineligible(eligibility)
        self.assertEqual(eligibility.fail_messages, [messages.income(15_961, 15_960)])

    def test_an_unanswered_pregnancy_drops_the_program(self):
        """`pregnant` is a dependency: a screen that never asked can't answer the route."""
        screen = self.household(1, head_wages=12_000, head_age=26)
        calculator = self.make_calculator(screen, missing=("pregnant",))

        self.assertFalse(calculator.can_calc())

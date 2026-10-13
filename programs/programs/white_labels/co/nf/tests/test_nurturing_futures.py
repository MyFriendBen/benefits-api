"""Nurturing Futures (Boulder County): the spec's test scenarios, plus HUD and birth-date edges.

HUD is stubbed with Boulder County's published 2026 limits, which are HUD's MTSP 30% figures
for the Boulder MSA, so the boundary scenarios test the dollar amounts the county states.
"""

from datetime import date
from typing import Optional

from programs.framework.base import Eligibility
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from programs.programs.testing_fixtures.households import make_program
from programs.programs.white_labels.co.nf.calculator import NurturingFutures
from screener.models import HouseholdMember, Screen

# Boulder County's published limits by household size; HUD MTSP 30% AMI, Boulder MSA, FY2026.
BOULDER_30_PERCENT_AMI = {1: 31_500, 2: 36_000, 3: 40_500, 4: 45_000, 5: 48_600, 6: 52_200, 7: 55_800, 8: 59_400}


def boulder_ami(screen: Screen, percent: str, year: int, county_override: Optional[str] = None) -> int:
    """HUD's answer for Boulder County, asserting the calculator asked for that and nothing else."""
    if (percent, year, county_override) != ("30%", 2026, "Boulder County"):
        raise AssertionError(f"Unexpected HUD lookup: {percent}, {year}, {county_override}")

    return BOULDER_30_PERCENT_AMI[screen.household_size]


class NurturingFuturesTestCase(CustomCalculatorTestCase):
    calculator_class = NurturingFutures
    white_label_code = "co"
    state_code = "CO"
    default_zipcode = "80301"
    default_county = "Boulder County"
    reference_date = date(2026, 10, 13)
    needs_program_row = False
    stores_age = False

    def run_calculator(self, screen: Screen) -> Eligibility:
        with self.hud_ami(boulder_ami):
            return self.calculate(screen)

    def assert_eligible(self, screen: Screen) -> None:
        e = self.run_calculator(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 7_200)

    def assert_ineligible(self, screen: Screen) -> None:
        self.assertFalse(self.run_calculator(screen).eligible)

    def add_child(self, screen: Screen, age: float = 2, **kwargs) -> HouseholdMember:
        return self.add_member(screen, relationship="child", age=age, **kwargs)


class TestSpecScenarios(NurturingFuturesTestCase):
    def three_person_household(self, head_wages: int) -> Screen:
        screen = self.make_screen(household_size=3)
        self.add_member(screen, age=30, yearly_income=head_wages)
        self.add_member(screen, relationship="spouse", age=28)
        self.add_child(screen)

        return screen

    def five_person_household(self, head_wages: int) -> Screen:
        screen = self.make_screen(household_size=5)
        self.add_member(screen, age=34, yearly_income=head_wages)
        self.add_member(screen, relationship="spouse", age=32)
        self.add_child(screen, age=9)
        self.add_child(screen, age=6)
        self.add_child(screen, age=None, birth_year_month=date(2023, 3, 1))

        return screen

    def test_1_golden_path(self):
        self.assert_eligible(self.three_person_household(30_000))

    def test_2_income_at_the_limit_for_three(self):
        self.assert_eligible(self.three_person_household(40_500))

    def test_3_income_one_dollar_over_the_limit_for_three(self):
        self.assert_ineligible(self.three_person_household(40_501))

    def test_4_income_at_the_limit_for_five(self):
        self.assert_eligible(self.five_person_household(48_600))

    def test_5_income_one_dollar_over_the_limit_for_five(self):
        self.assert_ineligible(self.five_person_household(48_601))

    def test_6_lives_outside_boulder_county(self):
        screen = self.make_screen(household_size=2, zipcode="80202", county="Denver County")
        self.add_member(screen, age=30, yearly_income=20_000)
        self.add_child(screen)

        self.assert_ineligible(screen)

    def test_7_child_born_in_the_boundary_month(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, age=30, yearly_income=20_000)
        self.add_child(screen, age=None, birth_year_month=date(2022, 11, 1))

        self.assert_eligible(screen)

    def test_8_child_born_one_month_before_the_boundary(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, age=30, yearly_income=20_000)
        self.add_child(screen, age=None, birth_year_month=date(2022, 10, 1))

        self.assert_ineligible(screen)

    def test_9_head_of_household_exactly_18(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, age=18, yearly_income=15_000)
        self.add_child(screen, age=1)

        self.assert_eligible(screen)

    def test_10_head_of_household_is_17(self):
        screen = self.make_screen(household_size=3)
        self.add_member(screen, age=17, yearly_income=15_000)
        self.add_child(screen, age=1)
        self.add_member(screen, relationship="grandParent", age=45)

        self.assert_ineligible(screen)

    def test_11_over_the_limit_on_snap_only(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, age=30, yearly_income=60_000)
        self.add_child(screen)
        screen.current_benefits.create(program=make_program("co", "co_snap", state_code="CO"))

        self.assert_ineligible(screen)

    def test_12_over_the_limit_reports_nurturing_futures_income(self):
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, age=30, yearly_income=60_000)
        self.add_income(head, 600, income_type="nurturingFutures")
        self.add_child(screen)

        self.assert_eligible(screen)


class TestChildBirthDate(NurturingFuturesTestCase):
    def test_a_child_without_a_birth_date_does_not_qualify(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, age=30, yearly_income=20_000)
        self.add_child(screen, age=None)

        self.assert_ineligible(screen)

    def test_a_head_without_a_birth_date_does_not_qualify(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, age=None, yearly_income=20_000)
        self.add_child(screen)

        self.assert_ineligible(screen)


class TestChildTurnsFourDuringTheWindow(NurturingFuturesTestCase):
    """The rule is a birth-date floor, not an age: a November 2022 child still qualifies at 4."""

    reference_date = date(2026, 12, 1)

    def test_child_born_november_2022_qualifies_after_turning_four(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, age=30, yearly_income=20_000)
        self.add_child(screen, age=None, birth_year_month=date(2022, 11, 1))

        self.assert_eligible(screen)


class TestHudLookup(NurturingFuturesTestCase):
    def test_hud_unavailable_hides_the_program(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, age=30, yearly_income=20_000)
        self.add_child(screen)

        with self.hud_ami(unavailable=True):
            e = self.calculate(screen)

        self.assertFalse(e.eligible)

    def test_returning_participant_skips_hud(self):
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, age=30, yearly_income=60_000)
        self.add_income(head, 600, income_type="nurturingFutures")
        self.add_child(screen)

        with self.hud_ami(unavailable=True) as hud:
            e = self.calculate(screen)

        self.assertTrue(e.eligible)
        hud.get_screen_mtsp_ami.assert_not_called()

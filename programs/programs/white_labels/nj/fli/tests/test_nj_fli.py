"""
NJ Family Leave Insurance, including Family Leave During Unemployment.

One test per spec §8 scenario, named for it, then the branches the scenarios don't reach:
the bonding relationships, family care through each disability flag, the FLDU cap and the
value floor.

The spec states values in cents; the API serializes whole dollars, so each scenario asserts
the figure rounded half-up (8,378.57 -> 8,379).
"""

from datetime import date
from typing import Optional

from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from programs.programs.white_labels.nj.fli.calculator import NjFli
from programs.programs.white_labels.nj.paid_leave import PAID_LEAVE_YEARS
from programs.util import DependencyError
from screener.models import HouseholdMember, Screen


class NjFliTestCase(CustomCalculatorTestCase):
    calculator_class = NjFli
    white_label_code = "nj"
    state_code = "NJ"
    default_zipcode = "08608"
    default_county = "Mercer County"
    reference_date = date(2026, 11, 5)
    needs_program_row = False
    stores_age = False

    def worker(
        self,
        screen: Screen,
        age: int,
        relationship: str = "headOfHousehold",
        wages: int = 0,
        unemployment: int = 0,
        ssdi: int = 0,
    ) -> HouseholdMember:
        """A member with yearly incomes, as the scenarios state them."""
        member = self.add_member(screen, relationship, age)
        for amount, income_type in ((wages, "wages"), (unemployment, "unemployment"), (ssdi, "sSDisability")):
            if amount:
                self.add_income(member, amount, income_type, "yearly")
        return member

    def parent_of_newborn(self, age: int = 31, child_age: int = 0, **incomes: int) -> Screen:
        screen = self.make_screen(household_size=2)
        self.worker(screen, age, **incomes)
        self.add_member(screen, "child", child_age)
        return screen

    def assertValue(self, screen: Screen, value: int) -> None:
        e = self.calculate(screen)
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, value)

    def assertIneligible(self, screen: Screen) -> None:
        self.assertFalse(self.calculate(screen).eligible)


class TestRegistration(NjFliTestCase):
    def test_program_code(self):
        self.assertEqual(NjFli.program_code, "nj_fli")

    def test_constants(self):
        self.assertEqual(NjFli.bonding_avg_days, 69)
        self.assertEqual(NjFli.care_avg_days, 45)
        self.assertEqual(PAID_LEAVE_YEARS[2026].fldu_max_weekly_rate, 905)

    def test_missing_relationship_drops_the_program(self):
        with self.assertRaises(DependencyError):
            self.calculate(self.parent_of_newborn(wages=52_000), missing=("relationship",))


class TestSpecScenarios(NjFliTestCase):
    def test_scenario_1_working_parent_of_a_newborn(self):
        self.assertValue(self.parent_of_newborn(31, wages=52_000), 8_379)

    def test_scenario_2_worker_living_with_a_disabled_parent(self):
        screen = self.make_screen(household_size=2)
        self.worker(screen, 45, wages=52_000)
        self.add_member(screen, "parent", 74, disabled=True)

        self.assertValue(screen, 5_464)

    def test_scenario_3_parent_of_a_newborn_at_the_earnings_limit(self):
        self.assertValue(self.parent_of_newborn(26, wages=15_500), 2_494)

    def test_scenario_4_parent_of_a_newborn_one_dollar_under_the_earnings_limit(self):
        self.assertIneligible(self.parent_of_newborn(26, wages=15_499))

    def test_scenario_5_working_parent_who_also_collects_unemployment(self):
        self.assertValue(self.parent_of_newborn(33, wages=20_000, unemployment=15_600), 3_213)

    def test_scenario_6_high_earning_parent_above_the_weekly_maximum(self):
        self.assertValue(self.parent_of_newborn(36, wages=80_000), 11_030)

    def test_scenario_7_working_parent_of_a_one_year_old(self):
        self.assertIneligible(self.parent_of_newborn(31, child_age=1, wages=52_000))

    def test_scenario_8_parent_of_a_newborn_on_unemployment(self):
        self.assertValue(self.parent_of_newborn(30, unemployment=26_000), 4_929)

    def test_scenario_9_parent_of_a_newborn_with_no_wages_and_no_unemployment(self):
        self.assertIneligible(self.parent_of_newborn(30))

    def test_scenario_10_low_wage_parent_who_also_collects_unemployment(self):
        self.assertIneligible(self.parent_of_newborn(28, wages=15_000, unemployment=5_000))

    def test_scenario_11_working_parent_who_also_gets_ssdi(self):
        self.assertIneligible(self.parent_of_newborn(34, wages=30_000, ssdi=18_000))

    def test_scenario_12_parent_on_high_unemployment_above_the_fldu_maximum(self):
        self.assertValue(self.parent_of_newborn(37, unemployment=52_000), 8_921)

    def test_scenario_13_parent_on_unemployment_who_also_gets_ssdi(self):
        self.assertIneligible(self.parent_of_newborn(38, unemployment=26_000, ssdi=18_000))


class TestBonding(NjFliTestCase):
    def household(self, worker_relationship: str, infant_relationship: str) -> Screen:
        screen = self.make_screen(household_size=3)
        if worker_relationship != "headOfHousehold":
            self.add_member(screen, "headOfHousehold", 55)
        self.worker(screen, 30, worker_relationship, wages=52_000)
        self.add_member(screen, infant_relationship, 0)
        return screen

    def test_parents_of_an_infant_child_stepchild_or_foster_child(self):
        for parent in NjFli.bonding_parents:
            for child in NjFli.bonding_children:
                with self.subTest(parent=parent, child=child):
                    self.assertValue(self.household(parent, child), 8_379)

    def test_the_heads_child_with_an_infant_grandchild(self):
        self.assertValue(self.household("child", "grandChild"), 8_379)

    def test_the_head_with_an_infant_grandchild_is_not_bonding(self):
        self.assertIneligible(self.household("headOfHousehold", "grandChild"))

    def test_a_roommate_with_an_infant_child_is_not_bonding(self):
        self.assertIneligible(self.household("roommate", "child"))

    def test_bonding_outranks_care_for_the_duration(self):
        screen = self.parent_of_newborn(31, wages=52_000)
        self.add_member(screen, "parent", 70, disabled=True)

        self.assertValue(screen, 8_379)


class TestFamilyCare(NjFliTestCase):
    def test_each_disability_flag_counts(self):
        for flag in ("disabled", "visually_impaired", "long_term_disability"):
            with self.subTest(flag=flag):
                screen = self.make_screen(household_size=2)
                self.worker(screen, 45, wages=52_000)
                self.add_member(screen, "roommate", 50, **{flag: True})

                self.assertValue(screen, 5_464)

    def test_own_disability_is_not_family_care(self):
        screen = self.make_screen()
        worker = self.worker(screen, 45, wages=52_000)
        worker.disabled = True
        worker.save()

        self.assertIneligible(screen)

    def test_the_disabled_member_is_not_valued_for_caring_for_themselves(self):
        screen = self.make_screen(household_size=2)
        self.worker(screen, 45, wages=52_000)
        parent = self.worker(screen, 60, "parent", wages=40_000)
        parent.disabled = True
        parent.save()

        e = self.calculate(screen)

        self.assertEqual([m.eligible for m in e.eligible_members], [True, False])
        self.assertEqual(e.value, 5_464)


class TestValue(NjFliTestCase):
    def test_fldu_below_the_cap_is_not_raised_to_it(self):
        # floor(46,800 / 52) = 900 a week, under the 905 cap: 900 x 69 / 7 = 8,871.43.
        self.assertValue(self.parent_of_newborn(30, unemployment=46_800), 8_871)

    def test_tiny_unemployment_is_floored_at_one_dollar(self):
        self.assertValue(self.parent_of_newborn(30, unemployment=40), 1)

    def test_unanswered_pregnancy_is_not_read(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", 30, pregnant=None)
        self.add_income(screen.household_members.get(), 52_000, "wages", "yearly")
        self.add_member(screen, "child", 0)

        self.assertValue(screen, 8_379)

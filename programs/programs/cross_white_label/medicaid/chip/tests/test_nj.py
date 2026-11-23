"""
NJ FamilyCare CHIP (``NjChip``): NJ's values, and one test per Test Scenario in the NJ spec
(program-ops ``programs/cross_white_label/medicaid/chip/nj/chip_nj_spec.md``, section 8).

The base rules are tested against stand-in states in ``test_mfb_base.py``; these run the
spec's households end to end through real screener rows. Scenarios marked "Eligible — no
dollar value asserted" (13, 15, 24) assert eligibility only: the pregnancy route has no
estimate, so those households are worth 0.
"""

from programs.framework.base import Eligibility
from programs.programs.cross_white_label.medicaid.chip.mfb_base import MfbChip
from programs.programs.cross_white_label.medicaid.chip.nj import NjChip
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from screener.models import HouseholdMember, Screen


def monthly(dollars: int) -> int:
    return dollars * 12


class NjChipTestCase(CustomCalculatorTestCase):
    calculator_class = NjChip
    white_label_code = "nj"
    state_code = "NJ"
    fpl_year = "2026"
    default_zipcode = "08608"
    default_county = "Mercer County"

    def household(self, size: int, head_age: int, head_wages: int = 0, **head) -> Screen:
        """A screen of `size` whose head earns `head_wages` a year. The test adds the rest."""
        screen = self.make_screen(household_size=size)
        self.head = self.add_member(screen, "headOfHousehold", head_age, yearly_income=head_wages, **head)
        return screen

    def couple_with_child(
        self, wages: int, child_age: int, head_age: int = 35, spouse_age: int = 33, **child
    ) -> Screen:
        screen = self.household(3, head_age, wages)
        self.add_member(screen, "spouse", spouse_age)
        self.child = self.add_member(screen, "child", child_age, **child)
        return screen

    def member_result(self, e: Eligibility, member: HouseholdMember):
        return next(m for m in e.eligible_members if m.member.id == member.id)

    def assert_eligible(self, e: Eligibility, value: int) -> None:
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, value)

    def assert_ineligible(self, e: Eligibility) -> None:
        self.assertFalse(e.eligible)


class TestNjChipConstants(NjChipTestCase):
    def test_registration(self):
        self.assertEqual(NjChip.program_code, "nj_chip")
        self.assertTrue(issubclass(NjChip, MfbChip))
        self.assertFalse(NjChip._abstract)

    def test_nj_values(self):
        self.assertEqual(NjChip.chip_income_limit_fpl, 350)
        self.assertEqual(NjChip.medicaid_child_income_limit_under_1_fpl, 194)
        self.assertEqual(NjChip.medicaid_child_income_limit_1_to_5_fpl, 142)
        self.assertEqual(NjChip.medicaid_child_income_limit_6_to_18_fpl, 142)
        self.assertEqual(NjChip.medicaid_pregnancy_income_limit_fpl, 194)
        self.assertEqual(NjChip.nj_pregnancy_income_limit_fpl, 200)
        self.assertTrue(NjChip.pregnant_women_option)
        self.assertEqual(NjChip.pregnant_member_count_for_others, "herself_plus_expected")
        self.assertEqual(NjChip.poverty_guideline_table, "48-state")
        self.assertEqual(NjChip.state_magi_excluded_income_types, ())

    def test_value_by_age(self):
        """Section 7: round(426.25 × DOBI age factor)."""
        screen = self.household(1, 18)
        calculator = self.make_calculator(screen)
        for age, value in ((0, 326), (14, 326), (15, 355), (16, 366), (17, 377), (18, 389)):
            with self.subTest(age=age):
                self.set_age(self.head, age)
                self.assertEqual(calculator.child_monthly_value(self.head), value)


class TestNjChipScenarios(NjChipTestCase):
    def test_scenario_1_child_in_the_middle_of_the_band(self):
        self.assert_eligible(self.calculate(self.couple_with_child(60_000, 8)), monthly(326))

    def test_scenario_2_child_exactly_at_the_ceiling(self):
        self.assert_eligible(self.calculate(self.couple_with_child(96_986, 10)), monthly(326))

    def test_scenario_3_child_one_dollar_over_the_ceiling(self):
        self.assert_ineligible(self.calculate(self.couple_with_child(96_987, 10)))

    def test_scenario_4_child_just_above_the_medicaid_limit(self):
        screen = self.couple_with_child(40_161, 1, head_age=30, spouse_age=29)
        self.assert_eligible(self.calculate(screen), monthly(326))

    def test_scenario_5_child_at_the_medicaid_limit(self):
        screen = self.couple_with_child(40_160, 4, head_age=30, spouse_age=29)
        self.assert_ineligible(self.calculate(screen))

    def test_scenario_6_infant_just_above_the_infant_limit(self):
        screen = self.couple_with_child(54_367, 0, head_age=30, spouse_age=29)
        self.assert_eligible(self.calculate(screen), monthly(326))

    def test_scenario_7_infant_at_the_infant_limit(self):
        screen = self.couple_with_child(54_366, 0, head_age=30, spouse_age=29)
        self.assert_ineligible(self.calculate(screen))

    def test_scenario_8_nineteen_year_old(self):
        screen = self.couple_with_child(60_000, 19, head_age=45, spouse_age=43)
        self.assert_ineligible(self.calculate(screen))

    def test_scenario_9_eighteen_year_old(self):
        screen = self.couple_with_child(60_000, 18, head_age=45, spouse_age=43)
        self.assert_eligible(self.calculate(screen), monthly(389))

    def test_scenario_10_three_teenagers(self):
        screen = self.household(5, 45, 80_000)
        self.add_member(screen, "spouse", 43)
        for age in (15, 16, 17):
            self.add_member(screen, "child", age)
        self.assert_eligible(self.calculate(screen), monthly(355 + 366 + 377))

    def test_scenario_11_child_on_medicaid(self):
        screen = self.couple_with_child(60_000, 8)
        self.add_insurance(self.child, medicaid=True, none=False)
        self.assert_ineligible(self.calculate(screen))

    def test_scenario_12_child_with_employer_coverage(self):
        screen = self.couple_with_child(60_000, 8)
        self.add_insurance(self.child, employer=True, none=False)
        self.assert_ineligible(self.calculate(screen))

    def test_scenario_13_pregnant_woman_just_above_the_pregnancy_limit(self):
        screen = self.household(2, 27, 54_367, pregnant=True)
        self.add_member(screen, "spouse", 29)
        e = self.calculate(screen)
        self.assertTrue(e.eligible)
        self.assertTrue(self.member_result(e, self.head).eligible)

    def test_scenario_14_pregnant_woman_at_the_pregnancy_limit(self):
        screen = self.household(2, 27, 54_366, pregnant=True)
        self.add_member(screen, "spouse", 29)
        self.assert_ineligible(self.calculate(screen))

    def test_scenario_15_pregnant_woman_exactly_at_the_pregnancy_ceiling(self):
        screen = self.household(2, 27, 56_006, pregnant=True)
        self.add_member(screen, "spouse", 29)
        e = self.calculate(screen)
        self.assertTrue(e.eligible)
        self.assertTrue(self.member_result(e, self.head).eligible)

    def test_scenario_16_pregnant_woman_one_dollar_over_the_pregnancy_ceiling(self):
        screen = self.household(2, 27, 56_007, pregnant=True)
        self.add_member(screen, "spouse", 29)
        self.assert_ineligible(self.calculate(screen))

    def test_scenario_17_adult_in_the_pregnancy_band_who_is_not_pregnant(self):
        screen = self.household(2, 27, 43_700)
        self.add_member(screen, "spouse", 29)
        self.assert_ineligible(self.calculate(screen))

    def test_scenario_18_child_moved_into_medicaid_by_the_expected_child(self):
        screen = self.household(3, 30, 43_000, pregnant=True)
        self.add_member(screen, "spouse", 32)
        child = self.add_member(screen, "child", 6)
        e = self.calculate(screen)
        self.assert_ineligible(e)
        self.assertFalse(self.member_result(e, child).eligible)
        self.assertFalse(self.member_result(e, self.head).eligible)

    def test_scenario_19_pregnant_woman_with_medicare(self):
        screen = self.household(2, 27, 54_367, pregnant=True)
        self.add_member(screen, "spouse", 29)
        self.add_insurance(self.head, medicare=True, none=False)
        self.assert_ineligible(self.calculate(screen))

    def test_scenario_20_child_eligible_while_a_parent_has_medicare(self):
        screen = self.couple_with_child(60_000, 8, head_age=50, spouse_age=48)
        self.add_insurance(self.head, medicare=True, none=False)
        self.assert_eligible(self.calculate(screen), monthly(326))

    def test_scenario_21_eligible_child_and_mother_in_medicaid_range(self):
        screen = self.household(3, 30, 55_000, pregnant=True)
        self.add_member(screen, "spouse", 32)
        child = self.add_member(screen, "child", 6)
        e = self.calculate(screen)
        self.assert_eligible(e, monthly(326))
        self.assertTrue(self.member_result(e, child).eligible)
        self.assertFalse(self.member_result(e, self.head).eligible)

    def test_scenario_22_pregnant_minor_inside_medicaid_range(self):
        screen = self.household(2, 42, 46_450)
        self.add_member(screen, "child", 16, pregnant=True)
        self.assert_ineligible(self.calculate(screen))

    def test_scenario_23_pregnant_minor_above_the_pregnancy_limit(self):
        screen = self.household(2, 42, 68_300)
        minor = self.add_member(screen, "child", 16, pregnant=True)
        e = self.calculate(screen)
        self.assert_eligible(e, monthly(366))
        self.assertTrue(self.member_result(e, minor).eligible)

    def test_scenario_24_two_pregnant_household_members(self):
        screen = self.household(2, 40, 66_000, pregnant=True)
        daughter = self.add_member(screen, "child", 20, pregnant=True, student=True)
        e = self.calculate(screen)
        self.assertTrue(e.eligible)
        self.assertTrue(self.member_result(e, self.head).eligible)
        self.assertTrue(self.member_result(e, daughter).eligible)

    def test_scenario_25_child_already_on_nj_familycare_chip(self):
        screen = self.couple_with_child(60_000, 8)
        self.add_insurance(self.child, chp=True, none=False)
        self.assert_ineligible(self.calculate(screen))
        # The results page reads the same answer as "already has" for this program.
        self.assertTrue(self.child.has_insurance("nj_chip"))

    def test_scenario_26_four_eligible_children(self):
        screen = self.household(6, 40, 90_000)
        self.add_member(screen, "spouse", 38)
        for age in (3, 5, 8, 10):
            self.add_member(screen, "child", age)
        self.assert_eligible(self.calculate(screen), monthly(4 * 326))

    def test_scenario_27_eighteen_year_old_applying_alone(self):
        self.assert_eligible(self.calculate(self.household(1, 18, 30_000)), monthly(389))

    def test_scenario_28_child_with_private_coverage(self):
        screen = self.couple_with_child(60_000, 8)
        self.add_insurance(self.child, private=True, none=False)
        self.assert_ineligible(self.calculate(screen))


class TestNjChipEdges(NjChipTestCase):
    """NJ rules no scenario isolates."""

    def test_chip_coverage_bars_only_the_childrens_route(self):
        # NJ-22-0033 CS20's "Children's Program" bar: a pregnant woman reporting CHIP
        # coverage is still measured on the pregnancy route (spec `no_other_coverage_nj`).
        screen = self.household(2, 27, 54_367, pregnant=True)
        self.add_member(screen, "spouse", 29)
        self.add_insurance(self.head, chp=True, none=False)
        self.assertTrue(self.calculate(screen).eligible)

    def test_medicare_bars_a_child(self):
        screen = self.couple_with_child(60_000, 8)
        self.add_insurance(self.child, medicare=True, none=False)
        self.assert_ineligible(self.calculate(screen))

    def test_child_and_pregnant_mother_both_eligible_value_only_the_child(self):
        # 200% of a family of 4, 195 after the disregard: above 194 for her, above 142 for the child.
        screen = self.household(3, 30, 66_000, pregnant=True)
        self.add_member(screen, "spouse", 32)
        child = self.add_member(screen, "child", 6)
        e = self.calculate(screen)
        self.assert_eligible(e, monthly(326))
        self.assertTrue(self.member_result(e, self.head).eligible)
        self.assertEqual(self.member_result(e, self.head).value, 0)
        self.assertEqual(self.member_result(e, child).value, monthly(326))

    def test_ssi_and_child_support_do_not_count(self):
        # Scenario 1's family with 40,000 more in SSI and child support stays in the band.
        screen = self.couple_with_child(60_000, 8)
        self.add_income(self.head, 20_000, income_type="sSI", frequency="yearly")
        self.add_income(self.head, 20_000, income_type="childSupport", frequency="yearly")
        self.assert_eligible(self.calculate(screen), monthly(326))

    def test_missing_household_size_drops_the_program(self):
        from programs.util import DependencyError

        screen = self.couple_with_child(60_000, 8)
        with self.assertRaises(DependencyError):
            self.calculate(screen, missing=("household_size",))

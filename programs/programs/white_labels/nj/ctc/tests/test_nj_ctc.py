"""
NJ Child Tax Credit.

Builds real Screen/HouseholdMember/IncomeStream rows and runs the real `calc()`. Every spec §8
scenario has a test named for it; the rest cover the filers, the exempt types, a missing age,
the year fallback and the missing-field guard.

Ages in the spec are ages at the end of the tax year, so members are built from a birth month
rather than today's age.
"""

from datetime import date
from unittest.mock import PropertyMock, patch

from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from programs.programs.white_labels.nj.ctc.calculator import NjCtc
from programs.util import DependencyError
from screener.models import HouseholdMember, Screen


class NjCtcTestCase(CustomCalculatorTestCase):
    calculator_class = NjCtc
    white_label_code = "nj"
    state_code = "NJ"
    default_zipcode = "07102"
    default_county = "Essex County"
    fpl_year = "2025"

    @property
    def tax_year(self) -> int:
        return int(self.fpl_year)

    def member(self, screen: Screen, relationship: str, age: int, month: int = 6, **kwargs) -> HouseholdMember:
        """A member whose `age` is their age at the end of the tax year, born in `month`."""
        born = date(self.tax_year - age, month, 1)
        return self.add_member(screen, relationship, None, birth_year_month=born, **kwargs)

    def parent_and_child(
        self, wages: int, child_age: int = 3, relationship: str = "child", child_month: int = 6
    ) -> tuple[Screen, HouseholdMember, HouseholdMember]:
        screen = self.make_screen(household_size=2)
        head = self.member(screen, "headOfHousehold", 30, yearly_income=wages)
        child = self.member(screen, relationship, child_age, month=child_month)
        return screen, head, child

    def assertValue(self, screen: Screen, value: int) -> None:
        e = self.calculate(screen)
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, value)

    def assertIneligible(self, screen: Screen) -> None:
        e = self.calculate(screen)
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)


class TestRegistration(NjCtcTestCase):
    def test_program_code(self):
        self.assertEqual(NjCtc.program_code, "nj_ctc")

    def test_constants(self):
        self.assertEqual((NjCtc.income_limit, NjCtc.child_age_limit), (80_000, 6))
        self.assertEqual(NjCtc.qualifying_relative_income_limits, {2025: 5_200, 2026: 5_300})
        self.assertNotIn("veteran", NjCtc.nj_exempt_income_types)
        self.assertIn("sSI", NjCtc.nj_exempt_income_types)

    def test_missing_income_amount_drops_the_program(self):
        screen, _, _ = self.parent_and_child(24_000)

        with self.assertRaises(DependencyError):
            self.calculate(screen, missing=("income_amount",))


class TestSpecScenarios(NjCtcTestCase):
    def test_1_single_parent_with_one_young_child(self):
        self.assertValue(self.parent_and_child(24_000)[0], 1_000)

    def test_2_income_exactly_30000(self):
        self.assertValue(self.parent_and_child(30_000)[0], 1_000)

    def test_3_income_30001(self):
        self.assertValue(self.parent_and_child(30_001)[0], 800)

    def test_4_income_exactly_40000(self):
        self.assertValue(self.parent_and_child(40_000)[0], 800)

    def test_5_income_40001(self):
        self.assertValue(self.parent_and_child(40_001)[0], 600)

    def test_6_income_50001(self):
        self.assertValue(self.parent_and_child(50_001)[0], 400)

    def test_7_income_60001(self):
        self.assertValue(self.parent_and_child(60_001)[0], 200)

    def test_8_income_exactly_at_the_80000_limit(self):
        self.assertValue(self.parent_and_child(80_000)[0], 200)

    def test_9_income_80001(self):
        self.assertIneligible(self.parent_and_child(80_001)[0])

    def test_10_child_aged_5_at_the_end_of_the_tax_year(self):
        self.assertValue(self.parent_and_child(24_000, child_age=5)[0], 1_000)

    def test_11_child_aged_6_at_the_end_of_the_tax_year(self):
        # Turned 6 in December of the tax year.
        self.assertIneligible(self.parent_and_child(24_000, child_age=6, child_month=12)[0])

    def test_12_child_who_has_turned_6_since_the_tax_year_ended(self):
        screen, _, child = self.parent_and_child(24_000, child_age=5, child_month=1)
        # Pin the screening date after the January birthday that follows the tax year.
        with patch.object(Screen, "get_reference_date", lambda _self: date(2026, 10, 1)):
            self.assertEqual(child.calc_age(), 6)
            self.assertValue(screen, 1_000)

    def test_13_unrelated_young_child_in_the_household(self):
        self.assertIneligible(self.parent_and_child(24_000, relationship="roommate")[0])

    def test_14_young_relative_who_is_not_the_taxpayers_qualifying_child(self):
        self.assertValue(self.parent_and_child(24_000, relationship="relatedOther")[0], 1_000)

    def test_15_three_children_two_under_6(self):
        screen = self.make_screen(household_size=4)
        self.member(screen, "headOfHousehold", 35, yearly_income=24_000)
        self.member(screen, "child", 3)
        self.member(screen, "child", 1)
        self.member(screen, "child", 7)
        self.assertValue(screen, 2_000)

    def test_16_young_relative_whose_own_income_reaches_the_exemption_amount(self):
        screen, _, relative = self.parent_and_child(24_000, relationship="relatedOther")
        self.add_income(relative, 5_200, "investment", "yearly")
        self.assertIneligible(screen)

    def test_20_two_earners_whose_combined_income_crosses_the_limit(self):
        screen = self.make_screen(household_size=3)
        self.member(screen, "headOfHousehold", 32, yearly_income=45_000)
        self.member(screen, "spouse", 31, yearly_income=36_000)
        self.member(screen, "child", 3)
        self.assertIneligible(screen)

    def test_21_income_new_jersey_does_not_tax(self):
        screen, head, _ = self.parent_and_child(24_000)
        self.add_income(head, 60_000, "childSupport", "yearly")
        self.assertValue(screen, 1_000)


class TestSpecScenarios2026(NjCtcTestCase):
    fpl_year = "2026"

    def test_17_same_household_on_the_2026_to_2028_schedule(self):
        self.assertValue(self.parent_and_child(24_000)[0], 1_250)

    def test_18_top_bracket_on_the_2026_to_2028_schedule(self):
        self.assertValue(self.parent_and_child(60_001)[0], 250)

    def test_19_relatives_income_between_the_2025_and_2026_exemption_amounts(self):
        screen, _, relative = self.parent_and_child(24_000, relationship="relatedOther")
        self.add_income(relative, 5_200, "investment", "yearly")
        self.assertValue(screen, 1_250)

    def test_higher_schedule_brackets(self):
        for wages, credit in ((30_000, 1_250), (30_001, 1_000), (40_001, 750), (50_001, 500), (80_000, 250)):
            with self.subTest(wages=wages):
                self.assertValue(self.parent_and_child(wages)[0], credit)

    def test_relative_at_the_2026_exemption_amount(self):
        screen, _, relative = self.parent_and_child(24_000, relationship="relatedOther")
        self.add_income(relative, 5_300, "investment", "yearly")
        self.assertIneligible(screen)


@patch.object(NjCtc, "tax_year", new_callable=PropertyMock, return_value=2029)
class TestLaterTaxYears(NjCtcTestCase):
    # No FPL row exists for 2029, so the tax year is patched rather than set on the program.
    tax_year = 2029

    def test_2029_returns_to_the_standard_schedule(self, _tax_year):
        self.assertValue(self.parent_and_child(24_000)[0], 1_000)

    @patch("programs.programs.white_labels.nj.ctc.calculator.capture_message")
    def test_year_without_an_exemption_amount_uses_the_latest_and_reports(self, capture, _tax_year):
        screen, _, relative = self.parent_and_child(24_000, relationship="relatedOther")
        self.add_income(relative, 5_250, "investment", "yearly")

        self.assertValue(screen, 1_000)
        capture.assert_called_once()


class TestIncome(NjCtcTestCase):
    def couple(self, partner: str, partner_wages: int) -> Screen:
        screen = self.make_screen(household_size=3)
        self.member(screen, "headOfHousehold", 32, yearly_income=50_000)
        self.member(screen, partner, 31, yearly_income=partner_wages)
        self.member(screen, "child", 3)
        return screen

    def test_domestic_partner_income_is_not_counted(self):
        # A domestic partner files their own New Jersey return.
        self.assertValue(self.couple("domesticPartner", 40_000), 600)

    def test_spouse_income_is_counted(self):
        self.assertValue(self.couple("spouse", 25_000), 200)

    def test_other_members_income_is_not_counted(self):
        screen, _, _ = self.parent_and_child(24_000)
        self.member(screen, "parent", 60, yearly_income=70_000)
        self.assertValue(screen, 1_000)

    def test_ssi_is_not_counted(self):
        screen, head, _ = self.parent_and_child(24_000)
        self.add_income(head, 60_000, "sSI", "yearly")
        self.assertValue(screen, 1_000)

    def test_veteran_income_is_counted(self):
        screen, head, _ = self.parent_and_child(24_000)
        self.add_income(head, 10_000, "veteran", "yearly")
        self.assertValue(screen, 800)

    def test_each_nj_exempt_type_is_left_out(self):
        for income_type in NjCtc.nj_exempt_income_types:
            with self.subTest(income_type=income_type):
                screen, head, _ = self.parent_and_child(24_000)
                self.add_income(head, 60_000, income_type, "yearly")
                self.assertValue(screen, 1_000)


class TestChildren(NjCtcTestCase):
    def test_each_qualifying_child_relationship(self):
        for relationship in NjCtc.child_relationships:
            with self.subTest(relationship=relationship):
                self.assertValue(self.parent_and_child(24_000, relationship=relationship)[0], 1_000)

    def test_qualifying_child_with_income_still_counts(self):
        # No support or income test is evaluated on the qualifying-child route.
        screen, _, child = self.parent_and_child(24_000)
        self.add_income(child, 6_000, "investment", "yearly")
        self.assertValue(screen, 1_000)

    def test_relatives_untaxed_income_is_left_out(self):
        screen, _, relative = self.parent_and_child(24_000, relationship="relatedOther")
        self.add_income(relative, 9_000, "sSDependent", "yearly")
        self.assertValue(screen, 1_000)

    def test_relative_just_under_the_exemption_amount(self):
        screen, _, relative = self.parent_and_child(24_000, relationship="relatedOther")
        self.add_income(relative, 5_199, "investment", "yearly")
        self.assertValue(screen, 1_000)

    def test_child_born_after_the_tax_year_is_not_counted(self):
        screen, _, _ = self.parent_and_child(24_000, child_age=7)
        self.add_member(screen, "child", None, birth_year_month=date(2026, 1, 1))
        self.assertIneligible(screen)

    def test_child_born_in_december_of_the_tax_year_counts(self):
        screen, _, _ = self.parent_and_child(24_000, child_age=0, child_month=12)
        self.assertValue(screen, 1_000)

    def test_member_with_no_age_is_not_counted(self):
        screen, _, _ = self.parent_and_child(24_000, child_age=7)
        self.add_member(screen, "child", None)
        self.assertIneligible(screen)

    def test_age_without_a_birth_month_reads_the_reported_age(self):
        for age, eligible in ((5, True), (6, False)):
            with self.subTest(age=age):
                screen = self.make_screen(household_size=2)
                self.member(screen, "headOfHousehold", 30, yearly_income=24_000)
                self.add_member(screen, "child", age, birth_year_month=None)
                self.assertEqual(self.calculate(screen).eligible, eligible)

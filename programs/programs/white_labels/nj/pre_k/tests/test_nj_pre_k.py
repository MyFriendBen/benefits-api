"""
NJ Pre-K, tested against the spec's §8 scenarios. Spec: program-ops
`programs/white_labels/nj/pre_k/nj_pre_k_spec.md`.

The scenarios are dated "this school year". They are pinned to November 15, 2026, so the school
year under way began in 2026 and October 1, 2026 and October 1, 2027 are the two age dates.
Scenarios 9 and 10 pin June 30 and July 1, 2027 on either side of the school-year switch.
"""

from datetime import date
from typing import Optional

from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from programs.programs.white_labels.nj.pre_k.calculator import NjPreK
from programs.util import DependencyError
from screener.models import Screen

# Spec §7's weighted value for each county.
SPEC_COUNTY_VALUES = {
    "Atlantic County": 16_462,
    "Bergen County": 17_070,
    "Burlington County": 16_725,
    "Camden County": 16_587,
    "Cape May County": 16_014,
    "Cumberland County": 16_185,
    "Essex County": 17_386,
    "Gloucester County": 16_479,
    "Hudson County": 17_562,
    "Hunterdon County": 17_126,
    "Mercer County": 17_131,
    "Middlesex County": 17_061,
    "Monmouth County": 16_903,
    "Morris County": 17_287,
    "Ocean County": 16_436,
    "Passaic County": 16_802,
    "Salem County": 16_479,
    "Somerset County": 17_586,
    "Sussex County": 16_768,
    "Union County": 17_292,
    "Warren County": 16_406,
}


class NjPreKTestCase(CustomCalculatorTestCase):
    calculator_class = NjPreK
    white_label_code = "nj"
    state_code = "NJ"
    default_zipcode = "07102"
    default_county = "Essex County"
    needs_program_row = False
    stores_age = False

    reference_date = date(2026, 11, 15)

    def household(
        self,
        *child_births: Optional[date],
        county: str = "Essex County",
        zipcode: str = "07102",
        adult_age: int = 31,
        wages: int = 3_200,
    ) -> Screen:
        """A head of household with wages and one child per birth month given."""
        screen = self.make_screen(household_size=1 + len(child_births), county=county, zipcode=zipcode)
        self.add_member(screen, age=adult_age, monthly_income=wages)
        for birth in child_births:
            self.add_member(screen, "child", age=None, birth_year_month=birth)

        return screen


class TestNjPreKScenarios(NjPreKTestCase):
    def test_scenario_1_four_year_old_in_essex(self) -> None:
        screen = self.household(date(2022, 3, 1))

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 17_386)

    def test_scenario_2_four_year_old_turning_five_in_november(self) -> None:
        # 4 on October 1, 2026, and already 5 on the screening date.
        screen = self.household(date(2021, 11, 1), county="Camden County", zipcode="08102", adult_age=35, wages=4_100)

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 16_587)

    def test_scenario_3_five_year_old_who_turned_five_in_september(self) -> None:
        screen = self.household(date(2021, 9, 1), county="Mercer County", zipcode="08608", adult_age=33, wages=3_600)

        e = self.calculate(screen)

        self.assertFalse(e.eligible)

    def test_scenario_4_two_year_old_turning_three_next_september(self) -> None:
        # 2 on October 1, 2026; 3 on October 1, 2027.
        screen = self.household(date(2024, 9, 1), county="Hudson County", zipcode="07302", adult_age=29, wages=2_900)

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 17_562)

    def test_scenario_5_child_who_is_two_on_october_1_next_school_year(self) -> None:
        # 1 on October 1, 2026; 2 on October 1, 2027.
        screen = self.household(date(2024, 11, 1), adult_age=30, wages=3_000)

        e = self.calculate(screen)

        self.assertFalse(e.eligible)

    def test_scenario_6_october_birthday_turning_three_next_october(self) -> None:
        # Born October 2024: counted as 3 on October 1, 2027, whatever the day of birth.
        screen = self.household(date(2024, 10, 1), county="Bergen County", zipcode="07601", adult_age=32, wages=3_800)

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 17_070)

    def test_scenario_7_october_birthday_turning_five_this_october(self) -> None:
        # Born October 2021: counted as 5 on October 1, 2026, whatever the day of birth.
        screen = self.household(date(2021, 10, 1), adult_age=34, wages=3_400)

        e = self.calculate(screen)

        self.assertFalse(e.eligible)

    def test_scenario_8_two_eligible_children(self) -> None:
        screen = self.household(date(2022, 5, 1), date(2023, 2, 1), adult_age=36, wages=5_000)

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 34_772)


class TestNjPreKLastDayOfSchoolYear(NjPreKTestCase):
    reference_date = date(2027, 6, 30)

    def test_scenario_9_one_year_old_screened_june_30(self) -> None:
        # The school year under way began in 2026: 1 on October 1, 2026, and 2 on October 1, 2027.
        screen = self.household(date(2025, 8, 1), adult_age=30, wages=3_000)

        e = self.calculate(screen)

        self.assertFalse(e.eligible)


class TestNjPreKFirstDayOfSchoolYear(NjPreKTestCase):
    reference_date = date(2027, 7, 1)

    def test_scenario_10_same_child_screened_july_1(self) -> None:
        # The school year under way began in 2027: 2 on October 1, 2027, and 3 on October 1, 2028.
        screen = self.household(date(2025, 8, 1), adult_age=30, wages=3_000)

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 17_386)


class TestNjPreKRules(NjPreKTestCase):
    def test_program_code_matches_the_record(self) -> None:
        self.assertEqual(NjPreK.program_code, "nj_pre_k")

    def test_household_without_a_preschooler_is_ineligible(self) -> None:
        screen = self.household(date(2018, 4, 1))

        e = self.calculate(screen)

        self.assertFalse(e.eligible)

    def test_only_the_preschooler_is_valued(self) -> None:
        screen = self.household(date(2022, 3, 1), date(2018, 4, 1))

        e = self.calculate(screen)

        values = {m.member.birth_year_month: (m.eligible, m.value) for m in e.eligible_members}
        self.assertEqual(values[date(2022, 3, 1)], (True, 17_386))
        self.assertFalse(values[date(2018, 4, 1)][0])
        self.assertEqual(e.value, 17_386)

    def test_no_income_test(self) -> None:
        screen = self.household(date(2022, 3, 1), wages=25_000)

        e = self.calculate(screen)

        self.assertTrue(e.eligible)

    def test_child_without_a_birth_month_gets_no_result(self) -> None:
        screen = self.household(None)

        with self.assertRaises(DependencyError):
            self.calculate(screen)

    def test_any_member_without_a_birth_month_gets_no_result(self) -> None:
        screen = self.household(date(2022, 3, 1))
        self.add_member(screen, "spouse", age=None, birth_year_month=None)

        with self.assertRaises(DependencyError):
            self.calculate(screen)

    def test_missing_county_gets_no_result(self) -> None:
        screen = self.household(date(2022, 3, 1))

        with self.assertRaises(DependencyError):
            self.calculate(screen, missing=("county",))

    def test_county_outside_the_table_raises(self) -> None:
        screen = self.household(date(2022, 3, 1), county="Kings County")

        with self.assertRaises(KeyError):
            self.calculate(screen)

    def test_every_county_matches_the_spec(self) -> None:
        self.assertEqual(set(NjPreK.county_rates), set(SPEC_COUNTY_VALUES))

        for county, expected in SPEC_COUNTY_VALUES.items():
            with self.subTest(county=county):
                screen = self.household(date(2022, 3, 1), county=county)

                self.assertEqual(self.calculate(screen).value, expected)

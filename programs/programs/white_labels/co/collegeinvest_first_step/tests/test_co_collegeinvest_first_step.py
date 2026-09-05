from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from datetime import date


from programs.programs.white_labels.co.collegeinvest_first_step.calculator import CoCollegeInvestFirstStep


class TestCoCollegeInvestFirstStep(CustomCalculatorTestCase):
    calculator_class = CoCollegeInvestFirstStep
    white_label_code = "co"
    state_code = "CO"
    needs_program_row = False
    default_zipcode = "80202"
    default_county = "Denver County"

    # --- class attributes ---

    def test_member_amount_is_121(self):
        self.assertEqual(CoCollegeInvestFirstStep.member_amount, 121)

    # --- eligible ---

    def test_eligible_newborn(self):
        """Denver family with newborn child (born 2026, age 0) is eligible."""
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", 34)
        self.add_member(screen, "child", 0, birth_year_month=date(2026, 1, 1))

        calc = self.make_calculator(screen)
        eligibility = calc.eligible()

        self.assertTrue(eligibility.eligible)

    def test_eligible_child_age_7_boundary(self):
        """Child exactly age 7 is still eligible."""
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", 35)
        self.add_member(screen, "child", 7, birth_year_month=date(2020, 1, 1))

        calc = self.make_calculator(screen)
        eligibility = calc.eligible()

        self.assertTrue(eligibility.eligible)

    def test_eligible_min_birth_year_boundary(self):
        """Child born January 2020 (minimum birth year) is eligible."""
        screen = self.make_screen(zipcode="80903", county="El Paso County", household_size=2)
        self.add_member(screen, "headOfHousehold", 35)
        self.add_member(screen, "child", 6, birth_year_month=date(2020, 1, 1))

        calc = self.make_calculator(screen)
        eligibility = calc.eligible()

        self.assertTrue(eligibility.eligible)

    def test_eligible_step_child(self):
        """stepChild relationship qualifies."""
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", 35)
        self.add_member(screen, "stepChild", 3, birth_year_month=date(2023, 1, 1))

        calc = self.make_calculator(screen)
        eligibility = calc.eligible()

        self.assertTrue(eligibility.eligible)

    def test_eligible_foster_child(self):
        """fosterChild relationship qualifies."""
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", 35)
        self.add_member(screen, "fosterChild", 2, birth_year_month=date(2024, 1, 1))

        calc = self.make_calculator(screen)
        eligibility = calc.eligible()

        self.assertTrue(eligibility.eligible)

    def test_eligible_grandchild(self):
        """grandChild relationship qualifies."""
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", 50)
        self.add_member(screen, "grandChild", 1, birth_year_month=date(2025, 1, 1))

        calc = self.make_calculator(screen)
        eligibility = calc.eligible()

        self.assertTrue(eligibility.eligible)

    # --- ineligible ---

    def test_ineligible_child_too_old(self):
        """Child aged 8 or older is not eligible — primary exclusion."""
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", 36)
        self.add_member(screen, "child", 9, birth_year_month=date(2017, 1, 1))

        calc = self.make_calculator(screen)
        eligibility = calc.eligible()

        self.assertFalse(eligibility.eligible)

    def test_ineligible_child_age_8_boundary(self):
        """Child exactly age 8 is not eligible."""
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", 35)
        self.add_member(screen, "child", 8, birth_year_month=date(2018, 1, 1))

        calc = self.make_calculator(screen)
        eligibility = calc.eligible()

        self.assertFalse(eligibility.eligible)

    def test_ineligible_birth_year_2019(self):
        """Child born in 2019 (age ≤ 7) is excluded by the birth year cutoff."""
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", 35)
        self.add_member(screen, "child", 6, birth_year_month=date(2019, 6, 1))

        calc = self.make_calculator(screen)
        eligibility = calc.eligible()

        self.assertFalse(eligibility.eligible)

    def test_ineligible_no_children(self):
        """Household with no children is not eligible."""
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", 38)
        self.add_member(screen, "spouse", 35)

        calc = self.make_calculator(screen)
        eligibility = calc.eligible()

        self.assertFalse(eligibility.eligible)

    def test_ineligible_non_child_relationship(self):
        """Members with non-child relationships do not qualify."""
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", 5, birth_year_month=date(2021, 1, 1))
        self.add_member(screen, "sibling", 3, birth_year_month=date(2023, 1, 1))

        calc = self.make_calculator(screen)
        eligibility = calc.eligible()

        self.assertFalse(eligibility.eligible)

    # --- benefit value ---

    def test_value_single_eligible_child(self):
        """Single eligible child yields $121."""
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", 34)
        self.add_member(screen, "child", 0, birth_year_month=date(2026, 1, 1))

        calc = self.make_calculator(screen)
        eligibility = calc.eligible()
        calc.value(eligibility)

        self.assertEqual(eligibility.value, 121)

    def test_value_two_eligible_children(self):
        """Two eligible children yield $242 (2 × $121)."""
        screen = self.make_screen(household_size=4)
        self.add_member(screen, "headOfHousehold", 35)
        self.add_member(screen, "spouse", 34)
        self.add_member(screen, "child", 3, birth_year_month=date(2023, 2, 1))
        self.add_member(screen, "child", 0, birth_year_month=date(2026, 3, 1))

        calc = self.make_calculator(screen)
        eligibility = calc.eligible()
        calc.value(eligibility)

        self.assertEqual(eligibility.value, 242)

    def test_value_mixed_eligible_and_ineligible_children(self):
        """Only qualifying children count toward the value; over-age child excluded."""
        screen = self.make_screen(household_size=3)
        self.add_member(screen, "headOfHousehold", 35)
        self.add_member(screen, "child", 9, birth_year_month=date(2017, 1, 1))
        self.add_member(screen, "child", 2, birth_year_month=date(2024, 1, 1))

        calc = self.make_calculator(screen)
        eligibility = calc.eligible()
        calc.value(eligibility)

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 121)

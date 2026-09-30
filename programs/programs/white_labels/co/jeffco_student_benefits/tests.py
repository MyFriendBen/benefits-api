from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from unittest.mock import Mock
from programs.programs.white_labels.co.jeffco_student_benefits.calculator import JeffcoStudentBenefits


class TestJeffcoStudentBenefits(CustomCalculatorTestCase):
    calculator_class = JeffcoStudentBenefits
    white_label_code = "co"
    state_code = "CO"
    default_zipcode = "80401"
    default_county = "Jefferson County"
    needs_program_row = False

    def test_eligible_jefferson_county_with_eligible_child(self):
        """Household in Jefferson County with child aged 3-19 is eligible"""
        screen = self.make_screen(household_size=2, zipcode="80401", county="Jefferson County")
        self.add_member(screen, "headOfHousehold", 35)
        self.add_member(screen, "child", 10)

        calculator = self.make_calculator(screen)
        eligibility = calculator.eligible()

        self.assertTrue(eligibility.eligible)

    def test_eligible_child_age_3_boundary(self):
        """Child exactly age 3 is eligible"""
        screen = self.make_screen(household_size=2, zipcode="80401", county="Jefferson County")
        self.add_member(screen, "headOfHousehold", 30)
        self.add_member(screen, "child", 3)

        calculator = self.make_calculator(screen)
        eligibility = calculator.eligible()

        self.assertTrue(eligibility.eligible)

    def test_eligible_child_age_19_boundary(self):
        """Child exactly age 19 is eligible"""
        screen = self.make_screen(household_size=2, zipcode="80401", county="Jefferson County")
        self.add_member(screen, "headOfHousehold", 45)
        self.add_member(screen, "child", 19)

        calculator = self.make_calculator(screen)
        eligibility = calculator.eligible()

        self.assertTrue(eligibility.eligible)

    def test_not_eligible_wrong_county(self):
        """Household not in Jefferson County is not eligible"""
        screen = self.make_screen(household_size=2, zipcode="80205", county="Denver County")
        self.add_member(screen, "headOfHousehold", 35)
        self.add_member(screen, "child", 10)

        calculator = self.make_calculator(screen)
        eligibility = calculator.eligible()

        self.assertFalse(eligibility.eligible)

    def test_not_eligible_child_too_young(self):
        """Child under age 3 is not eligible"""
        screen = self.make_screen(household_size=2, zipcode="80401", county="Jefferson County")
        self.add_member(screen, "headOfHousehold", 30)
        self.add_member(screen, "child", 2)

        calculator = self.make_calculator(screen)
        eligibility = calculator.eligible()

        self.assertFalse(eligibility.eligible)

    def test_not_eligible_child_too_old(self):
        """Child over age 19 is not eligible"""
        screen = self.make_screen(household_size=2, zipcode="80401", county="Jefferson County")
        self.add_member(screen, "headOfHousehold", 50)
        self.add_member(screen, "child", 20)

        calculator = self.make_calculator(screen)
        eligibility = calculator.eligible()

        self.assertFalse(eligibility.eligible)

    def test_not_eligible_no_children(self):
        """Household with no children is not eligible"""
        screen = self.make_screen(household_size=1, zipcode="80401", county="Jefferson County")
        self.add_member(screen, "headOfHousehold", 35)

        calculator = self.make_calculator(screen)
        eligibility = calculator.eligible()

        self.assertFalse(eligibility.eligible)

    def test_value_is_500(self):
        """Program value should be $500"""
        screen = self.make_screen(household_size=2, zipcode="80401", county="Jefferson County")
        self.add_member(screen, "headOfHousehold", 35)
        self.add_member(screen, "child", 10)

        calculator = self.make_calculator(screen)
        eligibility = calculator.eligible()
        calculator.value(eligibility)

        self.assertEqual(eligibility.value, 500)

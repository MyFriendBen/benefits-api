from django.test import TestCase
from programs.programs.co.universal_preschool.calculator import UniversalPreschool
from screener.models import Screen, HouseholdMember, IncomeStream, WhiteLabel
from programs.models import Program, FederalPoveryLimit
from programs.programs.calc import Eligibility
from programs.util import Dependencies


class TestCoUniversalPreschool(TestCase):
    """Test cases for Colorado Universal Preschool Program calculator"""

    @classmethod
    def setUpTestData(cls):
        """Set up test data that doesn't change between tests"""
        # Create white label for Colorado
        cls.co_white_label = WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")

        # Create FPL year for testing
        cls.fpl_year = FederalPoveryLimit.objects.create(year="2025", period="2025")

        # Create program using the manager method
        cls.program = Program.objects.new_program(white_label="co", name_abbreviated="upk")
        # Set the FPL year for the program
        cls.program.year = cls.fpl_year
        cls.program.save()

    def create_calculator(self, screen):
        """Helper method to create calculator instance with required dependencies"""
        data = {}
        missing_dependencies = Dependencies()
        return UniversalPreschool(screen, self.program, data, missing_dependencies)

    def test_member_value_3yo_foster_child_income_270_fpl_returns_10_hours(self):
        """Test 3-year-old foster child with HH income 270% FPL or less returns 10 hours"""

        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="80016",
            county="Elbert County",
            household_size=2,
            white_label=self.co_white_label,
            completed=False,
        )

        parent = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=32,
            has_income=True,
        )

        # Add income below 270% FPL
        IncomeStream.objects.create(
            screen=screen,
            household_member=parent,
            type="wages",
            amount=4500,  # 54,000/yearly
            frequency="monthly",
        )

        # Eligible child (3 years old and foster child)
        child = HouseholdMember.objects.create(
            screen=screen,
            relationship="fosterChild",
            age=3,
            has_income=False,
        )

        calc = self.create_calculator(screen)
        eligibility = calc.eligible()
        value = calc.member_value(child)
        self.assertTrue(eligibility.eligible)
        self.assertEqual(value, UniversalPreschool.amount_10_hr)

    def test_member_value_3yo_income_100_fpl_returns_10_hours(self):
        """Test 3-year-old child with HH income ≤100% FPL returns 10 hours"""

        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="80016",
            county="Elbert County",
            household_size=2,
            white_label=self.co_white_label,
            completed=False,
        )

        parent = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=32,
            has_income=True,
        )

        # Add income below 100% FPL
        IncomeStream.objects.create(
            screen=screen,
            household_member=parent,
            type="wages",
            amount=1700,  # 20,400/yearly
            frequency="monthly",
        )

        # Eligible child (3 years old)
        child = HouseholdMember.objects.create(
            screen=screen,
            relationship="child",
            age=3,
            has_income=False,
        )

        calc = self.create_calculator(screen)
        eligibility = calc.eligible()
        value = calc.member_value(child)
        self.assertTrue(eligibility.eligible)
        self.assertEqual(value, UniversalPreschool.amount_10_hr)

    def test_member_value_4yo_foster_income_270_fpl_returns_30_hours(self):
        """Test 4-year-old foster child with HH income 270% FPL or less returns 30 hours"""

        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="80016",
            county="Elbert County",
            household_size=3,
            white_label=self.co_white_label,
            completed=False,
        )

        parent = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=32,
            has_income=True,
        )

        # Add income below 270% FPL
        IncomeStream.objects.create(
            screen=screen,
            household_member=parent,
            type="wages",
            amount=5600,  # 67,200 yearly
            frequency="monthly",
        )

        # Eligible child (4 years old and foster child)
        child = HouseholdMember.objects.create(
            screen=screen,
            relationship="fosterChild",
            age=4,
            has_income=False,
        )

        spouse = HouseholdMember.objects.create(
            screen=screen,
            relationship="spouse",
            age=21,
            has_income=False,
        )

        calc = self.create_calculator(screen)
        eligibility = calc.eligible()
        value = calc.member_value(child)
        self.assertTrue(eligibility.eligible)
        self.assertEqual(value, UniversalPreschool.amount_30_hr)

    def test_member_value_4yo_income_100_fpl_returns_30_hours(self):
        """Test 4-year-old child with HH income 100% FPL or less returns 30 hours"""

        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="80016",
            county="Elbert County",
            household_size=2,
            white_label=self.co_white_label,
            completed=False,
        )

        parent = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=32,
            has_income=True,
        )

        # Add income below 100% FPL
        IncomeStream.objects.create(
            screen=screen,
            household_member=parent,
            type="wages",
            amount=1700,  # 20,400 yearly
            frequency="monthly",
        )

        # Eligible child (4 years old)
        child = HouseholdMember.objects.create(
            screen=screen,
            relationship="child",
            age=4,
            has_income=False,
        )

        calc = self.create_calculator(screen)
        eligibility = calc.eligible()
        value = calc.member_value(child)
        self.assertTrue(eligibility.eligible)
        self.assertEqual(value, UniversalPreschool.amount_30_hr)

    def test_member_value_4yo_non_qualifying_returns_15_hours(self):
        """Test 4-year-old child with HH income above 270% FPL returns 15 hours"""

        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="80016",
            county="Elbert County",
            household_size=2,
            white_label=self.co_white_label,
            completed=False,
        )

        parent = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=32,
            has_income=True,
        )

        # Add income above 270% FPL
        IncomeStream.objects.create(
            screen=screen,
            household_member=parent,
            type="wages",
            amount=5000,  # 60,000 yearly
            frequency="monthly",
        )
        # Eligible child (4 years old)
        child = HouseholdMember.objects.create(
            screen=screen,
            relationship="child",
            age=4,
            has_income=False,
        )

        calc = self.create_calculator(screen)
        eligibility = calc.eligible()
        value = calc.member_value(child)
        self.assertTrue(eligibility.eligible)
        self.assertEqual(value, UniversalPreschool.amount_15_hr)

    # Eligibility Tests
    def test_eligibility_3yo_above_270_fpl_not_eligible(self):
        """Test 3-year-old child with HH income above 270% FPL is not eligible"""
        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="80016",
            county="Elbert County",
            household_size=2,
            white_label=self.co_white_label,
            completed=False,
        )

        parent = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=32,
            has_income=True,
        )

        IncomeStream.objects.create(
            screen=screen,
            household_member=parent,
            type="wages",
            amount=5000,  # 60,000
            frequency="monthly",
        )

        child = HouseholdMember.objects.create(
            screen=screen,
            relationship="child",
            age=3,
            has_income=False,
        )

        calc = self.create_calculator(screen)
        eligibility = calc.eligible()
        self.assertFalse(eligibility.eligible)

    def test_age_2_not_eligible(self):
        """Test 2-year-old is not eligible (below minimum age)"""

        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="80016",
            county="Elbert County",
            household_size=2,
            white_label=self.co_white_label,
            completed=False,
        )

        parent = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=32,
            has_income=True,
        )

        child = HouseholdMember.objects.create(
            screen=screen,
            relationship="fosterChild",
            age=2,  # Too young!
            has_income=False,
        )

        calc = self.create_calculator(screen)
        eligibility = calc.eligible()
        self.assertFalse(eligibility.eligible)

    def test_age_5_not_eligible(self):
        """Test 5-year-old is not eligible (above maximum age)"""
        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="80016",
            county="Elbert County",
            household_size=2,
            white_label=self.co_white_label,
            completed=False,
        )

        parent = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=32,
            has_income=False,
        )

        child = HouseholdMember.objects.create(
            screen=screen,
            relationship="child",
            age=5,
            has_income=False,
        )

        calc = self.create_calculator(screen)
        eligibility = calc.eligible()
        self.assertFalse(eligibility.eligible)

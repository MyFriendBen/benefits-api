from django.test import TestCase
from unittest.mock import Mock
from programs.programs.co.jeffco_student_benefits.calculator import JeffcoStudentBenefits
from programs.util import Dependencies
from screener.models import Screen, HouseholdMember, WhiteLabel


class TestJeffcoStudentBenefits(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(
            name="Colorado",
            code="co",
            state_code="CO",
        )
        self.mock_program = Mock()

    def test_eligible_jefferson_county_with_eligible_child(self):
        """Household in Jefferson County with child aged 3-19 is eligible"""
        screen = Screen.objects.create(
            white_label=self.white_label,
            agree_to_tos=True,
            zipcode="80401",
            county="Jefferson County",
            household_size=2,
            completed=False,
        )
        HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=35,
        )
        HouseholdMember.objects.create(
            screen=screen,
            relationship="child",
            age=10,
        )

        calculator = JeffcoStudentBenefits(screen, self.mock_program, {}, Dependencies())
        eligibility = calculator.eligible()

        self.assertTrue(eligibility.eligible)

    def test_eligible_child_age_3_boundary(self):
        """Child exactly age 3 is eligible"""
        screen = Screen.objects.create(
            white_label=self.white_label,
            agree_to_tos=True,
            zipcode="80401",
            county="Jefferson County",
            household_size=2,
            completed=False,
        )
        HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=30,
        )
        HouseholdMember.objects.create(
            screen=screen,
            relationship="child",
            age=3,
        )

        calculator = JeffcoStudentBenefits(screen, self.mock_program, {}, Dependencies())
        eligibility = calculator.eligible()

        self.assertTrue(eligibility.eligible)

    def test_eligible_child_age_19_boundary(self):
        """Child exactly age 19 is eligible"""
        screen = Screen.objects.create(
            white_label=self.white_label,
            agree_to_tos=True,
            zipcode="80401",
            county="Jefferson County",
            household_size=2,
            completed=False,
        )
        HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=45,
        )
        HouseholdMember.objects.create(
            screen=screen,
            relationship="child",
            age=19,
        )

        calculator = JeffcoStudentBenefits(screen, self.mock_program, {}, Dependencies())
        eligibility = calculator.eligible()

        self.assertTrue(eligibility.eligible)

    def test_not_eligible_wrong_county(self):
        """Household not in Jefferson County is not eligible"""
        screen = Screen.objects.create(
            white_label=self.white_label,
            agree_to_tos=True,
            zipcode="80205",
            county="Denver County",
            household_size=2,
            completed=False,
        )
        HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=35,
        )
        HouseholdMember.objects.create(
            screen=screen,
            relationship="child",
            age=10,
        )

        calculator = JeffcoStudentBenefits(screen, self.mock_program, {}, Dependencies())
        eligibility = calculator.eligible()

        self.assertFalse(eligibility.eligible)

    def test_not_eligible_child_too_young(self):
        """Child under age 3 is not eligible"""
        screen = Screen.objects.create(
            white_label=self.white_label,
            agree_to_tos=True,
            zipcode="80401",
            county="Jefferson County",
            household_size=2,
            completed=False,
        )
        HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=30,
        )
        HouseholdMember.objects.create(
            screen=screen,
            relationship="child",
            age=2,
        )

        calculator = JeffcoStudentBenefits(screen, self.mock_program, {}, Dependencies())
        eligibility = calculator.eligible()

        self.assertFalse(eligibility.eligible)

    def test_not_eligible_child_too_old(self):
        """Child over age 19 is not eligible"""
        screen = Screen.objects.create(
            white_label=self.white_label,
            agree_to_tos=True,
            zipcode="80401",
            county="Jefferson County",
            household_size=2,
            completed=False,
        )
        HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=50,
        )
        HouseholdMember.objects.create(
            screen=screen,
            relationship="child",
            age=20,
        )

        calculator = JeffcoStudentBenefits(screen, self.mock_program, {}, Dependencies())
        eligibility = calculator.eligible()

        self.assertFalse(eligibility.eligible)

    def test_not_eligible_no_children(self):
        """Household with no children is not eligible"""
        screen = Screen.objects.create(
            white_label=self.white_label,
            agree_to_tos=True,
            zipcode="80401",
            county="Jefferson County",
            household_size=1,
            completed=False,
        )
        HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=35,
        )

        calculator = JeffcoStudentBenefits(screen, self.mock_program, {}, Dependencies())
        eligibility = calculator.eligible()

        self.assertFalse(eligibility.eligible)

    def test_value_is_500(self):
        """Program value should be $500"""
        screen = Screen.objects.create(
            white_label=self.white_label,
            agree_to_tos=True,
            zipcode="80401",
            county="Jefferson County",
            household_size=2,
            completed=False,
        )
        HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=35,
        )
        HouseholdMember.objects.create(
            screen=screen,
            relationship="child",
            age=10,
        )

        calculator = JeffcoStudentBenefits(screen, self.mock_program, {}, Dependencies())
        eligibility = calculator.eligible()
        calculator.value(eligibility)

        self.assertEqual(eligibility.value, 500)

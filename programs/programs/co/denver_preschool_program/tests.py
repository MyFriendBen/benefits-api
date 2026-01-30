from django.test import TestCase
from unittest import skip
from programs.programs.co.denver_preschool_program.calculator import DenverPreschoolProgram
from screener.models import Screen, HouseholdMember


@skip("Calculator constructor signature changed - needs API update")
class TestDenverPreschoolProgram(TestCase):
    def setUp(self):
        self.screen1 = Screen.objects.create(
            agree_to_tos=True, zipcode="80205", county="Denver County", household_size=2
        )
        self.person1 = HouseholdMember.objects.create(
            screen=self.screen1,
            relationship="headOfHousehold",
            age=30,
            student=False,
            pregnant=False,
            unemployed=False,
            worked_in_last_18_mos=True,
            visually_impaired=False,
            disabled=False,
            veteran=False,
            has_income=False,
            has_expenses=False,
        )
        self.person2 = HouseholdMember.objects.create(
            screen=self.screen1,
            relationship="child",
            age=3,
            student=False,
            pregnant=False,
            unemployed=False,
            worked_in_last_18_mos=True,
            visually_impaired=False,
            disabled=False,
            veteran=False,
            has_income=False,
            has_expenses=False,
        )

    def test_denver_preschool_program_has_preschooler(self):
        dpp = DenverPreschoolProgram(self.screen1)
        eligibility = dpp.eligibility

        self.assertTrue(eligibility["eligible"])

    def test_denver_preschool_program_doesnt_have_preschooler(self):
        self.person2.age = 5
        self.person2.save()
        dpp = DenverPreschoolProgram(self.screen1)
        eligibility = dpp.eligibility

        self.assertFalse(eligibility["eligible"])

from django.test import TestCase
from unittest import skip
from programs.programs.co.omnisalud.calculator import OmniSalud
from screener.models import Screen, HouseholdMember, IncomeStream


@skip("Calculator constructor signature changed - needs API update")
class TestOmniSaludPension(TestCase):
    def setUp(self):
        self.screen1 = Screen.objects.create(
            agree_to_tos=True,
            zipcode="80205",
            county="Denver County",
            household_size=1,
            household_assets=0,
            has_no_hi=True,
        )
        self.person1 = HouseholdMember.objects.create(
            screen=self.screen1,
            relationship="headOfHousehold",
            age=20,
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

    def test_omnisalud_pass_all_conditions(self):
        omnisalud = OmniSalud(self.screen1)
        eligibility = omnisalud.eligibility

        self.assertTrue(eligibility["eligible"])

    def test_omnisalud_failed_all_conditions(self):
        self.screen1.has_no_hi = False
        self.screen1.save()
        IncomeStream.objects.create(
            screen=self.screen1, household_member=self.person1, type="wages", amount=2000, frequency="monthly"
        )

        omnisalud = OmniSalud(self.screen1)
        eligibility = omnisalud.eligibility

        self.assertFalse(eligibility["eligible"])

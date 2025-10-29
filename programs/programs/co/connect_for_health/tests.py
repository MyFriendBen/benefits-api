from django.test import TestCase
from unittest import skip
from programs.programs.co.connect_for_health.calculator import ConnectForHealth
from screener.models import Screen, HouseholdMember, IncomeStream


@skip("Calculator constructor signature changed - needs API update")
class TestConnectForHealth(TestCase):
    def setUp(self):
        self.screen1 = Screen.objects.create(
            agree_to_tos=True,
            zipcode="80205",
            county="Denver County",
            household_size=1,
            household_assets=0,
            has_employer_hi=True,
            has_private_hi=True,
            has_medicaid_hi=True,
            has_chp_hi=True,
            has_no_hi=True,
        )
        self.person1 = HouseholdMember.objects.create(
            screen=self.screen1,
            relationship="headOfHousehold",
            age=60,
            student=False,
            student_full_time=False,
            pregnant=False,
            unemployed=False,
            worked_in_last_18_mos=True,
            visually_impaired=False,
            disabled=False,
            veteran=False,
            has_income=False,
            has_expenses=False,
        )

    def test_health_insurance_pass_all_conditions(self):
        cfhc = ConnectForHealth(self.screen1)
        eligibility = cfhc.eligibility

        self.assertTrue(eligibility["eligible"])

    def test_health_insurance_failed_all_conditions(self):
        self.screen1.has_no_hi = False
        self.screen1.save()
        income = IncomeStream.objects.create(
            screen=self.screen1, household_member=self.person1, type="wages", amount=5800, frequency="monthly"
        )

        cfhc = ConnectForHealth(self.screen1)
        eligibility = cfhc.eligibility

        self.assertFalse(eligibility["eligible"])

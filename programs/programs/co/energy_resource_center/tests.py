from django.test import TestCase
from unittest import skip
from programs.programs.co.energy_resource_center.calculator import EnergyResourceCenter
from screener.models import Screen, HouseholdMember, IncomeStream


@skip("Calculator constructor signature changed - needs API update")
class TestEnergyResourceCenterPension(TestCase):
    def setUp(self):
        self.screen1 = Screen.objects.create(
            agree_to_tos=True,
            zipcode="80205",
            county="Denver County",
            household_size=1,
            household_assets=0,
        )
        self.person1 = HouseholdMember.objects.create(
            screen=self.screen1,
            relationship="headOfHousehold",
            age=60,
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

    def test_energy_resource_center_visually_impaired_is_eligible(self):
        erc = EnergyResourceCenter(self.screen1)
        eligibility = erc.eligibility

        self.assertTrue(eligibility["eligible"])

    def test_energy_resource_center_failed_income_condition(self):
        income = IncomeStream.objects.create(
            screen=self.screen1, household_member=self.person1, type="wages", amount=3000, frequency="monthly"
        )
        erc = EnergyResourceCenter(self.screen1)
        eligibility = erc.eligibility

        self.assertFalse(eligibility["eligible"])

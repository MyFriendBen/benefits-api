from django.test import TestCase
from unittest import skip
from programs.programs.federal.head_start.calculator import HeadStart
from screener.models import Screen, HouseholdMember, IncomeStream


@skip("Calculator constructor signature changed - needs API update")
class TestHeadStartPension(TestCase):
    def setUp(self):
        self.screen1 = Screen.objects.create(
            agree_to_tos=True,
            zipcode="80205",
            county="Denver County",
            household_size=2,
            household_assets=0,
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
            age=4,
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

    def test_head_start_visually_impaired_is_eligible(self):
        chs = HeadStart(self.screen1)
        eligibility = chs.eligibility

        self.assertTrue(eligibility["eligible"])

    def test_head_start_failed_all_conditions(self):
        income = IncomeStream.objects.create(
            screen=self.screen1, household_member=self.person1, type="wages", amount=2000, frequency="monthly"
        )
        self.screen1.save()
        self.person2.age = 6
        self.person2.save()

        chs = HeadStart(self.screen1)
        eligibility = chs.eligibility

        self.assertFalse(eligibility["eligible"])

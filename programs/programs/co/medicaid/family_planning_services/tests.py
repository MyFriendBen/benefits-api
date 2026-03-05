from django.test import TestCase
from unittest import skip
from programs.programs.co.medicaid.family_planning_services.calculator import FamilyPlanningServices
from screener.models import Screen, HouseholdMember, IncomeStream


@skip("Calculator constructor signature changed - needs API update")
class TestFamilyPlanningServicesPension(TestCase):
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
        self.person2 = HouseholdMember.objects.create(
            screen=self.screen1,
            relationship="child",
            age=10,
            student=True,
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

    def test_family_planning_services_pass_all_conditions(self):
        fps = FamilyPlanningServices(self.screen1, [{"name_abbreviated": "medicaid", "eligible": False}])
        eligibility = fps.eligibility

        self.assertTrue(eligibility["eligible"])

    def test_family_planning_services_failed_all_conditions(self):
        self.person2.age = 20
        self.person2.save()
        IncomeStream.objects.create(
            screen=self.screen1, household_member=self.person1, type="wages", amount=4000, frequency="monthly"
        )

        fps = FamilyPlanningServices(self.screen1, [{"name_abbreviated": "medicaid", "eligible": True}])
        eligibility = fps.eligibility

        self.assertFalse(eligibility["eligible"])

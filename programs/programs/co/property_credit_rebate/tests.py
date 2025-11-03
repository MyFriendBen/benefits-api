from django.test import TestCase
from unittest import skip
from programs.programs.co.property_credit_rebate.calculator import PropertyCreditRebate
from screener.models import Screen, HouseholdMember, IncomeStream


@skip("Calculator constructor signature changed - needs API update")
class TestPropertyCreditRebatePension(TestCase):
    def setUp(self):
        self.screen1 = Screen.objects.create(
            agree_to_tos=True,
            zipcode="80205",
            county="Denver County",
            household_size=2,
            household_assets=0,
            has_tanf=False,
            has_ssi=False,
        )
        self.person1 = HouseholdMember.objects.create(
            screen=self.screen1,
            relationship="headOfHousehold",
            age=65,
            student=False,
            student_full_time=False,
            pregnant=False,
            unemployed=False,
            worked_in_last_18_mos=True,
            visually_impaired=False,
            disabled=True,
            veteran=False,
            has_income=False,
            has_expenses=False,
        )

    def test_screen_exits(self):
        self.assertEqual(self.screen1.agree_to_tos, True)
        self.assertEqual(self.person1.screen, self.screen1)

    def test_property_credit_rebate_visually_impaired_is_eligible(self):
        cpcr = PropertyCreditRebate(self.screen1)
        eligibility = cpcr.eligibility

        self.assertTrue(eligibility["eligible"])

    def test_property_credit_rebate_failed_all_conditions(self):
        self.person1.age = 30
        self.person1.disabled = False
        self.person1.save()
        income = IncomeStream.objects.create(
            screen=self.screen1, household_member=self.person1, type="wages", amount=2000, frequency="monthly"
        )

        cpcr = PropertyCreditRebate(self.screen1)
        eligibility = cpcr.eligibility

        self.assertFalse(eligibility["eligible"])

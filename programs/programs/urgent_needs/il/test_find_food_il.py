from unittest.mock import patch

from django.test import TestCase

from programs.models import UrgentNeed
from programs.programs.urgent_needs.il.find_food_il import FindFoodIl
from programs.util import Dependencies
from screener.models import HouseholdMember, Screen, WhiteLabel
from translations.models import Translation


def make_urgent_need(white_label):
    prefix = "test_urgent_need.il_find_food"
    return UrgentNeed.objects.create(
        white_label=white_label,
        external_name="il_find_food",
        name=Translation.objects.add_translation(f"{prefix}.name", "Find Food IL"),
        description=Translation.objects.add_translation(f"{prefix}.description", "Test"),
        link=Translation.objects.add_translation(f"{prefix}.link", "https://example.com"),
        website_description=Translation.objects.add_translation(f"{prefix}.website_description", "Test"),
        warning=Translation.objects.add_translation(f"{prefix}.warning", ""),
        notification_message=Translation.objects.add_translation(f"{prefix}.notification_message", ""),
    )


class TestFindFoodIl(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Illinois", code="il", state_code="IL")
        self.urgent_need = make_urgent_need(self.white_label)
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            agree_to_tos=True,
            zipcode="60601",
            county="Cook",
            household_size=2,
            household_assets=0,
            completed=False,
        )
        HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=30)

    def _calc(self, gross_income=0):
        with patch.object(self.screen.__class__, "calc_gross_income", return_value=gross_income):
            return FindFoodIl(self.screen, self.urgent_need, Dependencies(), {}).eligible()

    def test_eligible_with_young_member_and_low_income(self):
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=10)
        self.assertTrue(self._calc(gross_income=15_000))

    def test_not_eligible_no_members_under_22(self):
        self.assertFalse(self._calc(gross_income=15_000))

    def test_not_eligible_income_too_high(self):
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=10)
        self.assertFalse(self._calc(gross_income=25_000))

    def test_eligible_at_income_boundary(self):
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=10)
        self.assertTrue(self._calc(gross_income=22_000))

    def test_eligible_with_member_age_21(self):
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=21)
        self.assertTrue(self._calc(gross_income=15_000))

    def test_not_eligible_with_member_age_22(self):
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=22)
        self.assertFalse(self._calc(gross_income=15_000))

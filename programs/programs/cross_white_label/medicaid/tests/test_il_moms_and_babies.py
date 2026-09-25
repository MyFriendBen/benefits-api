from datetime import date
from unittest.mock import Mock, patch

from django.test import TestCase

from programs.programs.cross_white_label.medicaid.moms_and_babies.il import MomsAndBabies
from programs.util import Dependencies
from screener.models import HouseholdMember, Screen, WhiteLabel


class TestMomsAndBabiesNewborn(TestCase):
    """A newborn is a baby up to 2 months old, not every child under 1."""

    REFERENCE_DATE = date(2026, 9, 15)

    def setUp(self):
        white_label = WhiteLabel.objects.create(name="Illinois", code="il", state_code="IL")
        self.screen = Screen.objects.create(
            white_label=white_label, zipcode="60601", county="Cook County", household_size=2, completed=False
        )
        self.parent = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=28)
        self.calc = MomsAndBabies(self.screen, Mock(), {}, Dependencies())

        reference_date = patch.object(Screen, "get_reference_date", return_value=self.REFERENCE_DATE)
        reference_date.start()
        self.addCleanup(reference_date.stop)

    def _child(self, birth_year_month, age=0):
        return HouseholdMember.objects.create(
            screen=self.screen, relationship="child", age=age, birth_year_month=birth_year_month
        )

    def test_born_this_month_is_a_newborn(self):
        self.assertTrue(self.calc._is_eligible_newborn(self._child(date(2026, 9, 1))))

    def test_two_months_old_is_a_newborn(self):
        self.assertTrue(self.calc._is_eligible_newborn(self._child(date(2026, 7, 1))))

    def test_three_months_old_is_not_a_newborn(self):
        self.assertFalse(self.calc._is_eligible_newborn(self._child(date(2026, 6, 1))))

    def test_ten_months_old_is_not_a_newborn(self):
        self.assertFalse(self.calc._is_eligible_newborn(self._child(date(2025, 11, 1))))

    def test_without_a_birth_date_age_zero_is_a_newborn(self):
        child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=0)
        self.assertTrue(self.calc._is_eligible_newborn(child))

    def test_parent_of_a_newborn_is_an_eligible_adult(self):
        self._child(date(2026, 8, 1))
        self.assertTrue(self.calc._is_eligible_adult(self.parent))

    def test_parent_of_a_ten_month_old_is_not_an_eligible_adult(self):
        self._child(date(2025, 11, 1))
        self.assertFalse(self.calc._is_eligible_adult(self.parent))

    def test_newborn_gets_the_newborn_amount(self):
        self.assertEqual(self.calc.member_value(self._child(date(2026, 8, 1))), MomsAndBabies.newborn_member_amount)

    def test_ten_month_old_does_not_get_the_newborn_amount(self):
        self.assertEqual(self.calc.member_value(self._child(date(2025, 11, 1))), MomsAndBabies.adult_member_amount)

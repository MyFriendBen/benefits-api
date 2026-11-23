from django.test import TestCase

from programs.models import UrgentNeed
from programs.urgent_needs.il.il_dcfs_scholarship import IlDcfsScholarship
from programs.util import Dependencies
from screener.models import HouseholdMember, Screen, WhiteLabel
from translations.models import Translation


def make_urgent_need(white_label):
    prefix = "test_urgent_need.il_dcfs_scholarship"
    return UrgentNeed.objects.create(
        white_label=white_label,
        external_name="il_dcfs_scholarship",
        name=Translation.objects.add_translation(f"{prefix}.name", "DCFS Scholarship"),
        description=Translation.objects.add_translation(f"{prefix}.description", "Test"),
        link=Translation.objects.add_translation(f"{prefix}.link", "https://example.com"),
        website_description=Translation.objects.add_translation(f"{prefix}.website_description", "Test"),
        warning=Translation.objects.add_translation(f"{prefix}.warning", ""),
        notification_message=Translation.objects.add_translation(f"{prefix}.notification_message", ""),
    )


class TestIlDcfsScholarship(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Illinois", code="il", state_code="IL")
        self.urgent_need = make_urgent_need(self.white_label)
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            agree_to_tos=True,
            zipcode="60601",
            county="Cook",
            household_size=1,
            household_assets=0,
            completed=False,
        )

    def _member(self, **kwargs):
        defaults = {"relationship": "headOfHousehold", "age": 19, "student": True}
        return HouseholdMember.objects.create(screen=self.screen, **{**defaults, **kwargs})

    def _eligible(self, missing=None):
        calc = IlDcfsScholarship(self.screen, self.urgent_need, missing or Dependencies(), {})
        return calc.calc()

    def test_eligible_student_with_foster_care_tile(self):
        self._member(was_in_foster_care=True)
        self.assertTrue(self._eligible())

    def test_eligible_student_listed_as_foster_child(self):
        self._member(relationship="fosterChild", age=18)
        self.assertTrue(self._eligible())

    def test_not_eligible_without_foster_care(self):
        self._member(was_in_foster_care=False)
        self.assertFalse(self._eligible())

    def test_not_eligible_when_foster_care_unanswered(self):
        self._member(was_in_foster_care=None)
        self.assertFalse(self._eligible())

    def test_not_eligible_foster_care_but_not_a_student(self):
        self._member(was_in_foster_care=True, student=False)
        self.assertFalse(self._eligible())

    def test_not_eligible_foster_care_and_student_are_different_members(self):
        self._member(was_in_foster_care=True, student=False)
        self._member(relationship="child", age=17, student=True, was_in_foster_care=False)
        self.assertFalse(self._eligible())

    def test_no_age_limit(self):
        self._member(was_in_foster_care=True, age=45)
        self.assertTrue(self._eligible())

    def test_not_eligible_when_student_is_missing(self):
        self._member(was_in_foster_care=True)
        self.assertFalse(self._eligible(Dependencies(["student"])))

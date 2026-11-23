from datetime import date
from typing import Optional
from unittest.mock import Mock

from django.test import SimpleTestCase

from programs.programs.shared.tax_filers import is_younger, tax_filers


def member(relationship: str = "child", birth: Optional[date] = None, age: Optional[int] = None) -> Mock:
    m = Mock()
    m.relationship = relationship
    m.birth_year_month = birth
    m.calc_age.return_value = age
    return m


def screen_with(*members: Mock) -> Mock:
    screen = Mock()
    screen.household_members.all.return_value = list(members)
    return screen


class TestTaxFilers(SimpleTestCase):
    def setUp(self):
        self.head = member("headOfHousehold")
        self.spouse = member("spouse")
        self.partner = member("domesticPartner")
        self.child = member("child")
        self.screen = screen_with(self.child, self.spouse, self.head, self.partner)

    def test_single_return_is_the_head_alone(self):
        self.assertEqual(tax_filers(self.screen, joint=False), [self.head])

    def test_joint_return_adds_the_spouse_after_the_head(self):
        self.assertEqual(tax_filers(self.screen, joint=True), [self.head, self.spouse])

    def test_domestic_partner_is_never_a_filer(self):
        self.assertNotIn(self.partner, tax_filers(self.screen, joint=True))


class TestIsYounger(SimpleTestCase):
    def test_later_birth_month_is_younger(self):
        self.assertTrue(is_younger(member(birth=date(2010, 6, 1)), member(birth=date(1990, 1, 1))))

    def test_same_birth_month_is_not_younger(self):
        self.assertFalse(is_younger(member(birth=date(1990, 1, 1)), member(birth=date(1990, 1, 1))))

    def test_falls_back_to_age_when_a_birth_month_is_missing(self):
        self.assertTrue(is_younger(member(age=10), member(birth=date(1990, 1, 1), age=36)))
        self.assertFalse(is_younger(member(age=40), member(age=36)))

    def test_unknown_age_is_not_younger(self):
        self.assertFalse(is_younger(member(age=None), member(age=36)))

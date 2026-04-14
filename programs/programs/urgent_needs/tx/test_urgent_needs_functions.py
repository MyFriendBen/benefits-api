from unittest.mock import patch

from django.test import TestCase

from programs.models import UrgentNeed
from programs.programs.urgent_needs.tx.books_beginning_at_birth import BooksBeginningAtBirth
from programs.programs.urgent_needs.tx.double_up_food_bucks import DoubleUpFoodBucks
from programs.programs.urgent_needs.tx.hippy import Hippy
from programs.programs.urgent_needs.tx.oak_cliff_lena import OakCliffLena
from programs.programs.urgent_needs.tx.serve_southern_dallas import ServeSouthernDallas
from programs.programs.urgent_needs.tx.snap_employment import SnapEmploymentTraining
from programs.programs.urgent_needs.tx.wic import Wic
from programs.util import Dependencies
from screener.models import HouseholdMember, Screen, WhiteLabel
from translations.models import Translation


def make_urgent_need(white_label, external_name):
    prefix = f"test_urgent_need.{external_name}"
    return UrgentNeed.objects.create(
        white_label=white_label,
        external_name=external_name,
        name=Translation.objects.add_translation(f"{prefix}.name", "Test"),
        description=Translation.objects.add_translation(f"{prefix}.description", "Test"),
        link=Translation.objects.add_translation(f"{prefix}.link", "https://example.com"),
        website_description=Translation.objects.add_translation(f"{prefix}.website_description", "Test"),
        warning=Translation.objects.add_translation(f"{prefix}.warning", ""),
        notification_message=Translation.objects.add_translation(f"{prefix}.notification_message", ""),
    )


def make_tx_screen(white_label, **kwargs):
    return Screen.objects.create(
        white_label=white_label,
        agree_to_tos=True,
        zipcode="75001",
        county="Dallas",
        household_size=2,
        household_assets=0,
        completed=False,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# SnapEmploymentTraining
# ---------------------------------------------------------------------------


class TestSnapEmploymentTraining(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Texas", code="tx", state_code="TX")
        self.urgent_need = make_urgent_need(self.white_label, "tx_snap_employment")
        self.screen = make_tx_screen(self.white_label)
        HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=30)

    def _calc(self, data):
        return SnapEmploymentTraining(self.screen, self.urgent_need, Dependencies(), data).eligible()

    def test_eligible_when_snap_in_data(self):
        self.assertTrue(self._calc([{"name_abbreviated": "tx_snap", "eligible": True}]))

    def test_eligible_when_screen_has_snap(self):
        self.screen.has_snap = True
        self.screen.save()
        self.assertTrue(self._calc([]))

    def test_not_eligible_without_snap(self):
        self.assertFalse(self._calc([]))

    def test_not_eligible_when_snap_ineligible_in_data(self):
        self.assertFalse(self._calc([{"name_abbreviated": "tx_snap", "eligible": False}]))


# ---------------------------------------------------------------------------
# DoubleUpFoodBucks
# ---------------------------------------------------------------------------


class TestDoubleUpFoodBucks(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Texas", code="tx", state_code="TX")
        self.urgent_need = make_urgent_need(self.white_label, "tx_double_up_food_bucks")
        self.screen = make_tx_screen(self.white_label)
        HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=30)

    def _calc(self, data):
        return DoubleUpFoodBucks(self.screen, self.urgent_need, Dependencies(), data).eligible()

    def test_eligible_when_snap_in_data(self):
        self.assertTrue(self._calc([{"name_abbreviated": "tx_snap", "eligible": True}]))

    def test_eligible_when_screen_has_snap(self):
        self.screen.has_snap = True
        self.screen.save()
        self.assertTrue(self._calc([]))

    def test_not_eligible_without_snap(self):
        self.assertFalse(self._calc([]))

    def test_not_eligible_when_snap_ineligible_in_data(self):
        self.assertFalse(self._calc([{"name_abbreviated": "tx_snap", "eligible": False}]))


# ---------------------------------------------------------------------------
# ServeSouthernDallas
# ---------------------------------------------------------------------------


class TestServeSouthernDallas(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Texas", code="tx", state_code="TX")
        self.urgent_need = make_urgent_need(self.white_label, "tx_serve_southern_dallas")
        self.screen = make_tx_screen(self.white_label, needs_baby_supplies=True)
        HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=30)

    def _calc(self):
        return ServeSouthernDallas(self.screen, self.urgent_need, Dependencies(), {}).eligible()

    def test_eligible_with_young_child_and_baby_supplies(self):
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=2)
        self.assertTrue(self._calc())

    def test_not_eligible_child_too_old(self):
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=5)
        self.assertFalse(self._calc())

    def test_not_eligible_no_children(self):
        self.assertFalse(self._calc())

    def test_not_eligible_without_baby_supplies(self):
        self.screen.needs_baby_supplies = False
        self.screen.save()
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=2)
        self.assertFalse(self._calc())

    def test_eligible_at_age_boundary(self):
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=4)
        self.assertTrue(self._calc())


# ---------------------------------------------------------------------------
# Wic
# ---------------------------------------------------------------------------


class TestWic(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Texas", code="tx", state_code="TX")
        self.urgent_need = make_urgent_need(self.white_label, "tx_wic")
        self.screen = make_tx_screen(self.white_label)
        HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=30)

    def _calc(self):
        return Wic(self.screen, self.urgent_need, Dependencies(), {}).eligible()

    def test_eligible_with_young_child(self):
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=3)
        self.assertTrue(self._calc())

    def test_eligible_with_pregnant_member(self):
        HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=28, pregnant=True)
        self.assertTrue(self._calc())

    def test_not_eligible_child_too_old(self):
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=5)
        self.assertFalse(self._calc())

    def test_not_eligible_no_young_children_or_pregnant(self):
        self.assertFalse(self._calc())

    def test_eligible_at_age_boundary(self):
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=4)
        self.assertTrue(self._calc())


# ---------------------------------------------------------------------------
# OakCliffLena
# ---------------------------------------------------------------------------


class TestOakCliffLena(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Texas", code="tx", state_code="TX")
        self.urgent_need = make_urgent_need(self.white_label, "tx_oak_cliff_lena")
        self.screen = make_tx_screen(self.white_label)
        HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=30)

    def _calc(self):
        return OakCliffLena(self.screen, self.urgent_need, Dependencies(), {}).eligible()

    def test_eligible_with_young_child(self):
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=3)
        self.assertTrue(self._calc())

    def test_eligible_at_age_boundary(self):
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=4)
        self.assertTrue(self._calc())

    def test_not_eligible_child_too_old(self):
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=5)
        self.assertFalse(self._calc())

    def test_not_eligible_no_children(self):
        self.assertFalse(self._calc())


# ---------------------------------------------------------------------------
# BooksBeginningAtBirth
# ---------------------------------------------------------------------------


class TestBooksBeginningAtBirth(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Texas", code="tx", state_code="TX")
        self.urgent_need = make_urgent_need(self.white_label, "tx_books_beginning_at_birth")
        self.screen = make_tx_screen(self.white_label)
        HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=30)

    def _calc(self):
        return BooksBeginningAtBirth(self.screen, self.urgent_need, Dependencies(), {}).eligible()

    def test_eligible_with_young_child(self):
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=2)
        self.assertTrue(self._calc())

    def test_eligible_at_age_boundary(self):
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=4)
        self.assertTrue(self._calc())

    def test_not_eligible_child_too_old(self):
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=5)
        self.assertFalse(self._calc())

    def test_not_eligible_no_children(self):
        self.assertFalse(self._calc())


# ---------------------------------------------------------------------------
# Hippy
# ---------------------------------------------------------------------------


class TestHippy(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Texas", code="tx", state_code="TX")
        self.urgent_need = make_urgent_need(self.white_label, "tx_hippy")
        self.screen = make_tx_screen(self.white_label)
        HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=30)

    def _calc(self):
        return Hippy(self.screen, self.urgent_need, Dependencies(), {}).eligible()

    def test_eligible_with_child_in_range(self):
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=4)
        self.assertTrue(self._calc())

    def test_eligible_at_lower_boundary(self):
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=3)
        self.assertTrue(self._calc())

    def test_eligible_at_upper_boundary(self):
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=5)
        self.assertTrue(self._calc())

    def test_not_eligible_child_too_young(self):
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=2)
        self.assertFalse(self._calc())

    def test_not_eligible_child_too_old(self):
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=6)
        self.assertFalse(self._calc())

    def test_not_eligible_no_children(self):
        self.assertFalse(self._calc())

"""
Tests for shared UrgentNeedType rows (white_label = None).

A shared type is used by urgent needs in every white label, so the guarantees
worth pinning down are that it stays reachable from each white label and that
it never leaks one white label's urgent needs into another's response.
"""

from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory, TestCase
from rest_framework.test import APIClient, APITestCase

from authentication.models import User
from programs.admin import UrgentNeedTypeAdmin
from programs.models import UrgentNeed, UrgentNeedType, UrgentNeedTypeDataController
from programs.serializers import UrgentNeedTypeSerializer
from screener.models import WhiteLabel
from translations.models import Translation
from translations.views import has_translation_access


def make_type(external_name: str, white_label: str | None = None, name: str = "") -> UrgentNeedType:
    urgent_need_type = UrgentNeedType.objects.new_urgent_need_type(white_label, external_name, None)
    if name:
        Translation.objects.edit_translation_by_id(urgent_need_type.name.id, settings.LANGUAGE_CODE, name)
    return urgent_need_type


def make_need(
    external_name: str, white_label: WhiteLabel, category_type: UrgentNeedType, **overrides: bool
) -> UrgentNeed:
    need = UrgentNeed.objects.new_urgent_need(white_label=white_label.code, name=external_name, phone_number=None)
    need.category_type = category_type
    need.active = overrides.get("active", True)
    need.show_on_current_benefits = overrides.get("show_on_current_benefits", True)
    need.save()
    return need


class TestSharedUrgentNeedTypeModel(TestCase):
    def setUp(self) -> None:
        self.co = WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")
        self.mo = WhiteLabel.objects.create(name="Missouri", code="mo", state_code="MO")

    def test_new_urgent_need_type_creates_a_shared_row(self) -> None:
        urgent_need_type = UrgentNeedType.objects.new_urgent_need_type(None, "food_or_groceries", None)

        self.assertIsNone(urgent_need_type.white_label)

    def test_new_urgent_need_type_still_scopes_when_given_a_white_label(self) -> None:
        urgent_need_type = UrgentNeedType.objects.new_urgent_need_type("co", "co_only", None)

        self.assertEqual(urgent_need_type.white_label, self.co)

    def test_urgent_needs_in_different_white_labels_share_one_type(self) -> None:
        shared = make_type("food_or_groceries")

        co_need = make_need("co_food_bank", self.co, shared)
        mo_need = make_need("mo_food_bank", self.mo, shared)

        self.assertEqual(co_need.category_type_id, mo_need.category_type_id)
        self.assertEqual(shared.urgent_needs.count(), 2)


class TestSharedUrgentNeedTypeSerialization(TestCase):
    def setUp(self) -> None:
        self.co = WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")
        self.mo = WhiteLabel.objects.create(name="Missouri", code="mo", state_code="MO")
        self.shared = make_type("food_or_groceries")
        self.co_need = make_need("co_food_bank", self.co, self.shared)
        self.mo_need = make_need("mo_food_bank", self.mo, self.shared)

    def _need_ids(self, white_label_code: str) -> set[int]:
        data = UrgentNeedTypeSerializer(self.shared, context={"white_label": white_label_code}).data
        return {need["id"] for need in data["urgent_needs"]}

    def test_only_the_requested_white_labels_urgent_needs_are_returned(self) -> None:
        self.assertEqual(self._need_ids("co"), {self.co_need.id})
        self.assertEqual(self._need_ids("mo"), {self.mo_need.id})

    def test_hidden_urgent_needs_are_still_excluded(self) -> None:
        self.co_need.show_on_current_benefits = False
        self.co_need.save()

        self.assertEqual(self._need_ids("co"), set())


class TestSharedUrgentNeedTypeEndpoint(APITestCase):
    """GET /api/urgent_need_types/{white_label}/"""

    def setUp(self) -> None:
        self.co = WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")
        self.mo = WhiteLabel.objects.create(name="Missouri", code="mo", state_code="MO")
        self.shared = make_type("food_or_groceries", name="Food or groceries")
        self.co_need = make_need("co_food_bank", self.co, self.shared)
        self.mo_need = make_need("mo_food_bank", self.mo, self.shared)

        # Only MO has a need on this type, so CO must not see it at all.
        self.mo_only = make_type("veterans_resources", name="Veterans resources")
        make_need("mo_veterans", self.mo, self.mo_only)

        self.user = User.objects.create_user(email_or_cell="types@example.com", password="pw")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_shared_type_is_returned_for_each_white_label_that_uses_it(self) -> None:
        """It would be filtered out entirely if the view still scoped on the type's own white label."""
        co = self.client.get("/api/urgent_need_types/co/")
        mo = self.client.get("/api/urgent_need_types/mo/")

        self.assertEqual(co.status_code, 200)
        self.assertEqual({t["id"] for t in co.data}, {self.shared.id})
        self.assertEqual({t["id"] for t in mo.data}, {self.shared.id, self.mo_only.id})

    def test_a_white_label_sees_only_its_own_urgent_needs(self) -> None:
        response = self.client.get("/api/urgent_need_types/co/")

        need_ids = [need["id"] for urgent_need_type in response.data for need in urgent_need_type["urgent_needs"]]
        self.assertEqual(need_ids, [self.co_need.id])


class TestSharedUrgentNeedTypeDataController(TestCase):
    """The translation export/import round-trips a shared type without inventing a white label."""

    def setUp(self) -> None:
        self.co = WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")

    def test_shared_type_exports_a_null_white_label(self) -> None:
        shared = make_type("food_or_groceries")

        self.assertIsNone(UrgentNeedTypeDataController(shared).to_model_data()["white_label"])

    def test_importing_a_null_white_label_makes_the_type_shared(self) -> None:
        scoped = make_type("co_food", white_label="co")
        white_labels_before = WhiteLabel.objects.count()

        UrgentNeedTypeDataController(scoped).from_model_data({"white_label": None, "icon": None})

        scoped.refresh_from_db()
        self.assertIsNone(scoped.white_label)
        self.assertEqual(WhiteLabel.objects.count(), white_labels_before)


class TestSharedUrgentNeedTypeAdmin(TestCase):
    """A white label admin who isn't a superuser can see and edit shared types."""

    def setUp(self) -> None:
        self.co = WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")
        self.mo = WhiteLabel.objects.create(name="Missouri", code="mo", state_code="MO")
        self.shared = make_type("food_or_groceries")
        self.mo_scoped = make_type("mo_only", white_label="mo")

        self.user = User.objects.create_user(email_or_cell="co-admin@example.com", password="pw")
        self.user.is_staff = True
        self.user.save()
        self.user.white_labels.add(self.co)

        self.model_admin = UrgentNeedTypeAdmin(UrgentNeedType, AdminSite())
        self.request = RequestFactory().get("/admin/")
        self.request.user = self.user

    def test_shared_types_are_listed_but_other_white_labels_types_are_not(self) -> None:
        listed = set(self.model_admin.get_queryset(self.request))

        self.assertIn(self.shared, listed)
        self.assertNotIn(self.mo_scoped, listed)

    def test_shared_type_can_be_changed(self) -> None:
        self.assertTrue(self.model_admin.has_change_permission(self.request, self.shared))
        self.assertFalse(self.model_admin.has_change_permission(self.request, self.mo_scoped))

    def test_shared_type_cannot_be_deleted_by_a_white_label_admin(self) -> None:
        """Deleting a shared type would strip it from every white label."""
        co_scoped = make_type("co_only", white_label="co")

        self.assertFalse(self.model_admin.has_delete_permission(self.request, self.shared))
        self.assertTrue(self.model_admin.has_delete_permission(self.request, co_scoped))

    def test_shared_type_can_be_deleted_by_a_superuser(self) -> None:
        self.user.is_superuser = True
        self.user.save()

        self.assertTrue(self.model_admin.has_delete_permission(self.request, self.shared))

    def test_white_label_is_read_only_for_a_white_label_admin(self) -> None:
        """Otherwise one state's admin could re-scope a shared type to their own white label."""
        self.assertIn("white_label", self.model_admin.get_readonly_fields(self.request, self.shared))

    def test_white_label_is_editable_by_a_superuser(self) -> None:
        self.user.is_superuser = True
        self.user.save()

        self.assertNotIn("white_label", self.model_admin.get_readonly_fields(self.request, self.shared))

    def test_shared_types_name_translation_is_accessible(self) -> None:
        """The 'Translate: Name' link must not 500 on a type with no white label."""
        self.assertTrue(has_translation_access(self.shared.name, self.user))
        self.assertFalse(has_translation_access(self.mo_scoped.name, self.user))

    def test_shared_types_name_translation_needs_a_white_label(self) -> None:
        self.user.white_labels.clear()

        self.assertFalse(has_translation_access(self.shared.name, self.user))

"""
Tests for the single-benefit toggle endpoint:

    PATCH /api/screens/<uuid>/current-benefits/
    body: {"name_abbreviated": "snap", "has": true|false}

A lightweight add/remove of one CurrentBenefit row consumed by the results-page
"already have this" toggle. Resolution is white-label-scoped and the
operation is idempotent. See screener.views.ScreenCurrentBenefitsView.
"""

from django.contrib.auth.models import Permission
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from authentication.models import User
from programs.models import Program
from screener.models import CurrentBenefit, Screen, WhiteLabel
from screener.serializers import CurrentBenefitToggleSerializer
from screener.tests.helpers import seed_program

# Program.name_abbreviated column max_length — the `name_abbreviated` field cap must match it.
NAME_ABBREVIATED_MAX_LENGTH = Program._meta.get_field("name_abbreviated").max_length


class CurrentBenefitsToggleTests(APITestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", household_size=1, completed=False
        )
        seed_program(self.white_label, "snap", "tanf")

        self.url = f"/api/screens/{self.screen.uuid}/current-benefits/"

        # Same gate as the Screen PATCH path: DjangoModelPermissions maps PATCH to
        # screener.change_screen, so the test user needs that perm.
        self.user = User.objects.create_user(email_or_cell="toggle@example.com", password="password")
        self.user.user_permissions.add(Permission.objects.get(codename="change_screen"))

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _benefit_names(self):
        return set(
            CurrentBenefit.objects.filter(screen=self.screen).values_list("program__name_abbreviated", flat=True)
        )

    def test_add_new_benefit(self):
        """has=true creates the row and the response reflects the updated list."""
        response = self.client.patch(self.url, {"name_abbreviated": "snap", "has": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"current_benefits": ["snap"]})
        self.assertEqual(self._benefit_names(), {"snap"})

    def test_remove_existing_benefit(self):
        """has=false deletes the row and the response reflects the updated list."""
        self.client.patch(self.url, {"name_abbreviated": "snap", "has": True}, format="json")
        self.client.patch(self.url, {"name_abbreviated": "tanf", "has": True}, format="json")

        response = self.client.patch(self.url, {"name_abbreviated": "snap", "has": False}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"current_benefits": ["tanf"]})
        self.assertEqual(self._benefit_names(), {"tanf"})

    def test_repeat_add_is_idempotent(self):
        """Adding a benefit that already exists is a no-op — no error, no duplicate row."""
        self.client.patch(self.url, {"name_abbreviated": "snap", "has": True}, format="json")
        response = self.client.patch(self.url, {"name_abbreviated": "snap", "has": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"current_benefits": ["snap"]})
        self.assertEqual(CurrentBenefit.objects.filter(screen=self.screen).count(), 1)

    def test_repeat_remove_is_idempotent(self):
        """Removing a benefit that isn't present is a no-op — no error."""
        response = self.client.patch(self.url, {"name_abbreviated": "snap", "has": False}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"current_benefits": []})
        self.assertEqual(self._benefit_names(), set())

    def test_wrong_white_label_is_404(self):
        """A program offered only by another white label can't be toggled (404, no write)."""
        other_wl = WhiteLabel.objects.create(name="Other", code="other", state_code="OT")
        seed_program(other_wl, "other_only")

        response = self.client.patch(self.url, {"name_abbreviated": "other_only", "has": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self._benefit_names(), set())

    def test_unknown_program_is_404(self):
        """An unknown name_abbreviated is a 404, not a silent no-op."""
        response = self.client.patch(self.url, {"name_abbreviated": "not_a_real_program", "has": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self._benefit_names(), set())

    def test_unknown_screen_is_404(self):
        """An unknown screen uuid is a 404."""
        url = "/api/screens/00000000-0000-0000-0000-000000000000/current-benefits/"
        response = self.client.patch(url, {"name_abbreviated": "snap", "has": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_missing_name_abbreviated_is_400(self):
        """name_abbreviated is required."""
        response = self.client.patch(self.url, {"has": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name_abbreviated", response.data)

    def test_missing_has_is_400(self):
        """has is required."""
        response = self.client.patch(self.url, {"name_abbreviated": "snap"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("has", response.data)

    def test_unauthenticated_is_rejected(self):
        """Unauthenticated requests are rejected (401 or 403, per DRF auth-class config)."""
        response = APIClient().patch(self.url, {"name_abbreviated": "snap", "has": True}, format="json")

        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
        self.assertEqual(self._benefit_names(), set())

    def test_authenticated_without_change_perm_is_forbidden(self):
        """PATCH maps to screener.change_screen; a user lacking it is rejected."""
        no_perms_user = User.objects.create_user(email_or_cell="noperms@example.com", password="password")
        no_perms_client = APIClient()
        no_perms_client.force_authenticate(user=no_perms_user)

        response = no_perms_client.patch(self.url, {"name_abbreviated": "snap", "has": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self._benefit_names(), set())

    def test_name_abbreviated_cap_matches_db_column(self):
        """The `name_abbreviated` field cap equals the Program.name_abbreviated column, so a
        DB-valid name is never rejected for length before the WL-scoped lookup."""
        field = CurrentBenefitToggleSerializer().fields["name_abbreviated"]
        self.assertEqual(field.max_length, NAME_ABBREVIATED_MAX_LENGTH)

    def test_name_at_column_max_clears_validation(self):
        """A name as long as the column clears serializer validation and reaches the
        WL-scoped lookup — 404 here only because no such Program exists, proving the
        length didn't reject it (a 400 would mean the cap is too tight)."""
        name = "a" * NAME_ABBREVIATED_MAX_LENGTH
        response = self.client.patch(self.url, {"name_abbreviated": name, "has": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_name_over_column_max_is_400(self):
        """A name longer than the column is rejected by the serializer (400), never
        reaching the lookup."""
        name = "a" * (NAME_ABBREVIATED_MAX_LENGTH + 1)
        response = self.client.patch(self.url, {"name_abbreviated": name, "has": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name_abbreviated", response.data)

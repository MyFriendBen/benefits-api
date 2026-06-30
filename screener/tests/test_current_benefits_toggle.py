"""
Tests for the single-benefit toggle endpoint:

    PATCH /api/v2/screens/<uuid>/current-benefits/
    body: {"program": "snap", "has": true|false}

A lightweight add/remove of one CurrentBenefit row consumed by the results-page
"already have this" toggle (MFB-871). Resolution is white-label-scoped and the
operation is idempotent. See screener.views.ScreenCurrentBenefitsView.
"""

from django.contrib.auth.models import Permission
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from authentication.models import User
from screener.models import CurrentBenefit, Screen, WhiteLabel
from screener.tests.helpers import seed_program


class CurrentBenefitsToggleTests(APITestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", household_size=1, completed=False
        )
        seed_program(self.white_label, "snap", "tanf")

        self.url = f"/api/v2/screens/{self.screen.uuid}/current-benefits/"

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
        response = self.client.patch(self.url, {"program": "snap", "has": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"current_benefits": ["snap"]})
        self.assertEqual(self._benefit_names(), {"snap"})

    def test_remove_existing_benefit(self):
        """has=false deletes the row and the response reflects the updated list."""
        self.client.patch(self.url, {"program": "snap", "has": True}, format="json")
        self.client.patch(self.url, {"program": "tanf", "has": True}, format="json")

        response = self.client.patch(self.url, {"program": "snap", "has": False}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"current_benefits": ["tanf"]})
        self.assertEqual(self._benefit_names(), {"tanf"})

    def test_repeat_add_is_idempotent(self):
        """Adding a benefit that already exists is a no-op — no error, no duplicate row."""
        self.client.patch(self.url, {"program": "snap", "has": True}, format="json")
        response = self.client.patch(self.url, {"program": "snap", "has": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"current_benefits": ["snap"]})
        self.assertEqual(CurrentBenefit.objects.filter(screen=self.screen).count(), 1)

    def test_repeat_remove_is_idempotent(self):
        """Removing a benefit that isn't present is a no-op — no error."""
        response = self.client.patch(self.url, {"program": "snap", "has": False}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"current_benefits": []})
        self.assertEqual(self._benefit_names(), set())

    def test_wrong_white_label_is_404(self):
        """A program offered only by another white label can't be toggled (404, no write)."""
        other_wl = WhiteLabel.objects.create(name="Other", code="other", state_code="OT")
        seed_program(other_wl, "other_only")

        response = self.client.patch(self.url, {"program": "other_only", "has": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self._benefit_names(), set())

    def test_unknown_program_is_404(self):
        """An unknown name_abbreviated is a 404, not a silent no-op."""
        response = self.client.patch(self.url, {"program": "not_a_real_program", "has": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self._benefit_names(), set())

    def test_unknown_screen_is_404(self):
        """An unknown screen uuid is a 404."""
        url = "/api/v2/screens/00000000-0000-0000-0000-000000000000/current-benefits/"
        response = self.client.patch(url, {"program": "snap", "has": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_missing_program_is_400(self):
        """program is required."""
        response = self.client.patch(self.url, {"has": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("program", response.data)

    def test_missing_has_is_400(self):
        """has is required."""
        response = self.client.patch(self.url, {"program": "snap"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("has", response.data)

    def test_unauthenticated_is_rejected(self):
        """Unauthenticated requests are rejected (401 or 403, per DRF auth-class config)."""
        response = APIClient().patch(self.url, {"program": "snap", "has": True}, format="json")

        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
        self.assertEqual(self._benefit_names(), set())

    def test_authenticated_without_change_perm_is_forbidden(self):
        """PATCH maps to screener.change_screen; a user lacking it is rejected."""
        no_perms_user = User.objects.create_user(email_or_cell="noperms@example.com", password="password")
        no_perms_client = APIClient()
        no_perms_client.force_authenticate(user=no_perms_user)

        response = no_perms_client.patch(self.url, {"program": "snap", "has": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self._benefit_names(), set())

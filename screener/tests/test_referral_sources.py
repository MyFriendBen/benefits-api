"""
Tests for the ReferralSourcesView endpoint.
"""

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from authentication.models import User
from screener.models import WhiteLabel
from programs.models import Referrer


class TestReferralSourcesView(APITestCase):
    """Tests for GET /api/screener-options/{wl}/referral-options/"""

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.other_wl = WhiteLabel.objects.create(name="Other State", code="other", state_code="OS")

        # Referrers for test WL
        Referrer.objects.create(
            white_label=self.white_label, referrer_code="friend", name="Friend / Family", show_in_dropdown=True
        )
        Referrer.objects.create(
            white_label=self.white_label,
            referrer_code="searchEngine",
            name="Google or other search engine",
            show_in_dropdown=True,
        )
        Referrer.objects.create(
            white_label=self.white_label, referrer_code="other", name="Other", show_in_dropdown=True
        )
        Referrer.objects.create(
            white_label=self.white_label, referrer_code="hidden", name="Hidden Partner", show_in_dropdown=False
        )

        # Same referrer_code in another WL — should not appear in test WL results
        Referrer.objects.create(
            white_label=self.other_wl, referrer_code="friend", name="Friend (Other WL)", show_in_dropdown=True
        )

        self.url = "/api/screener-options/test/referral-options/"
        self.user = User.objects.create_user(email_or_cell="testuser@example.com", password="password")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_returns_show_in_dropdown_referrers(self):
        """Returns only referrers with show_in_dropdown=True for the WL."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("friend", response.data)
        self.assertIn("searchEngine", response.data)
        self.assertIn("other", response.data)

    def test_excludes_hidden_referrers(self):
        """Referrers with show_in_dropdown=False are excluded."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("hidden", response.data)

    def test_scoped_to_white_label(self):
        """Referrers from other WLs are not returned, even if they share a code."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # "friend" should be the test WL's name, not the other WL's
        self.assertEqual(response.data["friend"], "Friend / Family")
        # Total count should only include test WL's show_in_dropdown=True rows
        self.assertEqual(len(response.data), 3)

    def test_returns_correct_display_names(self):
        """Response maps referrer_code to display name."""
        response = self.client.get(self.url)

        self.assertEqual(response.data["searchEngine"], "Google or other search engine")
        self.assertEqual(response.data["other"], "Other")

    def test_blank_name_falls_back_to_referrer_code(self):
        """When name is blank, the referrer_code is used as the display value."""
        Referrer.objects.create(white_label=self.white_label, referrer_code="noname", name="", show_in_dropdown=True)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["noname"], "noname")

    def test_unknown_white_label_returns_empty(self):
        """Unknown WL code returns empty dict, not 404."""
        response = self.client.get("/api/screener-options/doesnotexist/referral-options/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {})

    def test_unauthenticated_returns_403(self):
        """Unauthenticated requests are rejected."""
        unauthenticated_client = APIClient()
        response = unauthenticated_client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

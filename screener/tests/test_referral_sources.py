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

        # Generic referrers for test WL
        Referrer.objects.create(
            white_label=self.white_label,
            referrer_code="friend",
            name="Friend / Family",
            show_in_dropdown=True,
            is_partner=False,
        )
        Referrer.objects.create(
            white_label=self.white_label,
            referrer_code="searchEngine",
            name="Google or other search engine",
            show_in_dropdown=True,
            is_partner=False,
        )
        Referrer.objects.create(
            white_label=self.white_label, referrer_code="other", name="Other", show_in_dropdown=True, is_partner=False
        )
        Referrer.objects.create(
            white_label=self.white_label,
            referrer_code="hidden",
            name="Hidden Partner",
            show_in_dropdown=False,
            is_partner=False,
        )

        # Partner referrer for test WL
        Referrer.objects.create(
            white_label=self.white_label,
            referrer_code="bia",
            name="Benefits in Action",
            show_in_dropdown=True,
            is_partner=True,
        )

        # Same referrer_code in another WL — should not appear in test WL results
        Referrer.objects.create(
            white_label=self.other_wl,
            referrer_code="friend",
            name="Friend (Other WL)",
            show_in_dropdown=True,
            is_partner=False,
        )

        self.url = "/api/screener-options/test/referral-options/"
        self.user = User.objects.create_user(email_or_cell="testuser@example.com", password="password")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_response_has_generic_and_partners_keys(self):
        """Response always has 'generic' and 'partners' top-level keys."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("generic", response.data)
        self.assertIn("partners", response.data)

    def test_returns_show_in_dropdown_referrers(self):
        """Returns only referrers with show_in_dropdown=True for the WL."""
        response = self.client.get(self.url)

        self.assertIn("friend", response.data["generic"])
        self.assertIn("searchEngine", response.data["generic"])
        self.assertIn("other", response.data["generic"])
        self.assertIn("bia", response.data["partners"])

    def test_excludes_hidden_referrers(self):
        """Referrers with show_in_dropdown=False are excluded."""
        response = self.client.get(self.url)

        self.assertNotIn("hidden", response.data["generic"])
        self.assertNotIn("hidden", response.data["partners"])

    def test_generic_and_partner_are_separated(self):
        """is_partner=True rows appear in partners, is_partner=False in generic."""
        response = self.client.get(self.url)

        self.assertNotIn("bia", response.data["generic"])
        self.assertNotIn("friend", response.data["partners"])

    def test_scoped_to_white_label(self):
        """Referrers from other WLs are not returned."""
        response = self.client.get(self.url)

        self.assertEqual(response.data["generic"]["friend"], "Friend / Family")
        self.assertEqual(len(response.data["generic"]), 3)
        self.assertEqual(len(response.data["partners"]), 1)

    def test_returns_correct_display_names(self):
        """Response maps referrer_code to display name."""
        response = self.client.get(self.url)

        self.assertEqual(response.data["generic"]["searchEngine"], "Google or other search engine")
        self.assertEqual(response.data["partners"]["bia"], "Benefits in Action")

    def test_generic_sorted_alphabetically(self):
        """Generic options are returned in alphabetical order by name."""
        response = self.client.get(self.url)

        names = list(response.data["generic"].values())
        self.assertEqual(names, sorted(names))

    def test_partners_sorted_alphabetically(self):
        """Partner options are returned in alphabetical order by name."""
        Referrer.objects.create(
            white_label=self.white_label,
            referrer_code="zzz",
            name="Zzz Partner",
            show_in_dropdown=True,
            is_partner=True,
        )
        Referrer.objects.create(
            white_label=self.white_label,
            referrer_code="aaa",
            name="Aaa Partner",
            show_in_dropdown=True,
            is_partner=True,
        )

        response = self.client.get(self.url)

        names = list(response.data["partners"].values())
        self.assertEqual(names, sorted(names))

    def test_blank_name_is_rejected(self):
        """Referrer name must be non-blank — the DB constraint rejects empty strings."""
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            Referrer.objects.create(
                white_label=self.white_label, referrer_code="noname", name="", show_in_dropdown=True
            )

    def test_unknown_white_label_returns_empty(self):
        """Unknown WL code returns empty groups, not 404."""
        response = self.client.get("/api/screener-options/doesnotexist/referral-options/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"generic": {}, "partners": {}})

    def test_unauthenticated_returns_403(self):
        """Unauthenticated requests are rejected."""
        unauthenticated_client = APIClient()
        response = unauthenticated_client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

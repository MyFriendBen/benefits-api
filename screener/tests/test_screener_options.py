"""
Tests for the ScreenerOptionsView endpoint.
"""

from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from authentication.models import User
from screener.models import WhiteLabel
from programs.models import Program, ProgramCategory, Referrer
from translations.models import Translation


def make_translation(label: str, default_message: str) -> Translation:
    return Translation.objects.add_translation(label, default_message=default_message)


class TestScreenerOptionsView(APITestCase):
    """Tests for GET /api/screener-options/{wl}/"""

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.other_wl = WhiteLabel.objects.create(name="Other State", code="other", state_code="OS")

        # Referrers
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
            white_label=self.white_label,
            referrer_code="other",
            name="Other",
            show_in_dropdown=True,
            is_partner=False,
        )
        Referrer.objects.create(
            white_label=self.white_label,
            referrer_code="hidden",
            name="Hidden Partner",
            show_in_dropdown=False,
            is_partner=False,
        )
        Referrer.objects.create(
            white_label=self.white_label,
            referrer_code="bia",
            name="Benefits in Action",
            show_in_dropdown=True,
            is_partner=True,
        )
        # Same code in other WL — should not appear
        Referrer.objects.create(
            white_label=self.other_wl,
            referrer_code="friend",
            name="Friend (Other WL)",
            show_in_dropdown=True,
            is_partner=False,
        )

        # Programs
        self.category = ProgramCategory.objects.create(
            white_label=self.white_label,
            external_name="test_cash",
            name=make_translation("category.test_cash-name", "Cash Assistance"),
            description=make_translation("category.test_cash-description", ""),
        )
        self.snap = Program.objects.create(
            white_label=self.white_label,
            name_abbreviated="SNAP",
            active=True,
            show_in_has_benefits_step=True,
            has_calculator=False,
            category=self.category,
            name=make_translation("program.snap-name", "Supplemental Nutrition Assistance Program"),
            website_description=make_translation("program.snap-website_description", "Monthly food assistance"),
            learn_more_link=make_translation("program.snap-learn_more_link", ""),
        )
        # Inactive — should not appear
        Program.objects.create(
            white_label=self.white_label,
            name_abbreviated="OLD",
            active=False,
            show_in_has_benefits_step=True,
            has_calculator=False,
            category=self.category,
            name=make_translation("program.old-name", "Old Program"),
            website_description=make_translation("program.old-website_description", ""),
            learn_more_link=make_translation("program.old-learn_more_link", ""),
        )
        # show_in_has_benefits_step=False — should not appear
        Program.objects.create(
            white_label=self.white_label,
            name_abbreviated="EXCL",
            active=True,
            show_in_has_benefits_step=False,
            has_calculator=True,
            category=self.category,
            name=make_translation("program.excl-name", "Excluded Program"),
            website_description=make_translation("program.excl-website_description", ""),
            learn_more_link=make_translation("program.excl-learn_more_link", ""),
        )
        # Other WL — should not appear
        Program.objects.create(
            white_label=self.other_wl,
            name_abbreviated="OTHER",
            active=True,
            show_in_has_benefits_step=True,
            has_calculator=False,
            name=make_translation("program.other-name", "Other WL Program"),
            website_description=make_translation("program.other-website_description", ""),
            learn_more_link=make_translation("program.other-learn_more_link", ""),
        )

        self.url = "/api/screener-options/test/"
        self.user = User.objects.create_user(email_or_cell="testuser@example.com", password="password")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    # --- Top-level shape ---

    def test_response_has_expected_top_level_keys(self):
        """Response always has referral_options and has_benefits_programs keys."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("referral_options", response.data)
        self.assertIn("has_benefits_programs", response.data)

    def test_referral_options_has_generic_and_partners(self):
        """referral_options always has generic and partners sub-keys."""
        response = self.client.get(self.url)

        self.assertIn("generic", response.data["referral_options"])
        self.assertIn("partners", response.data["referral_options"])

    # --- Referral options ---

    def test_returns_show_in_dropdown_referrers(self):
        """Returns only referrers with show_in_dropdown=True for the WL."""
        response = self.client.get(self.url)
        generic = response.data["referral_options"]["generic"]
        partners = response.data["referral_options"]["partners"]

        self.assertIn("friend", generic)
        self.assertIn("searchEngine", generic)
        self.assertIn("other", generic)
        self.assertIn("bia", partners)

    def test_excludes_hidden_referrers(self):
        """Referrers with show_in_dropdown=False are excluded."""
        response = self.client.get(self.url)
        generic = response.data["referral_options"]["generic"]
        partners = response.data["referral_options"]["partners"]

        self.assertNotIn("hidden", generic)
        self.assertNotIn("hidden", partners)

    def test_referrers_scoped_to_white_label(self):
        """Referrers from other WLs are not returned."""
        response = self.client.get(self.url)
        generic = response.data["referral_options"]["generic"]

        self.assertEqual(generic["friend"], "Friend / Family")
        self.assertEqual(len(generic), 3)
        self.assertEqual(len(response.data["referral_options"]["partners"]), 1)

    def test_referrers_sorted_alphabetically(self):
        """Generic and partner referrers are sorted alphabetically by name."""
        response = self.client.get(self.url)

        generic_names = list(response.data["referral_options"]["generic"].values())
        partner_names = list(response.data["referral_options"]["partners"].values())
        self.assertEqual(generic_names, sorted(generic_names))
        self.assertEqual(partner_names, sorted(partner_names))

    def test_blank_referrer_name_rejected(self):
        """Referrer name must be non-blank — the DB constraint rejects empty strings."""
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            Referrer.objects.create(
                white_label=self.white_label, referrer_code="noname", name="", show_in_dropdown=True
            )

    # --- Has-benefits programs ---

    def test_returns_active_show_in_has_benefits_step_programs(self):
        """Returns only active programs with show_in_has_benefits_step=True for the WL."""
        response = self.client.get(self.url)
        abbreviations = [p["name_abbreviated"] for p in response.data["has_benefits_programs"]]

        self.assertIn("SNAP", abbreviations)

    def test_excludes_inactive_programs(self):
        """Inactive programs are excluded even if show_in_has_benefits_step=True."""
        response = self.client.get(self.url)
        abbreviations = [p["name_abbreviated"] for p in response.data["has_benefits_programs"]]

        self.assertNotIn("OLD", abbreviations)

    def test_excludes_programs_not_in_step(self):
        """Programs with show_in_has_benefits_step=False are excluded."""
        response = self.client.get(self.url)
        abbreviations = [p["name_abbreviated"] for p in response.data["has_benefits_programs"]]

        self.assertNotIn("EXCL", abbreviations)

    def test_programs_scoped_to_white_label(self):
        """Programs from other WLs are not returned."""
        response = self.client.get(self.url)
        abbreviations = [p["name_abbreviated"] for p in response.data["has_benefits_programs"]]

        self.assertNotIn("OTHER", abbreviations)

    def test_program_response_shape(self):
        """Each program has name_abbreviated, name, website_description, and category."""
        response = self.client.get(self.url)

        self.assertEqual(len(response.data["has_benefits_programs"]), 1)
        program = response.data["has_benefits_programs"][0]
        self.assertEqual(program["name_abbreviated"], "SNAP")
        self.assertEqual(program["name"]["default_message"], "Supplemental Nutrition Assistance Program")
        self.assertEqual(program["website_description"]["default_message"], "Monthly food assistance")
        self.assertEqual(program["category"]["default_message"], "Cash Assistance")

    # --- Auth / unknown WL ---

    def test_unknown_white_label_returns_empty(self):
        """Unknown WL code returns empty data, not 404."""
        response = self.client.get("/api/screener-options/doesnotexist/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["referral_options"], {"generic": {}, "partners": {}})
        self.assertEqual(response.data["has_benefits_programs"], [])

    def test_unauthenticated_returns_403(self):
        """Unauthenticated requests are rejected."""
        unauthenticated_client = APIClient()
        response = unauthenticated_client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

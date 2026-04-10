"""
Tests for the HasBenefitsProgramsView endpoint.
"""

from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from authentication.models import User
from screener.models import WhiteLabel
from programs.models import Program, ProgramCategory
from translations.models import Translation


def make_translation(label: str, default_message: str) -> Translation:
    return Translation.objects.add_translation(label, default_message=default_message)


class TestHasBenefitsProgramsView(APITestCase):
    """Tests for GET /api/screener-options/{wl}/has-benefits-programs/"""

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.other_wl = WhiteLabel.objects.create(name="Other State", code="other", state_code="OS")

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
        self.inactive = Program.objects.create(
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
        self.excluded = Program.objects.create(
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

        # Other WL program — should not appear
        self.other_wl_program = Program.objects.create(
            white_label=self.other_wl,
            name_abbreviated="OTHER",
            active=True,
            show_in_has_benefits_step=True,
            has_calculator=False,
            name=make_translation("program.other-name", "Other WL Program"),
            website_description=make_translation("program.other-website_description", ""),
            learn_more_link=make_translation("program.other-learn_more_link", ""),
        )

        self.url = "/api/screener-options/test/has-benefits-programs/"
        self.user = User.objects.create_user(email_or_cell="testuser@example.com", password="password")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_returns_active_show_in_has_benefits_step_programs(self):
        """Returns only active programs with show_in_has_benefits_step=True for the WL."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        abbreviations = [p["name_abbreviated"] for p in response.data]
        self.assertIn("SNAP", abbreviations)

    def test_excludes_inactive_programs(self):
        """Inactive programs are excluded even if show_in_has_benefits_step=True."""
        response = self.client.get(self.url)

        abbreviations = [p["name_abbreviated"] for p in response.data]
        self.assertNotIn("OLD", abbreviations)

    def test_excludes_programs_not_in_step(self):
        """Programs with show_in_has_benefits_step=False are excluded."""
        response = self.client.get(self.url)

        abbreviations = [p["name_abbreviated"] for p in response.data]
        self.assertNotIn("EXCL", abbreviations)

    def test_scoped_to_white_label(self):
        """Programs from other WLs are not returned."""
        response = self.client.get(self.url)

        abbreviations = [p["name_abbreviated"] for p in response.data]
        self.assertNotIn("OTHER", abbreviations)

    def test_response_shape(self):
        """Each program has name_abbreviated, name, website_description, and category."""
        response = self.client.get(self.url)

        self.assertEqual(len(response.data), 1)
        program = response.data[0]
        self.assertIn("name_abbreviated", program)
        self.assertIn("name", program)
        self.assertIn("website_description", program)
        self.assertIn("category", program)
        self.assertEqual(program["name_abbreviated"], "SNAP")
        self.assertEqual(program["name"]["default_message"], "Supplemental Nutrition Assistance Program")
        self.assertEqual(program["website_description"]["default_message"], "Monthly food assistance")
        self.assertEqual(program["category"]["default_message"], "Cash Assistance")

    def test_unknown_white_label_returns_empty(self):
        """Unknown WL code returns an empty list, not 404."""
        response = self.client.get("/api/screener-options/doesnotexist/has-benefits-programs/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_unauthenticated_returns_403(self):
        """Unauthenticated requests are rejected."""
        unauthenticated_client = APIClient()
        response = unauthenticated_client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

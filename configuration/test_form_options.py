"""
Tests for the get_form_options endpoint and related models.
"""

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from authentication.models import User
from screener.models import WhiteLabel
from programs.models import Icon, FormOption
from translations.models import Translation


class TestIconModel(TestCase):
    def test_str(self):
        icon = Icon.objects.create(name="House", lucide_name="house")
        self.assertEqual(str(icon), "House (house)")

    def test_ordering_by_name(self):
        Icon.objects.create(name="Zebra", lucide_name="zap")
        Icon.objects.create(name="Apple", lucide_name="apple")
        names = list(Icon.objects.values_list("name", flat=True))
        self.assertEqual(names, sorted(names))

    def test_lucide_name_not_required_to_be_unique(self):
        Icon.objects.create(name="House", lucide_name="house")
        # Same lucide_name is allowed — two icons can share the same Lucide icon
        icon2 = Icon.objects.create(name="Home", lucide_name="house")
        self.assertEqual(icon2.lucide_name, "house")


class TestFormOptionModel(TestCase):
    def setUp(self):
        self.wl = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.icon = Icon.objects.create(name="House", lucide_name="house")
        self.translation = Translation.objects.add_translation("test.housing", "Help with housing")

    def test_str(self):
        opt = FormOption.objects.create(
            white_label=self.wl,
            option_type="condition",
            value="housing",
            icon=self.icon,
            text=self.translation,
            order=1,
        )
        self.assertEqual(str(opt), "test - condition: housing")

    def test_null_icon_allowed(self):
        opt = FormOption.objects.create(
            white_label=self.wl,
            option_type="condition",
            value="housing",
            icon=None,
            text=self.translation,
        )
        self.assertIsNone(opt.icon)

    def test_unique_together_enforced(self):
        from django.db import IntegrityError

        FormOption.objects.create(
            white_label=self.wl,
            option_type="condition",
            value="housing",
            text=self.translation,
        )
        with self.assertRaises(IntegrityError):
            FormOption.objects.create(
                white_label=self.wl,
                option_type="condition",
                value="housing",
                text=self.translation,
            )

    def test_active_defaults_to_true(self):
        opt = FormOption.objects.create(
            white_label=self.wl,
            option_type="condition",
            value="housing",
            text=self.translation,
        )
        self.assertTrue(opt.active)


class TestGetFormOptionsEndpoint(APITestCase):
    """Tests for GET /api/<white_label_code>/form-options/"""

    def setUp(self):
        self.wl = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.other_wl = WhiteLabel.objects.create(name="Other State", code="other", state_code="OS")
        self.icon = Icon.objects.create(name="House", lucide_name="house")
        self.translation = Translation.objects.add_translation("test.housing", "Help with housing")
        self.url = "/api/test/form-options/"
        self.user = User.objects.create_user(email_or_cell="testuser@example.com", password="password")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_returns_200_for_known_white_label(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_returns_404_for_unknown_white_label(self):
        response = self.client.get("/api/doesnotexist/form-options/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_response_shape(self):
        response = self.client.get(self.url)
        self.assertIn("condition_options", response.data)
        self.assertIn("health_insurance_options", response.data)

    def test_empty_lists_when_no_form_options(self):
        response = self.client.get(self.url)
        self.assertEqual(response.data["condition_options"], [])
        self.assertEqual(response.data["health_insurance_options"], [])

    def test_returns_active_options_only(self):
        FormOption.objects.create(
            white_label=self.wl,
            option_type="condition",
            value="housing",
            icon=self.icon,
            text=self.translation,
            order=1,
            active=True,
        )
        inactive_translation = Translation.objects.add_translation("test.food", "Food")
        FormOption.objects.create(
            white_label=self.wl,
            option_type="condition",
            value="food",
            text=inactive_translation,
            order=2,
            active=False,
        )
        response = self.client.get(self.url)
        values = [opt["value"] for opt in response.data["condition_options"]]
        self.assertIn("housing", values)
        self.assertNotIn("food", values)

    def test_serializes_icon_lucide_name(self):
        FormOption.objects.create(
            white_label=self.wl,
            option_type="condition",
            value="housing",
            icon=self.icon,
            text=self.translation,
        )
        response = self.client.get(self.url)
        opt = response.data["condition_options"][0]
        self.assertEqual(opt["icon"], "house")

    def test_null_icon_serialized_as_none(self):
        FormOption.objects.create(
            white_label=self.wl,
            option_type="condition",
            value="housing",
            icon=None,
            text=self.translation,
        )
        response = self.client.get(self.url)
        opt = response.data["condition_options"][0]
        self.assertIsNone(opt["icon"])

    def test_serializes_translation_fields(self):
        FormOption.objects.create(
            white_label=self.wl,
            option_type="condition",
            value="housing",
            text=self.translation,
        )
        response = self.client.get(self.url)
        opt = response.data["condition_options"][0]
        self.assertIn("label", opt["text"])
        self.assertIn("default_message", opt["text"])
        self.assertEqual(opt["text"]["label"], "test.housing")
        self.assertEqual(opt["text"]["default_message"], "Help with housing")

    def test_options_returned_in_order(self):
        t2 = Translation.objects.add_translation("test.food", "Food")
        t3 = Translation.objects.add_translation("test.baby", "Baby supplies")
        FormOption.objects.create(
            white_label=self.wl, option_type="condition", value="housing", text=self.translation, order=2
        )
        FormOption.objects.create(white_label=self.wl, option_type="condition", value="food", text=t2, order=1)
        FormOption.objects.create(white_label=self.wl, option_type="condition", value="baby", text=t3, order=3)
        response = self.client.get(self.url)
        values = [opt["value"] for opt in response.data["condition_options"]]
        self.assertEqual(values, ["food", "housing", "baby"])

    def test_scoped_to_white_label(self):
        other_translation = Translation.objects.add_translation("other.housing", "Housing (Other)")
        FormOption.objects.create(
            white_label=self.other_wl,
            option_type="condition",
            value="housing",
            text=other_translation,
        )
        response = self.client.get(self.url)
        self.assertEqual(response.data["condition_options"], [])

    def test_health_insurance_options_returned_separately(self):
        hi_translation = Translation.objects.add_translation("test.medicaid", "Medicaid")
        FormOption.objects.create(
            white_label=self.wl,
            option_type="health_insurance",
            value="medicaid",
            text=hi_translation,
        )
        response = self.client.get(self.url)
        self.assertEqual(len(response.data["health_insurance_options"]), 1)
        self.assertEqual(response.data["health_insurance_options"][0]["value"], "medicaid")
        self.assertEqual(len(response.data["condition_options"]), 0)

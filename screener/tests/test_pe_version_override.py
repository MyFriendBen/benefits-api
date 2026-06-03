"""
Locks the invariant that a ?pe_version= override promotes a screen to is_test=True
*before* eligibility is calculated (and therefore before the EligibilitySnapshot is
written). The flip lives as two ordered statements in EligibilityTranslationView.get;
this test fails if a future refactor reorders them so the snapshot would be born under
is_test=False. See MFB-1112.

The view is exercised directly via APIRequestFactory (bypassing the IsAuthenticated
permission layer) so the test stays focused on the get() ordering logic and does not
depend on the full eligibility/serialization machinery (all_results is patched).
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework.permissions import AllowAny
from rest_framework.test import APIRequestFactory

from screener.models import Screen, WhiteLabel
from screener.views import EligibilityTranslationView, is_valid_pe_version_override


class TestIsValidPeVersionOverride(TestCase):
    def test_accepts_aliases(self):
        self.assertTrue(is_valid_pe_version_override("current"))
        self.assertTrue(is_valid_pe_version_override("frontier"))

    def test_accepts_version_number(self):
        self.assertTrue(is_valid_pe_version_override("1.715.2"))
        self.assertTrue(is_valid_pe_version_override("1.800.0"))

    def test_rejects_garbage_and_typos(self):
        for value in ("banana", "fronteir", "1.7", "1.715", "v1.715.2", "1.715.2 "):
            self.assertFalse(is_valid_pe_version_override(value), value)


class TestPeVersionOverrideFlipsIsTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            completed=False,
            agree_to_tos=True,
            is_test=False,
        )

    def _call_view(self, query):
        """Invoke EligibilityTranslationView.get directly, capturing screen.is_test at
        the moment all_results (the calc entry point) is invoked."""
        captured = {}

        def fake_all_results(screen, *args, **kwargs):
            captured["is_test"] = screen.is_test
            captured["pe_version"] = kwargs.get("pe_version")
            return {"programs": [], "urgent_needs": [], "screen_id": screen.id}

        # as_view() wraps the request in a DRF Request (giving .query_params); override
        # permissions so the test targets the get() logic, not the auth layer.
        view = EligibilityTranslationView.as_view(permission_classes=[AllowAny])
        request = self.factory.get("/api/eligibility/", query)
        with patch("screener.views.all_results", side_effect=fake_all_results), patch(
            "screener.views.get_web_hook", return_value=None
        ):
            response = view(request, id=str(self.screen.uuid))
        return captured, response

    def test_override_flips_is_test_before_calc(self):
        captured, _ = self._call_view({"pe_version": "frontier"})

        # The screen was is_test=False; the override must flip it BEFORE the calc runs.
        self.assertTrue(captured["is_test"])
        self.assertEqual(captured["pe_version"], "frontier")

        # And the flip is persisted.
        self.screen.refresh_from_db()
        self.assertTrue(self.screen.is_test)

    def test_no_override_leaves_is_test_untouched(self):
        captured, _ = self._call_view({})

        self.assertFalse(captured["is_test"])
        self.assertIsNone(captured["pe_version"])
        self.screen.refresh_from_db()
        self.assertFalse(self.screen.is_test)

    def test_invalid_override_returns_400_and_does_not_flip_or_calc(self):
        captured, response = self._call_view({"pe_version": "fronteir"})

        # Rejected before any work: 400, no calc, and is_test untouched.
        self.assertEqual(response.status_code, 400)
        self.assertIn("pe_version", response.data)
        self.assertEqual(captured, {})  # all_results never called
        self.screen.refresh_from_db()
        self.assertFalse(self.screen.is_test)

    def test_webhook_not_sent_for_test_screen(self):
        """A test screen (incl. one promoted by ?pe_version=) must never POST to a
        partner webhook."""
        hook = MagicMock()

        def fake_all_results(screen, *args, **kwargs):
            return {"programs": [], "urgent_needs": [], "screen_id": screen.id}

        view = EligibilityTranslationView.as_view(permission_classes=[AllowAny])
        request = self.factory.get("/api/eligibility/", {"pe_version": "frontier"})
        with patch("screener.views.all_results", side_effect=fake_all_results), patch(
            "screener.views.get_web_hook", return_value=hook
        ):
            view(request, id=str(self.screen.uuid))

        hook.send.assert_not_called()

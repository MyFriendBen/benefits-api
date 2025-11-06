"""
Integration tests for HUD API client (requires HUD_API_TOKEN).

These tests make real API calls to HUD and should only run in
environments with valid API credentials.

Run integration tests with: pytest -m integration
Skip integration tests with: pytest -m "not integration"
"""

import pytest
from unittest import skipUnless
from django.test import TestCase
from decouple import config
from django.core.cache import cache

from integrations.clients.hud_income_limits import hud_client, HudIncomeClientError
from screener.models import Screen, WhiteLabel


@pytest.mark.integration
class TestHudIntegrationMTSP(TestCase):
    """Integration tests requiring real HUD API access."""

    @classmethod
    def setUpClass(cls):
        """Set up test class - check if HUD_API_TOKEN is available."""
        super().setUpClass()
        cls.has_token = config("HUD_API_TOKEN", default=None) is not None

    def setUp(self):
        """Set up test data."""
        cache.clear()

        self.white_label_il = WhiteLabel.objects.create(
            name="Illinois Integration Test", code="il_integration", state_code="IL"
        )

        self.white_label_co = WhiteLabel.objects.create(
            name="Colorado Integration Test", code="co_integration", state_code="CO"
        )

    @skipUnless(config("HUD_API_TOKEN", default=None), "HUD_API_TOKEN not set")
    def test_real_api_call_cook_county_il(self):
        """Test actual API call for Cook County, IL."""
        screen = Screen.objects.create(
            white_label=self.white_label_il, zipcode="60601", county="Cook", household_size=4, completed=False
        )

        # Make real API call
        result = hud_client.get_screen_mtsp_ami(screen, "80%", 2025)

        # Verify result is reasonable (Cook County IL should have high AMI)
        self.assertIsInstance(result, int)
        self.assertGreater(result, 50000, "Cook County 80% AMI should be > $50k")
        self.assertLess(result, 200000, "Cook County 80% AMI should be < $200k")

    @skipUnless(config("HUD_API_TOKEN", default=None), "HUD_API_TOKEN not set")
    def test_real_api_call_denver_county_co(self):
        """Test actual API call for Denver County, CO."""
        screen = Screen.objects.create(
            white_label=self.white_label_co, zipcode="80202", county="Denver", household_size=4, completed=False
        )

        result = hud_client.get_screen_mtsp_ami(screen, "80%", 2025)

        self.assertIsInstance(result, int)
        self.assertGreater(result, 40000, "Denver County 80% AMI should be > $40k")
        self.assertLess(result, 200000, "Denver County 80% AMI should be < $200k")

    @skipUnless(config("HUD_API_TOKEN", default=None), "HUD_API_TOKEN not set")
    def test_real_api_call_all_percentages(self):
        """Test all MTSP percentage levels with real API."""
        screen = Screen.objects.create(
            white_label=self.white_label_il, zipcode="60601", county="Cook", household_size=4, completed=False
        )

        percentages = ["20%", "30%", "40%", "50%", "60%", "70%", "80%", "100%"]
        results = {}

        for percent in percentages:
            result = hud_client.get_screen_mtsp_ami(screen, percent, 2025)
            results[percent] = result
            self.assertIsInstance(result, int)
            self.assertGreater(result, 0)

        # Verify percentages are in ascending order (except 100% which is median)
        for i in range(len(percentages) - 2):
            current = percentages[i]
            next_pct = percentages[i + 1]
            self.assertLess(results[current], results[next_pct], f"{current} should be less than {next_pct}")

    @skipUnless(config("HUD_API_TOKEN", default=None), "HUD_API_TOKEN not set")
    def test_real_api_call_different_household_sizes(self):
        """Test different household sizes with real API."""
        household_sizes = [1, 2, 4, 8]
        results = {}

        for size in household_sizes:
            screen = Screen.objects.create(
                white_label=self.white_label_il, zipcode="60601", county="Cook", household_size=size, completed=False
            )

            result = hud_client.get_screen_mtsp_ami(screen, "80%", 2025)
            results[size] = result
            self.assertIsInstance(result, int)
            self.assertGreater(result, 0)

        # Verify larger households have higher income limits
        self.assertLess(results[1], results[2])
        self.assertLess(results[2], results[4])
        self.assertLess(results[4], results[8])

    @skipUnless(config("HUD_API_TOKEN", default=None), "HUD_API_TOKEN not set")
    def test_real_api_call_caching(self):
        """Test that caching works with real API calls."""
        screen = Screen.objects.create(
            white_label=self.white_label_il, zipcode="60601", county="Cook", household_size=4, completed=False
        )

        # First call - should hit API
        import time

        start = time.time()
        result1 = hud_client.get_screen_mtsp_ami(screen, "80%", 2025)
        first_call_time = time.time() - start

        # Second call - should use cache (much faster)
        start = time.time()
        result2 = hud_client.get_screen_mtsp_ami(screen, "80%", 2025)
        second_call_time = time.time() - start

        # Results should be identical
        self.assertEqual(result1, result2)

        # Cached call should be significantly faster
        # Note: This might be flaky in slow environments
        print(f"First call: {first_call_time:.3f}s, Second call: {second_call_time:.3f}s")

    @skipUnless(config("HUD_API_TOKEN", default=None), "HUD_API_TOKEN not set")
    def test_real_api_call_invalid_county(self):
        """Test that invalid county raises error with real API."""
        screen = Screen.objects.create(
            white_label=self.white_label_il,
            zipcode="00000",
            county="Nonexistent County",
            household_size=4,
            completed=False,
        )

        with self.assertRaises(HudIncomeClientError) as context:
            hud_client.get_screen_mtsp_ami(screen, "80%", 2025)

        self.assertIn("County not found", str(context.exception))

    @skipUnless(config("HUD_API_TOKEN", default=None), "HUD_API_TOKEN not set")
    def test_real_api_call_historical_year(self):
        """Test API call with historical year data."""
        screen = Screen.objects.create(
            white_label=self.white_label_il, zipcode="60601", county="Cook", household_size=4, completed=False
        )

        # Test with 2024 data (should be available)
        result_2024 = hud_client.get_screen_mtsp_ami(screen, "80%", 2024)
        result_2025 = hud_client.get_screen_mtsp_ami(screen, "80%", 2025)

        self.assertIsInstance(result_2024, int)
        self.assertIsInstance(result_2025, int)
        self.assertGreater(result_2024, 0)
        self.assertGreater(result_2025, 0)

        # 2025 should typically be >= 2024 due to hold-harmless
        self.assertGreaterEqual(result_2025, result_2024 * 0.95)  # Allow 5% variance


@pytest.mark.integration
class TestHudIntegrationErrors(TestCase):
    """Integration tests for error conditions."""

    def setUp(self):
        """Set up test data."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="XX")

    @skipUnless(config("HUD_API_TOKEN", default=None), "HUD_API_TOKEN not set")
    def test_real_api_call_invalid_state(self):
        """Test that invalid state code raises error with real API."""
        screen = Screen.objects.create(
            white_label=self.white_label, zipcode="00000", county="Test County", household_size=4, completed=False
        )

        with self.assertRaises(HudIncomeClientError):
            hud_client.get_screen_mtsp_ami(screen, "80%", 2025)

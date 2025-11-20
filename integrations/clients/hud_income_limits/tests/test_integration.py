"""
Integration tests for HUD API client.

These tests use VCR to record/replay HTTP interactions:
- In CI (PRs): Uses VCR cassettes only (VCR_MODE=none, no credentials needed)
- In CI (push to main): Makes real API calls (VCR_MODE=new_episodes, validates integrations)
- Locally: Uses cassettes by default (VCR_MODE=once), records new ones if missing
- Force re-record all: VCR_MODE=all pytest -m integration

VCR automatically scrubs all sensitive data (API keys, tokens, etc.) from cassettes.

Run integration tests with: pytest -m integration
Skip integration tests with: pytest -m "not integration"
"""

import os
import time
import pytest
from django.test import TestCase
from decouple import config
from django.core.cache import cache

from integrations.clients.hud_income_limits import hud_client, HudIncomeClientError
from screener.models import Screen, WhiteLabel


@pytest.mark.integration
class TestHudIntegrationMTSP(TestCase):
    """Integration tests for MTSP (Multifamily Tax Subsidy Project) endpoint."""

    @classmethod
    def setUpClass(cls):
        """Set up test class."""
        super().setUpClass()
        # Check if we're using real API calls (VCR_MODE is "new_episodes" or "all")
        vcr_mode = os.getenv("VCR_MODE", "once").lower()
        cls.using_real_api = vcr_mode in ["new_episodes", "all"]
        cls.has_token = config("HUD_API_TOKEN", default=None) is not None

    def setUp(self):
        """Set up test data."""
        cache.clear()
        # Skip test if real API calls are needed but token is missing
        if self.using_real_api and not self.has_token:
            pytest.skip("Real API call requested but HUD_API_TOKEN not set")

        self.white_label_il = WhiteLabel.objects.create(
            name="Illinois Integration Test", code="il_integration", state_code="IL"
        )

        self.white_label_co = WhiteLabel.objects.create(
            name="Colorado Integration Test", code="co_integration", state_code="CO"
        )

    def test_real_api_call_cook_county_il(self):
        """Test actual API call for Cook County, IL (or use VCR cassette)."""
        screen = Screen.objects.create(
            white_label=self.white_label_il, zipcode="60601", county="Cook", household_size=4, completed=False
        )

        # Make real API call
        result = hud_client.get_screen_mtsp_ami(screen, "80%", 2025)

        # Verify result is reasonable (Cook County IL should have high AMI)
        self.assertIsInstance(result, int)
        self.assertGreater(result, 50000, "Cook County 80% AMI should be > $50k")
        self.assertLess(result, 200000, "Cook County 80% AMI should be < $200k")

    def test_real_api_call_denver_county_co(self):
        """Test actual API call for Denver County, CO."""
        screen = Screen.objects.create(
            white_label=self.white_label_co, zipcode="80202", county="Denver", household_size=4, completed=False
        )

        result = hud_client.get_screen_mtsp_ami(screen, "80%", 2025)

        self.assertIsInstance(result, int)
        self.assertGreater(result, 40000, "Denver County 80% AMI should be > $40k")
        self.assertLess(result, 200000, "Denver County 80% AMI should be < $200k")

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

    def test_real_api_call_caching(self):
        """Test that caching works with real MTSP API calls."""
        screen = Screen.objects.create(
            white_label=self.white_label_il, zipcode="60601", county="Cook", household_size=4, completed=False
        )

        # First call - should hit API
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
        print(f"MTSP - First call: {first_call_time:.3f}s, Second call: {second_call_time:.3f}s")

    def test_real_api_call_historical_year(self):
        """Test MTSP API call with historical year data."""
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
class TestHudIntegrationStandardIL(TestCase):
    """Integration tests for Standard Section 8 Income Limits endpoint."""

    @classmethod
    def setUpClass(cls):
        """Set up test class."""
        super().setUpClass()
        # Check if we're using real API calls (VCR_MODE is "new_episodes" or "all")
        vcr_mode = os.getenv("VCR_MODE", "once").lower()
        cls.using_real_api = vcr_mode in ["new_episodes", "all"]
        cls.has_token = config("HUD_API_TOKEN", default=None) is not None

    def setUp(self):
        """Set up test data."""
        cache.clear()
        # Skip test if real API calls are needed but token is missing
        if self.using_real_api and not self.has_token:
            pytest.skip("Real API call requested but HUD_API_TOKEN not set")

        self.white_label_il = WhiteLabel.objects.create(
            name="Illinois Integration Test IL", code="il_integration_il", state_code="IL"
        )

        self.white_label_co = WhiteLabel.objects.create(
            name="Colorado Integration Test IL", code="co_integration_il", state_code="CO"
        )

    def test_real_api_call_standard_il_cook_county(self):
        """Test actual Standard IL API call for Cook County, IL."""
        screen = Screen.objects.create(
            white_label=self.white_label_il, zipcode="60601", county="Cook", household_size=4, completed=False
        )

        # Make real API call to Standard IL endpoint
        result = hud_client.get_screen_il_ami(screen, "80%", 2025)

        # Verify result is reasonable (Cook County IL should have high AMI)
        self.assertIsInstance(result, int)
        self.assertGreater(result, 50000, "Cook County 80% AMI should be > $50k")
        self.assertLess(result, 200000, "Cook County 80% AMI should be < $200k")

    def test_real_api_call_standard_il_denver_county(self):
        """Test actual Standard IL API call for Denver County, CO."""
        screen = Screen.objects.create(
            white_label=self.white_label_co, zipcode="80202", county="Denver", household_size=4, completed=False
        )

        result = hud_client.get_screen_il_ami(screen, "80%", 2025)

        self.assertIsInstance(result, int)
        self.assertGreater(result, 40000, "Denver County 80% AMI should be > $40k")
        self.assertLess(result, 200000, "Denver County 80% AMI should be < $200k")

    def test_real_api_call_standard_il_all_percentages(self):
        """Test all Standard IL percentage levels (30%, 50%, 80%) with real API."""
        screen = Screen.objects.create(
            white_label=self.white_label_il, zipcode="60601", county="Cook", household_size=4, completed=False
        )

        percentages = ["30%", "50%", "80%"]
        results = {}

        for percent in percentages:
            result = hud_client.get_screen_il_ami(screen, percent, 2025)
            results[percent] = result
            self.assertIsInstance(result, int)
            self.assertGreater(result, 0)

        # Verify percentages are in ascending order
        self.assertLess(results["30%"], results["50%"], "30% should be less than 50%")
        self.assertLess(results["50%"], results["80%"], "50% should be less than 80%")

    def test_real_api_call_standard_il_different_household_sizes(self):
        """Test different household sizes with Standard IL API."""
        household_sizes = [1, 2, 4, 8]
        results = {}

        for size in household_sizes:
            screen = Screen.objects.create(
                white_label=self.white_label_il, zipcode="60601", county="Cook", household_size=size, completed=False
            )

            result = hud_client.get_screen_il_ami(screen, "80%", 2025)
            results[size] = result
            self.assertIsInstance(result, int)
            self.assertGreater(result, 0)

        # Verify larger households have higher income limits
        self.assertLess(results[1], results[2])
        self.assertLess(results[2], results[4])
        self.assertLess(results[4], results[8])

    def test_real_api_call_standard_il_caching(self):
        """Test that caching works with real Standard IL API calls."""
        screen = Screen.objects.create(
            white_label=self.white_label_il, zipcode="60601", county="Cook", household_size=4, completed=False
        )

        # First call - should hit API
        start = time.time()
        result1 = hud_client.get_screen_il_ami(screen, "80%", 2025)
        first_call_time = time.time() - start

        # Second call - should use cache (much faster)
        start = time.time()
        result2 = hud_client.get_screen_il_ami(screen, "80%", 2025)
        second_call_time = time.time() - start

        # Results should be identical
        self.assertEqual(result1, result2)

        # Cached call should be significantly faster
        print(f"Standard IL - First call: {first_call_time:.3f}s, Second call: {second_call_time:.3f}s")

    def test_real_api_call_standard_il_historical_year(self):
        """Test Standard IL API call with historical year data."""
        screen = Screen.objects.create(
            white_label=self.white_label_il, zipcode="60601", county="Cook", household_size=4, completed=False
        )

        # Test with 2024 data (should be available)
        result_2024 = hud_client.get_screen_il_ami(screen, "80%", 2024)
        result_2025 = hud_client.get_screen_il_ami(screen, "80%", 2025)

        self.assertIsInstance(result_2024, int)
        self.assertIsInstance(result_2025, int)
        self.assertGreater(result_2024, 0)
        self.assertGreater(result_2025, 0)

        # Note: Standard IL can decrease year-over-year (unlike MTSP), so we just verify both are positive
        # Allow for significant variance between years
        self.assertGreater(result_2024, 30000)  # Sanity check
        self.assertGreater(result_2025, 30000)  # Sanity check

    def test_mtsp_vs_standard_il_comparison(self):
        """Compare MTSP and Standard IL results to verify they may differ."""
        screen = Screen.objects.create(
            white_label=self.white_label_il, zipcode="60601", county="Cook", household_size=4, completed=False
        )

        # Get both MTSP and Standard IL for same parameters
        mtsp_result = hud_client.get_screen_mtsp_ami(screen, "80%", 2025)
        il_result = hud_client.get_screen_il_ami(screen, "80%", 2025)

        # Both should be positive integers
        self.assertIsInstance(mtsp_result, int)
        self.assertIsInstance(il_result, int)
        self.assertGreater(mtsp_result, 0)
        self.assertGreater(il_result, 0)

        # They may be equal or differ slightly depending on year and economic conditions
        # Just verify they're in the same ballpark (within 20% of each other)
        ratio = max(mtsp_result, il_result) / min(mtsp_result, il_result)
        self.assertLess(ratio, 1.2, "MTSP and Standard IL should be within 20% of each other")


@pytest.mark.integration
class TestHudIntegrationErrors(TestCase):
    """Integration tests for error conditions across both endpoints."""

    def setUp(self):
        """Set up test data."""
        cache.clear()

        self.white_label_invalid = WhiteLabel.objects.create(name="Test State", code="test", state_code="XX")
        self.white_label_il = WhiteLabel.objects.create(
            name="Illinois Integration Test Errors", code="il_integration_errors", state_code="IL"
        )

    def test_mtsp_invalid_state(self):
        """Test that invalid state code raises error with real MTSP API."""
        screen = Screen.objects.create(
            white_label=self.white_label_invalid,
            zipcode="00000",
            county="Test County",
            household_size=4,
            completed=False,
        )

        with self.assertRaises(HudIncomeClientError):
            hud_client.get_screen_mtsp_ami(screen, "80%", 2025)

    def test_mtsp_invalid_county(self):
        """Test that invalid county raises error with real MTSP API."""
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

    def test_standard_il_invalid_state(self):
        """Test that invalid state code raises error with real Standard IL API."""
        screen = Screen.objects.create(
            white_label=self.white_label_invalid,
            zipcode="00000",
            county="Test County",
            household_size=4,
            completed=False,
        )

        with self.assertRaises(HudIncomeClientError):
            hud_client.get_screen_il_ami(screen, "80%", 2025)

    def test_standard_il_invalid_county(self):
        """Test that invalid county raises error with real Standard IL API."""
        screen = Screen.objects.create(
            white_label=self.white_label_il,
            zipcode="00000",
            county="Nonexistent County",
            household_size=4,
            completed=False,
        )

        with self.assertRaises(HudIncomeClientError) as context:
            hud_client.get_screen_il_ami(screen, "80%", 2025)

        self.assertIn("County not found", str(context.exception))

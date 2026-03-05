"""
Unit tests for HUD Income Limits API Client.

These tests mock HUD API responses to test client logic without
requiring actual API credentials or network calls.
"""

import copy
import requests
from contextlib import contextmanager
from typing import Any
from django.test import TestCase
from unittest.mock import Mock, patch
from django.core.cache import cache

from integrations.clients.hud_income_limits.client import (
    HudIncomeClient,
    HudIncomeClientError,
    MtspAmiPercent,
    Section8AmiPercent,
)
from screener.models import Screen, WhiteLabel


# Shared test fixtures
class HudClientTestBase(TestCase):
    """Base test class with shared mock data fixtures."""

    @classmethod
    def setUpTestData(cls) -> None:
        """Set up shared mock data for all HUD client tests."""
        # Mock counties response used across all tests
        cls.mock_counties_response = [
            {"county_name": "Cook County", "fips_code": "17031"},
            {"county_name": "DuPage County", "fips_code": "17043"},
        ]

    def setUp(self) -> None:
        """Set up test screen and white label."""
        cache.clear()

        self.white_label = WhiteLabel.objects.create(name="Illinois Test", code="il_test", state_code="IL")
        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="60601", county="Cook", household_size=4, completed=False
        )

    @contextmanager
    def mock_api_responses(self, client: HudIncomeClient, *responses: Any):
        """
        Helper to mock sequential API responses.

        Args:
            client: HudIncomeClient instance
            *responses: Sequence of mock responses to return

        Yields:
            Mock object for additional assertions if needed
        """
        with patch.object(client, "_api_request", side_effect=responses) as mock_api:
            yield mock_api


class TestHudIncomeClientMTSP(HudClientTestBase):
    """Test MTSP endpoint-specific functionality."""

    def setUp(self):
        """Set up MTSP-specific mock data."""
        super().setUp()

        # Mock MTSP API response for Cook County, IL
        self.mock_mtsp_response = {
            "data": {
                "20percent": {
                    "il20_p1": 18140,
                    "il20_p2": 20740,
                    "il20_p3": 23320,
                    "il20_p4": 25900,
                    "il20_p5": 27980,
                    "il20_p6": 30060,
                    "il20_p7": 32140,
                    "il20_p8": 34220,
                },
                "30percent": {
                    "il30_p1": 27210,
                    "il30_p2": 31110,
                    "il30_p3": 34980,
                    "il30_p4": 38850,
                    "il30_p5": 41970,
                    "il30_p6": 45090,
                    "il30_p7": 48210,
                    "il30_p8": 51330,
                },
                "40percent": {
                    "il40_p1": 36280,
                    "il40_p2": 41480,
                    "il40_p3": 46640,
                    "il40_p4": 51800,
                    "il40_p5": 55960,
                    "il40_p6": 60120,
                    "il40_p7": 64280,
                    "il40_p8": 68440,
                },
                "50percent": {
                    "il50_p1": 45350,
                    "il50_p2": 51850,
                    "il50_p3": 58300,
                    "il50_p4": 64750,
                    "il50_p5": 69950,
                    "il50_p6": 75150,
                    "il50_p7": 80350,
                    "il50_p8": 85550,
                },
                "60percent": {
                    "il60_p1": 54420,
                    "il60_p2": 62220,
                    "il60_p3": 69960,
                    "il60_p4": 77700,
                    "il60_p5": 83940,
                    "il60_p6": 90180,
                    "il60_p7": 96420,
                    "il60_p8": 102660,
                },
                "70percent": {
                    "il70_p1": 63490,
                    "il70_p2": 72590,
                    "il70_p3": 81620,
                    "il70_p4": 90650,
                    "il70_p5": 97930,
                    "il70_p6": 105210,
                    "il70_p7": 112490,
                    "il70_p8": 119770,
                },
                "80percent": {
                    "il80_p1": 72560,
                    "il80_p2": 82960,
                    "il80_p3": 93280,
                    "il80_p4": 103600,
                    "il80_p5": 111920,
                    "il80_p6": 120240,
                    "il80_p7": 128560,
                    "il80_p8": 136880,
                },
                "median_income": 90700,
            }
        }

    def test_get_screen_mtsp_ami_80_percent_success(self) -> None:
        """Test successful MTSP AMI lookup for 80% AMI."""
        client = HudIncomeClient(api_token="test_token")

        with self.mock_api_responses(client, self.mock_counties_response, self.mock_mtsp_response):
            result = client.get_screen_mtsp_ami(self.screen, "80%", "2025")
            self.assertEqual(result, 103600)

    def test_get_screen_mtsp_ami_all_percentages(self) -> None:
        """Test all supported MTSP percentage levels (20% through 100%)."""
        client = HudIncomeClient(api_token="test_token")

        test_cases: list[tuple[MtspAmiPercent, int]] = [
            ("20%", 25900),
            ("30%", 38850),
            ("40%", 51800),
            ("50%", 64750),
            ("60%", 77700),
            ("70%", 90650),
            ("80%", 103600),
            ("100%", 90700),  # median_income
        ]

        for percent, expected in test_cases:
            with self.mock_api_responses(client, self.mock_counties_response, self.mock_mtsp_response):
                result = client.get_screen_mtsp_ami(self.screen, percent, "2025")
                self.assertEqual(result, expected, f"Failed for {percent}")
            cache.clear()

    def test_get_screen_mtsp_ami_caching(self) -> None:
        """Test that MTSP API responses are cached properly."""
        client = HudIncomeClient(api_token="test_token")

        with self.mock_api_responses(client, self.mock_counties_response, self.mock_mtsp_response) as mock_api:
            result1 = client.get_screen_mtsp_ami(self.screen, "80%", "2025")
            result2 = client.get_screen_mtsp_ami(self.screen, "80%", "2025")

            self.assertEqual(result1, result2)
            self.assertEqual(mock_api.call_count, 2)

    def test_missing_percentage_data_raises_error(self) -> None:
        """Test that missing MTSP percentage category raises error."""
        client = HudIncomeClient(api_token="test_token")

        incomplete_data = self.mock_mtsp_response.copy()
        del incomplete_data["data"]["80percent"]

        with self.mock_api_responses(client, self.mock_counties_response, incomplete_data):
            with self.assertRaisesRegex(HudIncomeClientError, r"80%"):
                client.get_screen_mtsp_ami(self.screen, "80%", "2025")

    def test_missing_household_size_data_raises_error(self) -> None:
        """Test that missing household size field in MTSP data raises error."""
        client = HudIncomeClient(api_token="test_token")

        incomplete_data = self.mock_mtsp_response.copy()
        del incomplete_data["data"]["80percent"]["il80_p4"]

        with self.mock_api_responses(client, self.mock_counties_response, incomplete_data):
            with self.assertRaisesRegex(HudIncomeClientError, r"household size"):
                client.get_screen_mtsp_ami(self.screen, "80%", "2025")

    def test_missing_median_income_for_100_percent(self) -> None:
        """Test that missing median income for 100% AMI raises error."""
        client = HudIncomeClient(api_token="test_token")

        incomplete_data = self.mock_mtsp_response.copy()
        del incomplete_data["data"]["median_income"]

        with self.mock_api_responses(client, self.mock_counties_response, incomplete_data):
            with self.assertRaisesRegex(HudIncomeClientError, r"No median income data available"):
                client.get_screen_mtsp_ami(self.screen, "100%", "2025")

    def test_empty_mtsp_response(self) -> None:
        """Test that empty MTSP response raises error."""
        client = HudIncomeClient(api_token="test_token")

        with self.mock_api_responses(client, self.mock_counties_response, {}):
            with self.assertRaisesRegex(HudIncomeClientError, r"No income limit data found"):
                client.get_screen_mtsp_ami(self.screen, "80%", "2025")


class TestHudIncomeClientStandardIL(HudClientTestBase):
    """Test Standard Section 8 Income Limits endpoint-specific functionality."""

    def setUp(self):
        """Set up Standard IL-specific mock data."""
        super().setUp()

        # Mock Standard IL API response for Cook County, IL
        # Matches actual HUD API structure with nested categories
        self.mock_il_response = {
            "data": {
                "median_income": 90700,
                "extremely_low": {
                    "il30_p1": 27210,
                    "il30_p2": 31110,
                    "il30_p3": 34980,
                    "il30_p4": 38850,
                    "il30_p5": 41970,
                    "il30_p6": 45090,
                    "il30_p7": 48210,
                    "il30_p8": 51330,
                },
                "very_low": {
                    "il50_p1": 45350,
                    "il50_p2": 51850,
                    "il50_p3": 58300,
                    "il50_p4": 64750,
                    "il50_p5": 69950,
                    "il50_p6": 75150,
                    "il50_p7": 80350,
                    "il50_p8": 85550,
                },
                "low": {
                    "il80_p1": 72560,
                    "il80_p2": 82960,
                    "il80_p3": 93280,
                    "il80_p4": 103600,
                    "il80_p5": 111920,
                    "il80_p6": 120240,
                    "il80_p7": 128560,
                    "il80_p8": 136880,
                },
            }
        }

    def test_get_screen_il_ami_80_percent_success(self) -> None:
        """Test successful Standard IL AMI lookup for 80% AMI."""
        client = HudIncomeClient(api_token="test_token")

        with self.mock_api_responses(client, self.mock_counties_response, self.mock_il_response):
            result = client.get_screen_il_ami(self.screen, "80%", "2025")
            self.assertEqual(result, 103600)

    def test_get_screen_il_ami_all_percentages(self) -> None:
        """Test all supported Standard IL percentage levels (30%, 50%, 80%)."""
        client = HudIncomeClient(api_token="test_token")

        test_cases: list[tuple[Section8AmiPercent, int]] = [
            ("30%", 38850),
            ("50%", 64750),
            ("80%", 103600),
        ]

        for percent, expected in test_cases:
            with self.mock_api_responses(client, self.mock_counties_response, self.mock_il_response):
                result = client.get_screen_il_ami(self.screen, percent, "2025")
                self.assertEqual(result, expected, f"Failed for {percent}")
            cache.clear()

    def test_get_screen_il_ami_caching(self) -> None:
        """Test that Standard IL API responses are cached properly."""
        client = HudIncomeClient(api_token="test_token")

        with self.mock_api_responses(client, self.mock_counties_response, self.mock_il_response) as mock_api:
            result1 = client.get_screen_il_ami(self.screen, "80%", "2025")
            result2 = client.get_screen_il_ami(self.screen, "80%", "2025")

            self.assertEqual(result1, result2)
            self.assertEqual(mock_api.call_count, 2)

    def test_get_screen_il_ami_missing_field(self) -> None:
        """Test that missing Standard IL field raises error."""
        client = HudIncomeClient(api_token="test_token")

        incomplete_data = copy.deepcopy(self.mock_il_response)
        del incomplete_data["data"]["low"]["il80_p4"]

        with self.mock_api_responses(client, self.mock_counties_response, incomplete_data):
            with self.assertRaisesRegex(HudIncomeClientError, r"No 80% AMI data"):
                client.get_screen_il_ami(self.screen, "80%", "2025")

    def test_empty_il_response_empty_dict(self) -> None:
        """Test that empty dict Standard IL response raises error."""
        client = HudIncomeClient(api_token="test_token")

        with self.mock_api_responses(client, self.mock_counties_response, {}):
            with self.assertRaisesRegex(HudIncomeClientError, r"No income limit data found"):
                client.get_screen_il_ami(self.screen, "80%", "2025")

    def test_empty_il_response_none(self) -> None:
        """Test that None Standard IL response raises error."""
        client = HudIncomeClient(api_token="test_token")

        with self.mock_api_responses(client, self.mock_counties_response, None):
            with self.assertRaisesRegex(HudIncomeClientError, r"No income limit data found"):
                client.get_screen_il_ami(self.screen, "80%", "2025")

    def test_empty_il_response_missing_data_key(self) -> None:
        """Test that Standard IL response without 'data' key raises error."""
        client = HudIncomeClient(api_token="test_token")

        with self.mock_api_responses(client, self.mock_counties_response, {"error": "some error"}):
            with self.assertRaisesRegex(HudIncomeClientError, r"No income limit data found"):
                client.get_screen_il_ami(self.screen, "80%", "2025")

    def test_standard_il_empty_category_data(self) -> None:
        """Test Standard IL when category exists but contains empty dict."""
        client = HudIncomeClient(api_token="test_token")

        incomplete_data = copy.deepcopy(self.mock_il_response)
        incomplete_data["data"]["low"] = {}  # Category exists but empty

        with self.mock_api_responses(client, self.mock_counties_response, incomplete_data):
            with self.assertRaisesRegex(HudIncomeClientError, r"No 80% AMI data"):
                client.get_screen_il_ami(self.screen, "80%", "2025")


class TestHudIncomeClientApproximate(HudClientTestBase):
    """Test approximate_screen_mtsp_ami linear interpolation method."""

    def setUp(self):
        super().setUp()

        # Mock MTSP response with 60% and 70% tiers for Cook County, HH size 4
        self.mock_mtsp_response = {
            "data": {
                "60percent": {"il60_p4": 79440},
                "70percent": {"il70_p4": 88800},
                "median_income": 90700,
            }
        }

    def test_65_percent_returns_midpoint_of_60_and_70(self) -> None:
        """65% AMI is linearly interpolated as (79440 + 88800) // 2 = 84120."""
        client = HudIncomeClient(api_token="test_token")

        with self.mock_api_responses(client, self.mock_counties_response, self.mock_mtsp_response):
            result = client.approximate_screen_mtsp_ami(self.screen, "65%", "2025")
            self.assertEqual(result, 84120)

    def test_exact_tier_returns_value_without_second_api_call(self) -> None:
        """When target is exactly on a supported tier, only one API call is needed."""
        client = HudIncomeClient(api_token="test_token")

        exact_response = {"data": {"60percent": {"il60_p4": 79440}, "median_income": 90700}}
        with self.mock_api_responses(client, self.mock_counties_response, exact_response) as mock_api:
            result = client.approximate_screen_mtsp_ami(self.screen, "60%", "2025")
            self.assertEqual(result, 79440)
            # Only one MTSP data call (no second tier needed)
            self.assertEqual(mock_api.call_count, 2)  # counties + one MTSP fetch

    def test_non_midpoint_interpolation(self) -> None:
        """63% AMI is 30% of the way from 60% to 70%: 79440 + 0.3 * (88800 - 79440) = 82248."""
        client = HudIncomeClient(api_token="test_token")

        with self.mock_api_responses(client, self.mock_counties_response, self.mock_mtsp_response):
            result = client.approximate_screen_mtsp_ami(self.screen, "63%", "2025")
            self.assertEqual(result, int(79440 + 0.3 * (88800 - 79440)))

    def test_integer_target_accepted(self) -> None:
        """Integer target (65) is accepted as well as string ("65%")."""
        client = HudIncomeClient(api_token="test_token")

        with self.mock_api_responses(client, self.mock_counties_response, self.mock_mtsp_response):
            result = client.approximate_screen_mtsp_ami(self.screen, 65, "2025")
            self.assertEqual(result, 84120)

    def test_out_of_range_raises_error(self) -> None:
        """Targets outside [20, 100] raise HudIncomeClientError."""
        client = HudIncomeClient(api_token="test_token")

        with self.assertRaisesRegex(HudIncomeClientError, r"outside the supported MTSP range"):
            client.approximate_screen_mtsp_ami(self.screen, "10%", "2025")

        with self.assertRaisesRegex(HudIncomeClientError, r"outside the supported MTSP range"):
            client.approximate_screen_mtsp_ami(self.screen, "105%", "2025")

    def test_propagates_hud_api_error(self) -> None:
        """HudIncomeClientError from the underlying API call propagates unchanged."""
        client = HudIncomeClient(api_token="test_token")

        with self.mock_api_responses(client, []):  # empty counties → county not found
            with self.assertRaises(HudIncomeClientError):
                client.approximate_screen_mtsp_ami(self.screen, "65%", "2025")

    def test_uses_county_override(self) -> None:
        """county_override is forwarded to the underlying get_screen_mtsp_ami calls."""
        client = HudIncomeClient(api_token="test_token")

        middlesex_counties = [{"county_name": "Middlesex County", "fips_code": "25017"}]
        with self.mock_api_responses(client, middlesex_counties, self.mock_mtsp_response) as mock_api:
            result = client.approximate_screen_mtsp_ami(self.screen, "65%", "2025", county_override="Middlesex")
            self.assertEqual(result, 84120)
            first_call_endpoint = mock_api.call_args_list[0][0][0]
            self.assertIn("listCounties", first_call_endpoint)


class TestHudIncomeClientValidation(HudClientTestBase):
    """Test shared validation logic across both endpoints."""

    def test_household_size_validation_too_small(self) -> None:
        """Test that household size < 1 raises error for both endpoints."""
        self.screen.household_size = 0
        client = HudIncomeClient(api_token="test_token")

        with self.assertRaisesRegex(HudIncomeClientError, r"between 1 and 8"):
            client.get_screen_mtsp_ami(self.screen, "80%", "2025")

        with self.assertRaisesRegex(HudIncomeClientError, r"between 1 and 8"):
            client.get_screen_il_ami(self.screen, "80%", "2025")

    def test_household_size_validation_too_large(self) -> None:
        """Test that household size > 8 raises error for both endpoints."""
        self.screen.household_size = 9
        client = HudIncomeClient(api_token="test_token")

        with self.assertRaisesRegex(HudIncomeClientError, r"between 1 and 8"):
            client.get_screen_mtsp_ami(self.screen, "80%", "2025")

        with self.assertRaisesRegex(HudIncomeClientError, r"between 1 and 8"):
            client.get_screen_il_ami(self.screen, "80%", "2025")

    def test_missing_api_token_raises_error(self) -> None:
        """Test that missing API token raises descriptive error."""
        with patch("integrations.clients.hud_income_limits.client.config") as mock_config:
            mock_config.return_value = None
            client = HudIncomeClient()

            with self.assertRaisesRegex(HudIncomeClientError, r"HUD_API_TOKEN"):
                _ = client.headers


class TestHudIncomeClientCountyLookup(HudClientTestBase):
    """Test county FIPS code lookup functionality."""

    def setUp(self) -> None:
        """Set up minimal mock MTSP response for county lookup tests."""
        super().setUp()

        # Minimal MTSP response for county lookup tests
        self.mock_mtsp_response = {
            "data": {
                "80percent": {"il80_p4": 103600},
                "median_income": 90700,
            }
        }

    def test_county_not_found_raises_error(self) -> None:
        """Test that invalid county raises error."""
        client = HudIncomeClient(api_token="test_token")
        self.screen.county = "Nonexistent"

        with self.mock_api_responses(client, self.mock_counties_response):
            with self.assertRaisesRegex(HudIncomeClientError, r"County not found"):
                client.get_screen_mtsp_ami(self.screen, "80%", "2025")

    def test_county_name_normalization(self) -> None:
        """Test that county names are normalized correctly (adds 'County' suffix)."""
        client = HudIncomeClient(api_token="test_token")

        # Test without " County" suffix
        self.screen.county = "Cook"

        with self.mock_api_responses(client, self.mock_counties_response, self.mock_mtsp_response):
            result = client.get_screen_mtsp_ami(self.screen, "80%", "2025")
            self.assertEqual(result, 103600)

    def test_county_lookup_includes_year_parameter(self) -> None:
        """Test that county lookup includes 'year' and 'updated' parameters per HUD API spec."""
        client = HudIncomeClient(api_token="test_token")

        with self.mock_api_responses(client, self.mock_counties_response, self.mock_mtsp_response) as mock_api:
            client.get_screen_mtsp_ami(self.screen, "80%", 2025)

            # Verify first call (county lookup) includes both 'year' and 'updated' parameters for 2025+
            first_call_args = mock_api.call_args_list[0]
            self.assertEqual(first_call_args[0][0], "fmr/listCounties/IL")
            self.assertEqual(first_call_args[0][1], {"year": "2025", "updated": "2025"})

    def test_county_lookup_2024_only_includes_year_not_updated(self) -> None:
        """Test that county lookup for 2024 includes 'year' but NOT 'updated' parameter."""
        client = HudIncomeClient(api_token="test_token")

        with self.mock_api_responses(client, self.mock_counties_response, self.mock_mtsp_response) as mock_api:
            client.get_screen_mtsp_ami(self.screen, "80%", 2024)

            # Verify first call (county lookup) includes ONLY 'year' for pre-2025
            first_call_args = mock_api.call_args_list[0]
            self.assertEqual(first_call_args[0][0], "fmr/listCounties/IL")
            self.assertEqual(first_call_args[0][1], {"year": "2024"})
            # Explicitly verify 'updated' is NOT present
            self.assertNotIn("updated", first_call_args[0][1])

    def test_empty_counties_list(self) -> None:
        """Test that empty counties list raises error."""
        client = HudIncomeClient(api_token="test_token")

        with self.mock_api_responses(client, []):
            with self.assertRaisesRegex(HudIncomeClientError, r"Could not retrieve counties"):
                client._get_entity_id("TS", "Test County", 2025)


class TestHudIncomeClientHTTPErrors(TestCase):
    """Test HTTP and network error handling."""

    def test_successful_api_request(self) -> None:
        """Test successful API request returns JSON data."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status = Mock()

        client = HudIncomeClient(api_token="test_token")

        with patch.object(client._session, "get", return_value=mock_response):
            result = client._api_request("test/endpoint")

            self.assertEqual(result, {"data": "test"})
            mock_response.raise_for_status.assert_called_once()

    def test_401_authentication_error(self) -> None:
        """Test 401 authentication error handling."""
        mock_response = Mock()
        mock_response.status_code = 401
        http_error = requests.exceptions.HTTPError("401 Unauthorized")
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error

        client = HudIncomeClient(api_token="invalid_token")

        with patch.object(client._session, "get", return_value=mock_response):
            with self.assertRaisesRegex(HudIncomeClientError, r"Authentication failed"):
                client._api_request("test/endpoint")

    def test_403_access_denied_error(self) -> None:
        """Test 403 access denied error handling."""
        mock_response = Mock()
        mock_response.status_code = 403
        http_error = requests.exceptions.HTTPError("403 Forbidden")
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error

        client = HudIncomeClient(api_token="test_token")

        with patch.object(client._session, "get", return_value=mock_response):
            with self.assertRaisesRegex(HudIncomeClientError, r"Access denied.*FMR and Income Limits"):
                client._api_request("test/endpoint")

    def test_404_data_not_found_error(self) -> None:
        """Test 404 data not found error handling."""
        mock_response = Mock()
        mock_response.status_code = 404
        http_error = requests.exceptions.HTTPError("404 Not Found")
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error

        client = HudIncomeClient(api_token="test_token")

        with patch.object(client._session, "get", return_value=mock_response):
            with self.assertRaisesRegex(HudIncomeClientError, r"Data not found"):
                client._api_request("test/endpoint")

    def test_500_server_error(self) -> None:
        """Test 500 server error handling."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        http_error = requests.exceptions.HTTPError("500 Server Error")
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error

        client = HudIncomeClient(api_token="test_token")

        with patch.object(client._session, "get", return_value=mock_response):
            with self.assertRaisesRegex(HudIncomeClientError, r"API request failed \(500\).*Internal Server Error"):
                client._api_request("test/endpoint")

    def test_network_error_handling(self) -> None:
        """Test network error handling."""
        client = HudIncomeClient(api_token="test_token")

        with patch.object(client._session, "get", side_effect=requests.exceptions.RequestException("Network error")):
            with self.assertRaisesRegex(HudIncomeClientError, r"Request failed"):
                client._api_request("test/endpoint")

    def test_retry_configuration(self) -> None:
        """Test that client is configured with retry strategy."""
        client = HudIncomeClient(api_token="test_token", max_retries=3)

        # Verify session exists and has retry adapters
        self.assertIsNotNone(client._session)

        # Check that adapters are mounted for both http and https
        self.assertIn("http://", client._session.adapters)
        self.assertIn("https://", client._session.adapters)

        # Verify the adapter has a retry configuration
        https_adapter = client._session.get_adapter("https://")
        self.assertIsNotNone(https_adapter.max_retries)

    def test_connection_error_propagates_after_retries(self) -> None:
        """Test that connection errors are caught and wrapped properly."""
        client = HudIncomeClient(api_token="test_token", max_retries=2)

        with patch.object(client._session, "get") as mock_session_get:
            # Simulate connection error
            mock_session_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

            with self.assertRaisesRegex(HudIncomeClientError, r"Connection failed"):
                client._api_request("test/endpoint")

    def test_max_retries_parameter(self) -> None:
        """Test that max_retries parameter configures retry behavior."""
        # Test with 0 retries
        client_no_retry = HudIncomeClient(api_token="test_token", max_retries=0)
        https_adapter = client_no_retry._session.get_adapter("https://")
        self.assertEqual(https_adapter.max_retries.total, 0)

        # Test with 5 retries
        client_five_retries = HudIncomeClient(api_token="test_token", max_retries=5)
        https_adapter = client_five_retries._session.get_adapter("https://")
        self.assertEqual(https_adapter.max_retries.total, 5)

    def test_429_rate_limit_error(self) -> None:
        """Test 429 rate limit error handling."""
        mock_response = Mock()
        mock_response.status_code = 429
        http_error = requests.exceptions.HTTPError("429 Too Many Requests")
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error

        client = HudIncomeClient(api_token="test_token")

        with patch.object(client._session, "get", return_value=mock_response):
            with self.assertRaisesRegex(HudIncomeClientError, r"Rate limit exceeded"):
                client._api_request("test/endpoint")

    def test_timeout_error_handling(self) -> None:
        """Test timeout error handling."""
        client = HudIncomeClient(api_token="test_token", max_retries=2)

        with patch.object(client._session, "get") as mock_session_get:
            # All attempts timeout
            mock_session_get.side_effect = requests.exceptions.Timeout("Request timed out")

            with self.assertRaisesRegex(HudIncomeClientError, r"Request timeout"):
                client._api_request("test/endpoint")

    def test_retry_strategy_configuration(self) -> None:
        """Test retry strategy is configured correctly."""
        from urllib3.util.retry import Retry

        client = HudIncomeClient(api_token="test_token", max_retries=3)
        https_adapter = client._session.get_adapter("https://")

        # Verify retry strategy properties
        retry_config: Retry = https_adapter.max_retries
        self.assertEqual(retry_config.total, 3)
        self.assertEqual(retry_config.backoff_factor, 1)
        self.assertEqual(retry_config.status_forcelist, [429, 500, 502, 503, 504])
        self.assertIn("GET", retry_config.allowed_methods)

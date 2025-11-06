"""
Unit tests for HUD Income Limits API Client.

These tests mock HUD API responses to test client logic without
requiring actual API credentials or network calls.
"""

from django.test import TestCase
from unittest.mock import Mock, patch, MagicMock
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
    def setUpTestData(cls):
        """Set up shared mock data for all HUD client tests."""
        # Mock counties response used across all tests
        cls.mock_counties_response = [
            {"county_name": "Cook County", "fips_code": "17031"},
            {"county_name": "DuPage County", "fips_code": "17043"},
        ]

    def setUp(self):
        """Set up test screen and white label."""
        cache.clear()

        self.white_label = WhiteLabel.objects.create(name="Illinois Test", code="il_test", state_code="IL")
        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="60601", county="Cook", household_size=4, completed=False
        )


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

    def test_get_screen_mtsp_ami_80_percent_success(self):
        """Test successful MTSP AMI lookup for 80% AMI."""
        client = HudIncomeClient(api_token="test_token")

        with patch.object(client, "_api_request") as mock_api:
            mock_api.side_effect = [
                self.mock_counties_response,
                self.mock_mtsp_response,
            ]

            result = client.get_screen_mtsp_ami(self.screen, "80%", "2025")

            self.assertEqual(result, 103600)
            self.assertEqual(mock_api.call_count, 2)

    def test_get_screen_mtsp_ami_all_percentages(self):
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

        with patch.object(client, "_api_request") as mock_api:
            for percent, expected in test_cases:
                mock_api.side_effect = [
                    self.mock_counties_response,
                    self.mock_mtsp_response,
                ]

                result = client.get_screen_mtsp_ami(self.screen, percent, "2025")
                self.assertEqual(result, expected, f"Failed for {percent}")

                cache.clear()

    def test_get_screen_mtsp_ami_caching(self):
        """Test that MTSP API responses are cached properly."""
        client = HudIncomeClient(api_token="test_token")

        with patch.object(client, "_api_request") as mock_api:
            mock_api.side_effect = [
                self.mock_counties_response,
                self.mock_mtsp_response,
            ]

            result1 = client.get_screen_mtsp_ami(self.screen, "80%", "2025")
            result2 = client.get_screen_mtsp_ami(self.screen, "80%", "2025")

            self.assertEqual(result1, result2)
            self.assertEqual(mock_api.call_count, 2)

    def test_missing_percentage_data_raises_error(self):
        """Test that missing MTSP percentage category raises error."""
        client = HudIncomeClient(api_token="test_token")

        incomplete_data = self.mock_mtsp_response.copy()
        del incomplete_data["data"]["80percent"]

        with patch.object(client, "_api_request") as mock_api:
            mock_api.side_effect = [
                self.mock_counties_response,
                incomplete_data,
            ]

            with self.assertRaises(HudIncomeClientError) as context:
                client.get_screen_mtsp_ami(self.screen, "80%", "2025")

            self.assertIn("80%", str(context.exception))

    def test_missing_household_size_data_raises_error(self):
        """Test that missing household size field in MTSP data raises error."""
        client = HudIncomeClient(api_token="test_token")

        incomplete_data = self.mock_mtsp_response.copy()
        del incomplete_data["data"]["80percent"]["il80_p4"]

        with patch.object(client, "_api_request") as mock_api:
            mock_api.side_effect = [
                self.mock_counties_response,
                incomplete_data,
            ]

            with self.assertRaises(HudIncomeClientError) as context:
                client.get_screen_mtsp_ami(self.screen, "80%", "2025")

            self.assertIn("household size", str(context.exception))

    def test_missing_median_income_for_100_percent(self):
        """Test that missing median income for 100% AMI raises error."""
        client = HudIncomeClient(api_token="test_token")

        incomplete_data = self.mock_mtsp_response.copy()
        del incomplete_data["data"]["median_income"]

        with patch.object(client, "_api_request") as mock_api:
            mock_api.side_effect = [
                self.mock_counties_response,
                incomplete_data,
            ]

            with self.assertRaises(HudIncomeClientError) as context:
                client.get_screen_mtsp_ami(self.screen, "100%", "2025")

            self.assertIn("No median income data available", str(context.exception))

    def test_empty_mtsp_response(self):
        """Test that empty MTSP response raises error."""
        client = HudIncomeClient(api_token="test_token")

        with patch.object(client, "_api_request") as mock_api:
            mock_api.side_effect = [
                self.mock_counties_response,
                {},
            ]

            with self.assertRaises(HudIncomeClientError) as context:
                client.get_screen_mtsp_ami(self.screen, "80%", "2025")

            self.assertIn("No income limit data found", str(context.exception))


class TestHudIncomeClientStandardIL(HudClientTestBase):
    """Test Standard Section 8 Income Limits endpoint-specific functionality."""

    def setUp(self):
        """Set up Standard IL-specific mock data."""
        super().setUp()

        # Mock Standard IL API response for Cook County, IL
        self.mock_il_response = {
            "data": {
                "l30_1": 27210,
                "l30_2": 31110,
                "l30_3": 34980,
                "l30_4": 38850,
                "l30_5": 41970,
                "l30_6": 45090,
                "l30_7": 48210,
                "l30_8": 51330,
                "l50_1": 45350,
                "l50_2": 51850,
                "l50_3": 58300,
                "l50_4": 64750,
                "l50_5": 69950,
                "l50_6": 75150,
                "l50_7": 80350,
                "l50_8": 85550,
                "l80_1": 72560,
                "l80_2": 82960,
                "l80_3": 93280,
                "l80_4": 103600,
                "l80_5": 111920,
                "l80_6": 120240,
                "l80_7": 128560,
                "l80_8": 136880,
                "median": 90700,
            }
        }

    def test_get_screen_il_ami_80_percent_success(self):
        """Test successful Standard IL AMI lookup for 80% AMI."""
        client = HudIncomeClient(api_token="test_token")

        with patch.object(client, "_api_request") as mock_api:
            mock_api.side_effect = [
                self.mock_counties_response,
                self.mock_il_response,
            ]

            result = client.get_screen_il_ami(self.screen, "80%", "2025")

            self.assertEqual(result, 103600)
            self.assertEqual(mock_api.call_count, 2)

    def test_get_screen_il_ami_all_percentages(self):
        """Test all supported Standard IL percentage levels (30%, 50%, 80%)."""
        client = HudIncomeClient(api_token="test_token")

        test_cases: list[tuple[Section8AmiPercent, int]] = [
            ("30%", 38850),
            ("50%", 64750),
            ("80%", 103600),
        ]

        with patch.object(client, "_api_request") as mock_api:
            for percent, expected in test_cases:
                mock_api.side_effect = [
                    self.mock_counties_response,
                    self.mock_il_response,
                ]

                result = client.get_screen_il_ami(self.screen, percent, "2025")
                self.assertEqual(result, expected, f"Failed for {percent}")

                cache.clear()

    def test_get_screen_il_ami_caching(self):
        """Test that Standard IL API responses are cached properly."""
        client = HudIncomeClient(api_token="test_token")

        with patch.object(client, "_api_request") as mock_api:
            mock_api.side_effect = [
                self.mock_counties_response,
                self.mock_il_response,
            ]

            result1 = client.get_screen_il_ami(self.screen, "80%", "2025")
            result2 = client.get_screen_il_ami(self.screen, "80%", "2025")

            self.assertEqual(result1, result2)
            self.assertEqual(mock_api.call_count, 2)

    def test_get_screen_il_ami_missing_field(self):
        """Test that missing Standard IL field raises error."""
        client = HudIncomeClient(api_token="test_token")

        incomplete_data = self.mock_il_response.copy()
        del incomplete_data["data"]["l80_4"]

        with patch.object(client, "_api_request") as mock_api:
            mock_api.side_effect = [
                self.mock_counties_response,
                incomplete_data,
            ]

            with self.assertRaises(HudIncomeClientError) as context:
                client.get_screen_il_ami(self.screen, "80%", "2025")

            self.assertIn("No 80% AMI data", str(context.exception))

    def test_empty_il_response(self):
        """Test that empty Standard IL response raises error."""
        client = HudIncomeClient(api_token="test_token")

        with patch.object(client, "_api_request") as mock_api:
            # Test empty dict
            mock_api.side_effect = [
                self.mock_counties_response,
                {},
            ]

            with self.assertRaises(HudIncomeClientError) as context:
                client.get_screen_il_ami(self.screen, "80%", "2025")
            self.assertIn("No income limit data found", str(context.exception))

            cache.clear()

            # Test None response
            mock_api.side_effect = [
                self.mock_counties_response,
                None,
            ]

            with self.assertRaises(HudIncomeClientError) as context:
                client.get_screen_il_ami(self.screen, "80%", "2025")
            self.assertIn("No income limit data found", str(context.exception))

            cache.clear()

            # Test response without 'data' key
            mock_api.side_effect = [
                self.mock_counties_response,
                {"error": "some error"},
            ]

            with self.assertRaises(HudIncomeClientError) as context:
                client.get_screen_il_ami(self.screen, "80%", "2025")
            self.assertIn("No income limit data found", str(context.exception))


class TestHudIncomeClientValidation(HudClientTestBase):
    """Test shared validation logic across both endpoints."""

    def test_household_size_validation_too_small(self):
        """Test that household size < 1 raises error for both endpoints."""
        self.screen.household_size = 0
        client = HudIncomeClient(api_token="test_token")

        with self.assertRaises(HudIncomeClientError) as context:
            client.get_screen_mtsp_ami(self.screen, "80%", "2025")
        self.assertIn("between 1 and 8", str(context.exception))

        with self.assertRaises(HudIncomeClientError) as context:
            client.get_screen_il_ami(self.screen, "80%", "2025")
        self.assertIn("between 1 and 8", str(context.exception))

    def test_household_size_validation_too_large(self):
        """Test that household size > 8 raises error for both endpoints."""
        self.screen.household_size = 9
        client = HudIncomeClient(api_token="test_token")

        with self.assertRaises(HudIncomeClientError) as context:
            client.get_screen_mtsp_ami(self.screen, "80%", "2025")
        self.assertIn("between 1 and 8", str(context.exception))

        with self.assertRaises(HudIncomeClientError) as context:
            client.get_screen_il_ami(self.screen, "80%", "2025")
        self.assertIn("between 1 and 8", str(context.exception))

    def test_missing_api_token_raises_error(self):
        """Test that missing API token raises descriptive error."""
        with patch("integrations.clients.hud_income_limits.client.config") as mock_config:
            mock_config.return_value = None
            client = HudIncomeClient()

            with self.assertRaises(HudIncomeClientError) as context:
                _ = client.headers

            self.assertIn("HUD_API_TOKEN", str(context.exception))


class TestHudIncomeClientCountyLookup(HudClientTestBase):
    """Test county FIPS code lookup functionality."""

    def setUp(self):
        """Set up minimal mock MTSP response for county lookup tests."""
        super().setUp()

        # Minimal MTSP response for county lookup tests
        self.mock_mtsp_response = {
            "data": {
                "80percent": {"il80_p4": 103600},
                "median_income": 90700,
            }
        }

    def test_county_not_found_raises_error(self):
        """Test that invalid county raises error."""
        client = HudIncomeClient(api_token="test_token")
        self.screen.county = "Nonexistent"

        with patch.object(client, "_api_request") as mock_api:
            mock_api.return_value = self.mock_counties_response

            with self.assertRaises(HudIncomeClientError) as context:
                client.get_screen_mtsp_ami(self.screen, "80%", "2025")

            self.assertIn("County not found", str(context.exception))

    def test_county_name_normalization(self):
        """Test that county names are normalized correctly (adds 'County' suffix)."""
        client = HudIncomeClient(api_token="test_token")

        # Test without " County" suffix
        self.screen.county = "Cook"

        with patch.object(client, "_api_request") as mock_api:
            mock_api.side_effect = [
                self.mock_counties_response,
                self.mock_mtsp_response,
            ]

            result = client.get_screen_mtsp_ami(self.screen, "80%", "2025")
            self.assertEqual(result, 103600)

    def test_county_lookup_includes_year_parameter(self):
        """Test that county lookup includes 'updated' parameter per HUD API spec."""
        client = HudIncomeClient(api_token="test_token")

        with patch.object(client, "_api_request") as mock_api:
            mock_api.side_effect = [
                self.mock_counties_response,
                self.mock_mtsp_response,
            ]

            client.get_screen_mtsp_ami(self.screen, "80%", 2025)

            # Verify first call (county lookup) includes 'updated' parameter
            first_call_args = mock_api.call_args_list[0]
            self.assertEqual(first_call_args[0][0], "fmr/listCounties/IL")
            self.assertEqual(first_call_args[0][1], {"updated": "2025"})

    def test_empty_counties_list(self):
        """Test that empty counties list raises error."""
        client = HudIncomeClient(api_token="test_token")

        with patch.object(client, "_api_request") as mock_api:
            mock_api.return_value = []

            with self.assertRaises(HudIncomeClientError) as context:
                client._get_entity_id("TS", "Test County", 2025)

            self.assertIn("Could not retrieve counties", str(context.exception))


class TestHudIncomeClientHTTPErrors(TestCase):
    """Test HTTP and network error handling."""

    def setUp(self):
        """Set up test screen."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="12345", county="Test County", household_size=4, completed=False
        )

    @patch("integrations.clients.hud_income_limits.client.requests.get")
    def test_successful_api_request(self, mock_get):
        """Test successful API request returns JSON data."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = HudIncomeClient(api_token="test_token")
        result = client._api_request("test/endpoint")

        self.assertEqual(result, {"data": "test"})
        mock_response.raise_for_status.assert_called_once()

    @patch("integrations.clients.hud_income_limits.client.requests.get")
    def test_401_authentication_error(self, mock_get):
        """Test 401 authentication error handling."""
        import requests

        mock_response = Mock()
        mock_response.status_code = 401
        http_error = requests.exceptions.HTTPError("401 Unauthorized")
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_get.return_value = mock_response

        client = HudIncomeClient(api_token="invalid_token")

        with self.assertRaises(HudIncomeClientError) as context:
            client._api_request("test/endpoint")

        self.assertIn("Authentication failed", str(context.exception))

    @patch("integrations.clients.hud_income_limits.client.requests.get")
    def test_403_access_denied_error(self, mock_get):
        """Test 403 access denied error handling."""
        import requests

        mock_response = Mock()
        mock_response.status_code = 403
        http_error = requests.exceptions.HTTPError("403 Forbidden")
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_get.return_value = mock_response

        client = HudIncomeClient(api_token="test_token")

        with self.assertRaises(HudIncomeClientError) as context:
            client._api_request("test/endpoint")

        self.assertIn("Access denied", str(context.exception))
        self.assertIn("FMR and Income Limits", str(context.exception))

    @patch("integrations.clients.hud_income_limits.client.requests.get")
    def test_404_data_not_found_error(self, mock_get):
        """Test 404 data not found error handling."""
        import requests

        mock_response = Mock()
        mock_response.status_code = 404
        http_error = requests.exceptions.HTTPError("404 Not Found")
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_get.return_value = mock_response

        client = HudIncomeClient(api_token="test_token")

        with self.assertRaises(HudIncomeClientError) as context:
            client._api_request("test/endpoint")

        self.assertIn("Data not found", str(context.exception))

    @patch("integrations.clients.hud_income_limits.client.requests.get")
    def test_500_server_error(self, mock_get):
        """Test 500 server error handling."""
        import requests

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        http_error = requests.exceptions.HTTPError("500 Server Error")
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_get.return_value = mock_response

        client = HudIncomeClient(api_token="test_token")

        with self.assertRaises(HudIncomeClientError) as context:
            client._api_request("test/endpoint")

        self.assertIn("API request failed (500)", str(context.exception))
        self.assertIn("Internal Server Error", str(context.exception))

    @patch("integrations.clients.hud_income_limits.client.requests.get")
    def test_network_error_handling(self, mock_get):
        """Test network error handling."""
        import requests

        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        client = HudIncomeClient(api_token="test_token")

        with self.assertRaises(HudIncomeClientError) as context:
            client._api_request("test/endpoint")

        self.assertIn("Request failed", str(context.exception))


class TestAmiPercentTypes(TestCase):
    """Test AMI percentage type aliases."""

    def test_mtsp_ami_percent_accepts_valid_values(self):
        """Test that valid MTSP percentage strings are accepted."""
        valid_percents: list[MtspAmiPercent] = ["20%", "30%", "40%", "50%", "60%", "70%", "80%", "100%"]

        # Type checker will validate at static analysis time
        # This test documents the valid values
        self.assertEqual(len(valid_percents), 8)

    def test_section8_ami_percent_accepts_valid_values(self):
        """Test that valid Section 8 percentage strings are accepted."""
        valid_percents: list[Section8AmiPercent] = ["30%", "50%", "80%"]

        # Type checker will validate at static analysis time
        # This test documents the valid values
        self.assertEqual(len(valid_percents), 3)

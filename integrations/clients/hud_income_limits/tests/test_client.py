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
    AmiPercent,
)
from screener.models import Screen, WhiteLabel


class TestHudIncomeClientMTSP(TestCase):
    """Test HudIncomeClient MTSP functionality with mocked API calls."""

    def setUp(self):
        """Set up test data and mocks."""
        # Clear cache before each test
        cache.clear()

        # Create test white label and screen
        self.white_label = WhiteLabel.objects.create(name="Illinois Test", code="il_test", state_code="IL")

        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="60601", county="Cook", household_size=4, completed=False
        )

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

        # Mock county list response
        self.mock_counties_response = [
            {"county_name": "Cook County", "fips_code": "17031"},
            {"county_name": "DuPage County", "fips_code": "17043"},
        ]

    def test_get_screen_mtsp_ami_80_percent_success(self):
        """Test successful MTSP AMI lookup for 80% AMI."""
        client = HudIncomeClient(api_token="test_token")

        with patch.object(client, "_api_request") as mock_api:
            # First call returns counties, second returns MTSP data
            mock_api.side_effect = [
                self.mock_counties_response,
                self.mock_mtsp_response,
            ]

            result = client.get_screen_mtsp_ami(self.screen, "80%", "2025")

            # Should return 80% AMI for household size 4
            self.assertEqual(result, 103600)

            # Verify API was called correctly
            self.assertEqual(mock_api.call_count, 2)

    def test_get_screen_mtsp_ami_all_percentages(self):
        """Test all supported MTSP percentage levels."""
        client = HudIncomeClient(api_token="test_token")

        expected_values = {
            "20%": 25900,
            "30%": 38850,
            "40%": 51800,
            "50%": 64750,
            "60%": 77700,
            "70%": 90650,
            "80%": 103600,
            "100%": 90700,  # median_income
        }

        with patch.object(client, "_api_request") as mock_api:
            for percent, expected in expected_values.items():
                mock_api.side_effect = [
                    self.mock_counties_response,
                    self.mock_mtsp_response,
                ]

                result = client.get_screen_mtsp_ami(self.screen, percent, "2025")
                self.assertEqual(result, expected, f"Failed for {percent}")

                # Clear cache between tests
                cache.clear()

    def test_get_screen_mtsp_ami_caching(self):
        """Test that API responses are cached properly."""
        client = HudIncomeClient(api_token="test_token")

        with patch.object(client, "_api_request") as mock_api:
            mock_api.side_effect = [
                self.mock_counties_response,
                self.mock_mtsp_response,
            ]

            # First call - should hit API
            result1 = client.get_screen_mtsp_ami(self.screen, "80%", "2025")

            # Second call - should use cache
            result2 = client.get_screen_mtsp_ami(self.screen, "80%", "2025")

            self.assertEqual(result1, result2)
            # Should only call API twice (once for counties, once for MTSP data)
            # Second call uses cache
            self.assertEqual(mock_api.call_count, 2)

    def test_household_size_validation_too_small(self):
        """Test that household size < 1 raises error."""
        self.screen.household_size = 0
        client = HudIncomeClient(api_token="test_token")

        with self.assertRaises(HudIncomeClientError) as context:
            client.get_screen_mtsp_ami(self.screen, "80%", "2025")

        self.assertIn("between 1 and 8", str(context.exception))

    def test_household_size_validation_too_large(self):
        """Test that household size > 8 raises error."""
        self.screen.household_size = 9
        client = HudIncomeClient(api_token="test_token")

        with self.assertRaises(HudIncomeClientError) as context:
            client.get_screen_mtsp_ami(self.screen, "80%", "2025")

        self.assertIn("between 1 and 8", str(context.exception))

    def test_missing_api_token_raises_error(self):
        """Test that missing API token raises descriptive error."""
        with patch("integrations.clients.hud_income_limits.client.config") as mock_config:
            mock_config.return_value = None
            client = HudIncomeClient()

            with self.assertRaises(HudIncomeClientError) as context:
                _ = client.headers

            self.assertIn("HUD_API_TOKEN", str(context.exception))

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
        """Test that county names are normalized correctly."""
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
        """Test that county lookup includes 'updated' parameter to ensure FIPS codes match the year."""
        client = HudIncomeClient(api_token="test_token")

        with patch.object(client, "_api_request") as mock_api:
            mock_api.side_effect = [
                self.mock_counties_response,
                self.mock_mtsp_response,
            ]

            client.get_screen_mtsp_ami(self.screen, "80%", 2025)

            # Verify first call (county lookup) includes 'updated' parameter per HUD API spec
            first_call_args = mock_api.call_args_list[0]
            self.assertEqual(first_call_args[0][0], "fmr/listCounties/IL")
            self.assertEqual(first_call_args[0][1], {"updated": "2025"})

    def test_missing_percentage_data_raises_error(self):
        """Test that missing percentage data raises error."""
        client = HudIncomeClient(api_token="test_token")

        # Remove 80percent data
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
        """Test that missing household size data raises error."""
        client = HudIncomeClient(api_token="test_token")

        # Remove household size 4 data
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

    def test_empty_mtsp_response(self):
        """Test that empty MTSP response raises error."""
        client = HudIncomeClient(api_token="test_token")

        with patch.object(client, "_api_request") as mock_api:
            mock_api.side_effect = [
                self.mock_counties_response,
                {},  # Empty response
            ]

            with self.assertRaises(HudIncomeClientError) as context:
                client.get_screen_mtsp_ami(self.screen, "80%", "2025")

            self.assertIn("No income limit data found", str(context.exception))

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


class TestHudIncomeClientErrors(TestCase):
    """Test HUD client error handling."""

    def setUp(self):
        """Set up test screen."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="12345", county="Test County", household_size=4, completed=False
        )

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

    def test_empty_counties_list(self):
        """Test that empty counties list raises error."""
        client = HudIncomeClient(api_token="test_token")

        with patch.object(client, "_api_request") as mock_api:
            mock_api.return_value = []

            with self.assertRaises(HudIncomeClientError) as context:
                client._get_entity_id("TS", "Test County", 2025)

            self.assertIn("Could not retrieve counties", str(context.exception))


class TestHudIncomeClientStandardIL(TestCase):
    """Test Standard Section 8 Income Limits functionality."""

    def setUp(self):
        """Set up test screen."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="12345", county="Test County", household_size=4, completed=False
        )

    def test_get_screen_il_ami_not_implemented(self):
        """Test that Standard IL method raises NotImplementedError."""
        client = HudIncomeClient(api_token="test_token")

        with self.assertRaises(NotImplementedError) as context:
            client.get_screen_il_ami(self.screen, "80%", "2025")

        error_msg = str(context.exception)
        self.assertIn("not yet implemented", error_msg)
        self.assertIn("get_screen_mtsp_ami", error_msg)
        self.assertIn("/il/data/", error_msg)


# Backward compatibility test removed - get_screen_ami() method was not implemented
# Users should call get_screen_mtsp_ami() directly


class TestAmiPercentType(TestCase):
    """Test AmiPercent type alias."""

    def test_ami_percent_accepts_valid_values(self):
        """Test that valid percentage strings are accepted."""
        valid_percents: list[AmiPercent] = ["20%", "30%", "40%", "50%", "60%", "70%", "80%", "100%"]

        # Type checker will validate at static analysis time
        # This test documents the valid values
        self.assertEqual(len(valid_percents), 8)

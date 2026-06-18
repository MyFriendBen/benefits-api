"""
Unit tests for the Google Places Autocomplete proxy:
  - GooglePlacesClient.autocomplete_address
  - PlacesAutocompleteView (empty input / 502 / happy-path)
"""

import requests
from unittest.mock import patch, Mock

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from integrations.clients.google_places import GooglePlacesClient


class TestGooglePlacesClient(TestCase):
    """Unit tests for GooglePlacesClient.autocomplete_address."""

    MOCK_GOOGLE_RESPONSE = {
        "predictions": [
            {"description": "123 Main St, Denver, CO 80014, USA", "place_id": "abc123"},
            {"description": "123 Main Ave, Boulder, CO 80302, USA", "place_id": "def456"},
        ],
        "status": "OK",
    }

    @patch("integrations.clients.google_places.requests.get")
    def test_returns_parsed_predictions(self, mock_get):
        mock_get.return_value = Mock(json=lambda: self.MOCK_GOOGLE_RESPONSE)
        mock_get.return_value.raise_for_status = Mock()

        client = GooglePlacesClient()
        results = client.autocomplete_address("123 Main")

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["place_id"], "abc123")

    @patch("integrations.clients.google_places.requests.get")
    def test_strips_usa_suffix_from_descriptions(self, mock_get):
        mock_get.return_value = Mock(json=lambda: self.MOCK_GOOGLE_RESPONSE)
        mock_get.return_value.raise_for_status = Mock()

        results = GooglePlacesClient().autocomplete_address("123 Main")

        self.assertEqual(results[0]["description"], "123 Main St, Denver, CO 80014")
        self.assertEqual(results[1]["description"], "123 Main Ave, Boulder, CO 80302")

    @patch("integrations.clients.google_places.requests.get")
    def test_passes_correct_params_to_google(self, mock_get):
        mock_get.return_value = Mock(json=lambda: {"predictions": []})
        mock_get.return_value.raise_for_status = Mock()

        GooglePlacesClient().autocomplete_address("456 Oak")

        _, kwargs = mock_get.call_args
        params = kwargs["params"]
        self.assertEqual(params["input"], "456 Oak")
        self.assertEqual(params["types"], "address")
        self.assertEqual(params["components"], "country:us")

    @patch("integrations.clients.google_places.requests.get")
    def test_returns_empty_list_when_no_predictions(self, mock_get):
        mock_get.return_value = Mock(json=lambda: {"predictions": [], "status": "ZERO_RESULTS"})
        mock_get.return_value.raise_for_status = Mock()

        results = GooglePlacesClient().autocomplete_address("zzz")

        self.assertEqual(results, [])

    @patch("integrations.clients.google_places.requests.get")
    def test_preserves_non_usa_descriptions_unchanged(self, mock_get):
        mock_get.return_value = Mock(
            json=lambda: {
                "predictions": [{"description": "123 Main St, Denver, CO 80014", "place_id": "xyz"}]
            }
        )
        mock_get.return_value.raise_for_status = Mock()

        results = GooglePlacesClient().autocomplete_address("123 Main")

        self.assertEqual(results[0]["description"], "123 Main St, Denver, CO 80014")


class TestPlacesAutocompleteView(APITestCase):
    """Integration tests for GET /api/places/autocomplete/."""

    URL = "/api/places/autocomplete/"

    MOCK_PREDICTIONS = [
        {"description": "123 Main St, Denver, CO 80014", "place_id": "abc123"},
        {"description": "123 Main Ave, Boulder, CO 80302", "place_id": "def456"},
    ]

    def setUp(self):
        patcher = patch("screener.views.PlacesRateThrottle.allow_request", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    # ── empty / missing input ─────────────────────────────────────────────────

    def test_returns_empty_list_when_input_param_is_missing(self):
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_returns_empty_list_when_input_is_blank(self):
        response = self.client.get(self.URL, {"input": "   "})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    # ── 502: upstream errors ──────────────────────────────────────────────────

    @patch("screener.views.GooglePlacesClient.autocomplete_address")
    def test_google_http_error_returns_502(self, mock_autocomplete):
        err = requests.HTTPError()
        err.response = Mock(status_code=403)
        mock_autocomplete.side_effect = err
        response = self.client.get(self.URL, {"input": "123 Main"})
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn("error", response.data)

    @patch("screener.views.GooglePlacesClient.autocomplete_address")
    def test_network_failure_returns_502(self, mock_autocomplete):
        mock_autocomplete.side_effect = requests.RequestException("timeout")
        response = self.client.get(self.URL, {"input": "123 Main"})
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn("error", response.data)
        self.assertIn("detail", response.data)

    # ── 200: happy path ───────────────────────────────────────────────────────

    @patch("screener.views.GooglePlacesClient.autocomplete_address")
    def test_happy_path_returns_predictions(self, mock_autocomplete):
        mock_autocomplete.return_value = self.MOCK_PREDICTIONS
        response = self.client.get(self.URL, {"input": "123 Main"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]["description"], "123 Main St, Denver, CO 80014")
        self.assertEqual(response.data[0]["place_id"], "abc123")

    @patch("screener.views.GooglePlacesClient.autocomplete_address")
    def test_input_is_trimmed_before_forwarding(self, mock_autocomplete):
        mock_autocomplete.return_value = []
        self.client.get(self.URL, {"input": "  123 Main  "})
        mock_autocomplete.assert_called_once_with("123 Main")

    @patch("screener.views.GooglePlacesClient.autocomplete_address")
    def test_returns_empty_list_when_no_predictions(self, mock_autocomplete):
        mock_autocomplete.return_value = []
        response = self.client.get(self.URL, {"input": "zzz"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

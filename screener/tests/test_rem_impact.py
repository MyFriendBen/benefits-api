"""
Unit tests for CESN Calculate Impact utilities:
  - _convert_emissions_to_lbs helper
  - RemImpactSerializer
  - RemImpactView (400 / 502 / happy-path)
"""

import requests
from unittest.mock import patch, Mock

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from screener.serializers import KG_TO_LBS, RemImpactSerializer, _convert_emissions_to_lbs


class TestConvertEmissionsToLbs(TestCase):
    """Tests for _convert_emissions_to_lbs."""

    def test_converts_values_from_kg_to_lbs(self) -> None:
        emissions = {
            "median": {"value": -731.2272, "unit": "kgCO2e"},
        }
        result = _convert_emissions_to_lbs(emissions)
        self.assertAlmostEqual(result["median"]["value"], -731.2272 * KG_TO_LBS, places=4)

    def test_updates_unit_to_lbco2e(self) -> None:
        emissions = {
            "median": {"value": -731.2272, "unit": "kgCO2e"},
        }
        result = _convert_emissions_to_lbs(emissions)
        self.assertEqual(result["median"]["unit"], "lbCO2e")

    def test_converts_all_stat_keys(self) -> None:
        emissions = {
            "mean": {"value": -797.9434, "unit": "kgCO2e"},
            "median": {"value": -731.2272, "unit": "kgCO2e"},
            "percentile_20": {"value": -1160.2125, "unit": "kgCO2e"},
            "percentile_80": {"value": -430.9163, "unit": "kgCO2e"},
        }
        result = _convert_emissions_to_lbs(emissions)
        self.assertAlmostEqual(result["mean"]["value"], -797.9434 * KG_TO_LBS, places=4)
        self.assertAlmostEqual(result["median"]["value"], -731.2272 * KG_TO_LBS, places=4)
        self.assertAlmostEqual(result["percentile_20"]["value"], -1160.2125 * KG_TO_LBS, places=4)
        self.assertAlmostEqual(result["percentile_80"]["value"], -430.9163 * KG_TO_LBS, places=4)
        for key in result:
            self.assertEqual(result[key]["unit"], "lbCO2e")

    def test_zero_value(self) -> None:
        emissions = {"median": {"value": 0.0, "unit": "kgCO2e"}}
        result = _convert_emissions_to_lbs(emissions)
        self.assertAlmostEqual(result["median"]["value"], 0.0)
        self.assertEqual(result["median"]["unit"], "lbCO2e")

    def test_missing_value_key_defaults_to_zero(self) -> None:
        result = _convert_emissions_to_lbs({"median": {"unit": "kgCO2e"}})
        self.assertAlmostEqual(result["median"]["value"], 0.0)
        self.assertEqual(result["median"]["unit"], "lbCO2e")

    def test_null_value_defaults_to_zero(self) -> None:
        result = _convert_emissions_to_lbs({"median": {"value": None, "unit": "kgCO2e"}})
        self.assertAlmostEqual(result["median"]["value"], 0.0)

    def test_empty_dict_returns_empty_dict(self) -> None:
        self.assertEqual(_convert_emissions_to_lbs({}), {})

    def test_does_not_mutate_input(self) -> None:
        emissions = {"median": {"value": -731.2272, "unit": "kgCO2e"}}
        _convert_emissions_to_lbs(emissions)
        self.assertEqual(emissions["median"]["unit"], "kgCO2e")


class TestRemImpactSerializer(TestCase):
    """Tests for RemImpactSerializer."""

    def _make_raw_response(self, cost: dict, emissions: dict) -> dict:
        """Build a minimal RA API response dict with the given total delta values."""
        return {
            "fuel_results": {
                "total": {
                    "delta": {
                        "cost": cost,
                        "emissions": emissions,
                        "energy": {},
                    }
                }
            },
            "rates": {},
            "emissions_factors": {},
            "sampling_details": {},
            "estimate_type": {},
        }

    def test_bill_delta_passed_through_unchanged(self) -> None:
        cost = {
            "median": {"value": -21.9063, "unit": "$"},
            "percentile_20": {"value": -60.5161, "unit": "$"},
        }
        raw = self._make_raw_response(cost=cost, emissions={"median": {"value": 0.0, "unit": "kgCO2e"}})
        data = RemImpactSerializer(raw).data
        self.assertEqual(data["bill_delta"]["median"]["value"], -21.9063)
        self.assertEqual(data["bill_delta"]["median"]["unit"], "$")

    def test_emissions_delta_converted_to_lbs(self) -> None:
        emissions = {"median": {"value": -731.2272, "unit": "kgCO2e"}}
        raw = self._make_raw_response(cost={}, emissions=emissions)
        data = RemImpactSerializer(raw).data
        self.assertAlmostEqual(data["emissions_delta"]["median"]["value"], -731.2272 * KG_TO_LBS, places=4)
        self.assertEqual(data["emissions_delta"]["median"]["unit"], "lbCO2e")

    def test_other_fuel_results_stripped_from_output(self) -> None:
        raw = self._make_raw_response(cost={}, emissions={})
        raw["fuel_results"]["electricity"] = {"delta": {"cost": {"median": {"value": -999}}}}
        data = RemImpactSerializer(raw).data
        self.assertNotIn("electricity", data)
        self.assertNotIn("fuel_results", data)

    def test_missing_fuel_results_returns_empty_dicts(self) -> None:
        data = RemImpactSerializer({}).data
        self.assertEqual(data["bill_delta"], {})
        self.assertEqual(data["emissions_delta"], {})


class TestRemImpactView(APITestCase):
    """Integration tests for GET /api/screener-options/<white_label>/rem-impact/."""

    URL = "/api/screener-options/cesn/rem-impact/"

    VALID_PARAMS = {
        "upgrade": "water_heater__heat_pump_uef3.35",
        "address": "200 E Colfax Ave Denver, CO 80203",
        "heating_fuel": "natural_gas",
        "water_heater_fuel": "natural_gas",
    }

    # Minimal raw RA response; serializer transformation is tested separately.
    MOCK_RAW_RESPONSE = {
        "fuel_results": {
            "total": {
                "delta": {
                    "cost": {"median": {"value": -21.91, "unit": "$"}},
                    "emissions": {"median": {"value": -731.23, "unit": "kgCO2e"}},
                    "energy": {},
                }
            }
        },
        "rates": {},
        "emissions_factors": {},
        "sampling_details": {},
        "estimate_type": {},
    }

    def setUp(self) -> None:
        # Disable the REM rate throttle so individual tests are not throttled.
        patcher = patch("screener.views.RemRateThrottle.allow_request", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    # ── 400: missing required params ──────────────────────────────────────────

    def test_returns_400_when_upgrade_missing(self) -> None:
        params = {k: v for k, v in self.VALID_PARAMS.items() if k != "upgrade"}
        response = self.client.get(self.URL, params)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_returns_400_when_address_missing(self) -> None:
        params = {k: v for k, v in self.VALID_PARAMS.items() if k != "address"}
        response = self.client.get(self.URL, params)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_returns_400_when_heating_fuel_missing(self) -> None:
        params = {k: v for k, v in self.VALID_PARAMS.items() if k != "heating_fuel"}
        response = self.client.get(self.URL, params)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ── 502: upstream errors ──────────────────────────────────────────────────

    @patch("screener.views.RewiringAmericaClient.fetch_rem_impact")
    def test_upstream_http_error_returns_502(self, mock_fetch) -> None:
        err = requests.HTTPError()
        err.response = Mock(status_code=400, json=lambda: {"msg": "bad"})
        mock_fetch.side_effect = err
        response = self.client.get(self.URL, self.VALID_PARAMS)
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn("error", response.data)
        self.assertIn("detail", response.data)

    @patch("screener.views.RewiringAmericaClient.fetch_rem_impact")
    def test_upstream_http_error_with_non_json_body_falls_back_to_text(self, mock_fetch) -> None:
        err = requests.HTTPError()
        err.response = Mock(
            status_code=500,
            json=Mock(side_effect=ValueError("not json")),
            text="Internal Server Error",
        )
        mock_fetch.side_effect = err
        response = self.client.get(self.URL, self.VALID_PARAMS)
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(response.data["detail"], "Internal Server Error")

    @patch("screener.views.RewiringAmericaClient.fetch_rem_impact")
    def test_network_failure_returns_502(self, mock_fetch) -> None:
        mock_fetch.side_effect = requests.RequestException("connection refused")
        response = self.client.get(self.URL, self.VALID_PARAMS)
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn("error", response.data)

    # ── 422: address-level errors ─────────────────────────────────────────────

    @patch("screener.views.RewiringAmericaClient.fetch_rem_impact")
    def test_rem_400_with_known_address_error_type_returns_422(self, mock_fetch):
        for error_type in (
            "multifamily_not_supported",
            "building_type_not_supported",
            "address_not_parsable",
            "building_not_supported",
        ):
            with self.subTest(error_type=error_type):
                err = requests.HTTPError()
                # REM wraps the typed error one level deep: {"detail": {"type": ..., "msg": ...}}
                err.response = Mock(
                    status_code=400,
                    json=lambda t=error_type: {"detail": {"type": t, "msg": "some message"}},
                )
                mock_fetch.side_effect = err
                response = self.client.get(self.URL, self.VALID_PARAMS)
                self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
                self.assertEqual(response.data["error"], "address_not_supported")
                self.assertIn("detail", response.data)

    @patch("screener.views.RewiringAmericaClient.fetch_rem_impact")
    def test_rem_400_with_unknown_error_type_still_returns_502(self, mock_fetch):
        err = requests.HTTPError()
        err.response = Mock(status_code=400, json=lambda: {"detail": {"type": "some_future_type", "msg": "x"}})
        mock_fetch.side_effect = err
        response = self.client.get(self.URL, self.VALID_PARAMS)
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)

    # ── 200: happy path ───────────────────────────────────────────────────────

    @patch("screener.views.RewiringAmericaClient.fetch_rem_impact")
    def test_happy_path_returns_bill_and_emissions_delta(self, mock_fetch) -> None:
        mock_fetch.return_value = self.MOCK_RAW_RESPONSE
        response = self.client.get(self.URL, self.VALID_PARAMS)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("bill_delta", response.data)
        self.assertIn("emissions_delta", response.data)

    @patch("screener.views.RewiringAmericaClient.fetch_rem_impact")
    def test_water_heater_fuel_is_optional(self, mock_fetch) -> None:
        mock_fetch.return_value = self.MOCK_RAW_RESPONSE
        params = {k: v for k, v in self.VALID_PARAMS.items() if k != "water_heater_fuel"}
        response = self.client.get(self.URL, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # water_heater_fuel absent from params → client receives None
        call_kwargs = mock_fetch.call_args
        passed_water_heater_fuel = (
            call_kwargs.kwargs.get("water_heater_fuel")
            if call_kwargs.kwargs
            else call_kwargs.args[3] if len(call_kwargs.args) > 3 else None
        )
        self.assertIsNone(passed_water_heater_fuel)

    @patch("screener.views.RewiringAmericaClient.fetch_rem_impact")
    def test_emissions_converted_to_lbs_in_response(self, mock_fetch) -> None:
        mock_fetch.return_value = self.MOCK_RAW_RESPONSE
        response = self.client.get(self.URL, self.VALID_PARAMS)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["emissions_delta"]["median"]["unit"], "lbCO2e")

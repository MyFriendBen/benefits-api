"""
Unit tests for CESN Calculate Impact utilities: the kgCO2e → lbCO2e conversion
function and the RemImpactSerializer that applies it.
"""

from django.test import TestCase
from screener.serializers import RemImpactSerializer, _convert_emissions_to_lbs

_KG_TO_LBS = 2.20462


class TestConvertEmissionsToLbs(TestCase):
    """Tests for _convert_emissions_to_lbs."""

    def test_converts_values_from_kg_to_lbs(self):
        emissions = {
            "median": {"value": -731.2272, "unit": "kgCO2e"},
        }
        result = _convert_emissions_to_lbs(emissions)
        self.assertAlmostEqual(result["median"]["value"], -731.2272 * _KG_TO_LBS, places=4)

    def test_updates_unit_to_lbco2e(self):
        emissions = {
            "median": {"value": -731.2272, "unit": "kgCO2e"},
        }
        result = _convert_emissions_to_lbs(emissions)
        self.assertEqual(result["median"]["unit"], "lbCO2e")

    def test_converts_all_stat_keys(self):
        emissions = {
            "mean": {"value": -797.9434, "unit": "kgCO2e"},
            "median": {"value": -731.2272, "unit": "kgCO2e"},
            "percentile_20": {"value": -1160.2125, "unit": "kgCO2e"},
            "percentile_80": {"value": -430.9163, "unit": "kgCO2e"},
        }
        result = _convert_emissions_to_lbs(emissions)
        self.assertAlmostEqual(result["mean"]["value"], -797.9434 * _KG_TO_LBS, places=4)
        self.assertAlmostEqual(result["median"]["value"], -731.2272 * _KG_TO_LBS, places=4)
        self.assertAlmostEqual(result["percentile_20"]["value"], -1160.2125 * _KG_TO_LBS, places=4)
        self.assertAlmostEqual(result["percentile_80"]["value"], -430.9163 * _KG_TO_LBS, places=4)
        for key in result:
            self.assertEqual(result[key]["unit"], "lbCO2e")

    def test_zero_value(self):
        emissions = {"median": {"value": 0.0, "unit": "kgCO2e"}}
        result = _convert_emissions_to_lbs(emissions)
        self.assertAlmostEqual(result["median"]["value"], 0.0)
        self.assertEqual(result["median"]["unit"], "lbCO2e")

    def test_empty_dict_returns_empty_dict(self):
        self.assertEqual(_convert_emissions_to_lbs({}), {})

    def test_does_not_mutate_input(self):
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

    def test_bill_delta_passed_through_unchanged(self):
        cost = {
            "median": {"value": -21.9063, "unit": "$"},
            "percentile_20": {"value": -60.5161, "unit": "$"},
        }
        raw = self._make_raw_response(cost=cost, emissions={"median": {"value": 0.0, "unit": "kgCO2e"}})
        data = RemImpactSerializer(raw).data
        self.assertEqual(data["bill_delta"]["median"]["value"], -21.9063)
        self.assertEqual(data["bill_delta"]["median"]["unit"], "$")

    def test_emissions_delta_converted_to_lbs(self):
        emissions = {"median": {"value": -731.2272, "unit": "kgCO2e"}}
        raw = self._make_raw_response(cost={}, emissions=emissions)
        data = RemImpactSerializer(raw).data
        self.assertAlmostEqual(data["emissions_delta"]["median"]["value"], -731.2272 * _KG_TO_LBS, places=4)
        self.assertEqual(data["emissions_delta"]["median"]["unit"], "lbCO2e")

    def test_other_fuel_results_stripped_from_output(self):
        raw = self._make_raw_response(cost={}, emissions={})
        raw["fuel_results"]["electricity"] = {"delta": {"cost": {"median": {"value": -999}}}}
        data = RemImpactSerializer(raw).data
        self.assertNotIn("electricity", data)
        self.assertNotIn("fuel_results", data)

    def test_missing_fuel_results_returns_empty_dicts(self):
        data = RemImpactSerializer({}).data
        self.assertEqual(data["bill_delta"], {})
        self.assertEqual(data["emissions_delta"], {})

"""Unit tests for PolicyEngineClient (programs/programs/policyengine/client.py).

Uses a stub Sim -- no network, no Docker required. See test_integration.py
for tests against a real, recorded PolicyEngine response.
"""

from unittest.mock import patch
from django.test import SimpleTestCase

from programs.programs.policyengine.client import PolicyEngineClient
from programs.programs.policyengine.engines import ApiSim


class StubSim:
    """Minimal Sim double: records every .value() call and returns canned values."""

    def __init__(self, data=None):
        self.data = data or {}
        self.calls = []

    def value(self, unit, sub_unit, variable, period):
        self.calls.append((unit, sub_unit, variable, period))
        return self.data[(unit, sub_unit, variable, period)]

    def members(self, unit, sub_unit):
        raise NotImplementedError


class TestGetMemberValue(SimpleTestCase):
    def test_reads_people_category_uncast(self):
        sim = StubSim({("people", "1", "medicaid_category", "2024"): "ADULT"})
        client = PolicyEngineClient(sim, "2024")

        self.assertEqual(client.get_member_value(1, "medicaid_category"), "ADULT")
        self.assertEqual(sim.calls, [("people", "1", "medicaid_category", "2024")])

    def test_does_not_cast_numeric_strings_that_are_not_currency(self):
        # e.g. a FIPS county code -- would silently corrupt if cast to int.
        sim = StubSim({("people", "1", "county_fips", "2024"): "08031"})
        client = PolicyEngineClient(sim, "2024")

        self.assertEqual(client.get_member_value(1, "county_fips"), "08031")


class TestGetSpmValue(SimpleTestCase):
    def test_casts_to_int_truncating(self):
        sim = StubSim({("spm_units", "spm_unit", "snap", "2024"): 279.59998})
        client = PolicyEngineClient(sim, "2024")

        self.assertEqual(client.get_spm_value("snap"), 279)
        self.assertEqual(sim.calls, [("spm_units", "spm_unit", "snap", "2024")])

    def test_period_override_reads_at_the_given_period_not_self_period(self):
        # SNAP's real value lives at the monthly pe_output_period ("2024-01"),
        # not the annual self.period ("2024") -- see DECISIONS.md D-013.
        sim = StubSim({("spm_units", "spm_unit", "snap", "2024-01"): 279.59998})
        client = PolicyEngineClient(sim, "2024")

        self.assertEqual(client.get_spm_value("snap", period="2024-01"), 279)
        self.assertEqual(sim.calls, [("spm_units", "spm_unit", "snap", "2024-01")])

    def test_no_period_override_still_defaults_to_self_period(self):
        sim = StubSim({("spm_units", "spm_unit", "snap", "2024"): 279.59998})
        client = PolicyEngineClient(sim, "2024")

        self.assertEqual(client.get_spm_value("snap", period=None), 279)
        self.assertEqual(sim.calls, [("spm_units", "spm_unit", "snap", "2024")])


class TestGetHouseholdValue(SimpleTestCase):
    def test_reads_arbitrary_category_uncast(self):
        sim = StubSim({("households", "your household", "state_name", "2024"): "CO"})
        client = PolicyEngineClient(sim, "2024")

        self.assertEqual(client.get_household_value("households", "your household", "state_name"), "CO")
        self.assertEqual(sim.calls, [("households", "your household", "state_name", "2024")])

    def test_reads_tax_unit_category(self):
        sim = StubSim({("tax_units", "your tax unit", "eitc", "2024"): 1500.4})
        client = PolicyEngineClient(sim, "2024")

        # Uncast on purpose (see DECISIONS.md D-009) -- caller casts if it needs to.
        self.assertEqual(client.get_household_value("tax_units", "your tax unit", "eitc"), 1500.4)


class TestWrappingExistingSimDoesNotTriggerASecondApiCall(SimpleTestCase):
    """RFC 0003's own open question: does the client cause a second live PE call?"""

    def test_constructing_the_client_makes_no_http_call(self):
        with patch("requests.post") as mock_post:
            sim = StubSim({("spm_units", "spm_unit", "snap", "2024"): 100})
            PolicyEngineClient(sim, "2024")

            mock_post.assert_not_called()

    def test_multiple_getter_calls_reuse_the_same_sim_construction(self):
        # ApiSim.__init__ is where the one real HTTP call happens (engines.py:43).
        # Construct exactly one ApiSim, then call every client getter several times --
        # the mocked requests.post call count must stay at 1 throughout.
        with patch("requests.post") as mock_post:
            mock_post.return_value.raise_for_status.return_value = None
            mock_post.return_value.json.return_value = {
                "result": {
                    "people": {"1": {"age": {"2024": 30}}},
                    "spm_units": {"spm_unit": {"snap": {"2024": 279.6}}},
                    "households": {"your household": {"state_name": {"2024": "CO"}}},
                }
            }

            sim = ApiSim({"household": {}})
            self.assertEqual(mock_post.call_count, 1)

            client = PolicyEngineClient(sim, "2024")
            for _ in range(3):
                client.get_member_value(1, "age")
                client.get_spm_value("snap")
                client.get_household_value("households", "your household", "state_name")

            self.assertEqual(mock_post.call_count, 1)

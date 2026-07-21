"""Integration tests for PolicyEngineClient against a real, recorded PolicyEngine
response (per RFC 0008: "Use vcrpy fixtures for PolicyEngine calls").

Follows the repo's existing VCR convention exactly (see
integrations/clients/hud_income_limits/tests/test_integration.py and the
auto_vcr fixture in the root conftest.py). Cassettes live in
tests/cassettes/<test_name>.yaml, generated once against the local
self-hosted PolicyEngine Docker container (see RISKS.md/DECISIONS.md D-003 --
never the real hosted API), then replayed with zero live dependency.

Run: pytest -m integration programs/programs/policyengine/tests/test_integration.py
"""

import pytest
from django.test import SimpleTestCase

from programs.programs.policyengine.client import PolicyEngineClient
from programs.programs.policyengine.engines import ApiSim

PERIOD = "2024"

HOUSEHOLD_PAYLOAD = {
    "household": {
        "people": {"you": {"age": {PERIOD: 30}, "employment_income": {PERIOD: 20000}}},
        "families": {"your family": {"members": ["you"]}},
        "spm_units": {"spm_unit": {"members": ["you"], "snap": {PERIOD: None}}},
        "tax_units": {"your tax unit": {"members": ["you"]}},
        "households": {"your household": {"members": ["you"], "state_name": {PERIOD: "CO"}}},
        "marital_units": {"your marital unit": {"members": ["you"]}},
    }
}


class DockerApiSim(ApiSim):
    """Test-only Sim pointed at the local self-hosted Docker container instead of
    PolicyEngine's real hosted API -- keeps faith with D-003 while still recording
    a genuine response. Defined here only; engines.py is not touched."""

    pe_url = "http://localhost:8080/us/calculate"


@pytest.mark.integration
class TestPolicyEngineClientAgainstRealResponse(SimpleTestCase):
    def setUp(self):
        self.sim = DockerApiSim(HOUSEHOLD_PAYLOAD)
        self.client = PolicyEngineClient(self.sim, PERIOD)

    def test_get_member_value_reads_person_level_value(self):
        self.assertEqual(self.client.get_member_value("you", "age"), 30)

    def test_get_spm_value_casts_currency_to_int(self):
        # Real recorded value is a float (e.g. 279.59998); get_spm_value truncates.
        value = self.client.get_spm_value("snap")
        self.assertIsInstance(value, int)
        self.assertGreater(value, 0)

    def test_get_household_value_reads_arbitrary_category_uncast(self):
        # state_name is a real non-numeric value on a category other than spm/people --
        # confirms the method is genuinely generic, and returns it uncast.
        self.assertEqual(self.client.get_household_value("households", "your household", "state_name"), "CO")

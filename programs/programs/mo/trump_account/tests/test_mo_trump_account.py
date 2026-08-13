"""
Wiring tests for the MO Trump Account program.

MO has no state-specific calculator: the program is `Fed (as-is)` and resolves to the
shared federal `TrumpAccount` class through the global calculator registry, keyed on
`Program.name_abbreviated`. These tests lock in that wiring plus the shape of the
MO config, since a config-only program has no eligibility scenarios of its own.
"""

import json
from pathlib import Path

from django.test import TestCase

from programs.programs import calculators
from programs.programs.federal.trump_account.calculator import TrumpAccount

CONFIG_PATH = (
    Path(__file__).resolve().parents[4]
    / "management"
    / "commands"
    / "import_program_config_data"
    / "data"
    / "mo_trump_account_initial_config.json"
)

SIBLING_STATES = ["co", "il", "ks", "ma", "nc", "tx", "wa"]


def load_config(state: str) -> dict:
    path = CONFIG_PATH.with_name(f"{state}_trump_account_initial_config.json")
    with open(path) as f:
        return json.load(f)


class TestMoTrumpAccountConfig(TestCase):
    """The MO config file is present, parseable, and correctly shaped."""

    @classmethod
    def setUpTestData(cls):
        cls.config = load_config("mo")
        cls.program = cls.config["program"]

    def test_config_file_exists(self):
        self.assertTrue(CONFIG_PATH.exists())

    def test_targets_mo_white_label(self):
        self.assertEqual(self.config["white_label"]["code"], "mo")

    def test_name_abbreviated_is_lowercase(self):
        # A CHECK constraint rejects uppercase name_abbreviated on import.
        name = self.program["name_abbreviated"]
        self.assertEqual(name, name.lower())

    def test_external_name_is_state_scoped(self):
        self.assertEqual(self.program["external_name"], "mo_trump_account")

    def test_has_calculator_is_true(self):
        self.assertTrue(self.program["has_calculator"])

    def test_value_type_is_benefit(self):
        self.assertEqual(self.program["value_type"], "benefit")

    def test_value_format_is_lump_sum(self):
        self.assertEqual(self.program["value_format"], "lump_sum")

    def test_requires_citizenship(self):
        self.assertEqual(self.program["legal_status_required"], ["citizen"])

    def test_no_year_key(self):
        # There is no income test, so the program is not tied to an FPL year.
        self.assertNotIn("year", self.program)

    def test_omits_stale_notices_warning(self):
        # The shared trump_account_notices warning text is out of date; MO does not carry it.
        self.assertNotIn("warning_message", self.config)
        self.assertNotIn("warning_messages", self.config)

    def test_declares_parent_ssn_document(self):
        externals = [d["external_name"] for d in self.config["documents"]]
        self.assertIn("trump_account_parent_ssn", externals)

    def test_documents_reuse_shared_trump_account_keys(self):
        for document in self.config["documents"]:
            self.assertTrue(document["external_name"].startswith("trump_account_"))

    def test_documents_have_text(self):
        # A document key absent from the DB is created from `text`, so it must be present.
        for document in self.config["documents"]:
            self.assertTrue(document["text"].strip())

    def test_declares_call_center_navigator(self):
        externals = [n["external_name"] for n in self.config["navigators"]]
        self.assertEqual(externals, ["trump_account_call_center"])


class TestMoTrumpAccountCalculatorWiring(TestCase):
    """The MO config resolves to the shared federal calculator."""

    def test_name_abbreviated_resolves_to_federal_calculator(self):
        name = load_config("mo")["program"]["name_abbreviated"]
        self.assertIs(calculators[name.lower()], TrumpAccount)

    def test_mo_declares_no_state_specific_override(self):
        # MO is Fed (as-is): a state subclass registered under the same key would
        # replace the federal class for every state, since the registry is global.
        from programs.programs.mo import mo_calculators

        self.assertNotIn("trump_account", mo_calculators)


class TestTrumpAccountSiblingParity(TestCase):
    """MO uses the same calculator key as the states that already shipped."""

    def test_all_states_share_one_calculator_key(self):
        keys = {state: load_config(state)["program"]["name_abbreviated"] for state in SIBLING_STATES + ["mo"]}
        self.assertEqual(set(keys.values()), {"trump_account"})

    def test_states_that_set_external_name_scope_it_by_state(self):
        # Only some sibling configs declare external_name; where present it is state-scoped.
        for state in SIBLING_STATES + ["mo"]:
            external_name = load_config(state)["program"].get("external_name")
            if external_name is not None:
                self.assertEqual(external_name, f"{state}_trump_account")

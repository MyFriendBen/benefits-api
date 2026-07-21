from django.conf import settings
from django.test import SimpleTestCase

from programs.programs.config.loader import (
    ConfigLoadError,
    UnknownDependencyClassError,
    UnsupportedPeEntityError,
    load_config_layer,
    load_config_layer_from_file,
)
from programs.programs.policyengine.calculators.dependencies.household import CoStateCodeDependency
from programs.programs.policyengine.calculators.dependencies.member import AgeDependency

EXAMPLES_DIR = settings.BASE_DIR / "schemas" / "examples"


class TestLoadConfigLayerFederal(SimpleTestCase):
    def test_federal_config_with_no_extends_resolves_additional_inputs(self):
        config = load_config_layer_from_file(EXAMPLES_DIR / "snap_federal.json")

        self.assertEqual(config.program, "snap")
        self.assertEqual(config.state, "federal")
        self.assertEqual(config.pe_name, "snap")
        self.assertEqual(config.pe_entity, "spm_unit")
        self.assertEqual(config.pe_period_month, "01")
        self.assertIn(AgeDependency, config.pe_inputs)
        self.assertEqual(len(config.pe_inputs), 22)


class TestLoadConfigLayerState(SimpleTestCase):
    def test_state_config_extends_federal_and_appends_state_dependency(self):
        config = load_config_layer_from_file(
            EXAMPLES_DIR / "co_snap_config.json",
            federal_path=EXAMPLES_DIR / "snap_federal.json",
        )

        self.assertEqual(config.state, "co")
        # base (federal, 22 entries) + own additional_inputs (0) + state_dependency (1)
        self.assertEqual(len(config.pe_inputs), 23)
        self.assertEqual(config.pe_inputs[-1], CoStateCodeDependency)

    def test_extends_without_federal_config_raises(self):
        with self.assertRaises(ConfigLoadError):
            load_config_layer_from_file(EXAMPLES_DIR / "co_snap_config.json")

    def test_federal_config_program_mismatch_raises(self):
        state_config = {
            "program": "snap",
            "state": "co",
            "pe_name": "snap",
            "pe_entity": "spm_unit",
            "state_dependency": None,
            "extends": "snap",
            "additional_inputs": [],
            "pe_period_month": None,
        }
        wrong_federal = {
            "program": "tanf",
            "state": "federal",
            "pe_name": "tanf",
            "pe_entity": "spm_unit",
            "state_dependency": None,
            "extends": None,
            "additional_inputs": [],
            "pe_period_month": None,
        }

        with self.assertRaises(ConfigLoadError):
            load_config_layer(state_config, federal_config=wrong_federal)

    def test_federal_config_with_non_null_extends_raises(self):
        state_config = {
            "program": "snap",
            "state": "co",
            "pe_name": "snap",
            "pe_entity": "spm_unit",
            "state_dependency": None,
            "extends": "snap",
            "additional_inputs": [],
            "pe_period_month": None,
        }
        two_level_federal = {
            "program": "snap",
            "state": "federal",
            "pe_name": "snap",
            "pe_entity": "spm_unit",
            "state_dependency": None,
            "extends": "something_else",
            "additional_inputs": [],
            "pe_period_month": None,
        }

        with self.assertRaises(ConfigLoadError):
            load_config_layer(state_config, federal_config=two_level_federal)


class TestLoadConfigLayerOutputs(SimpleTestCase):
    def test_pe_outputs_is_derived_from_entity_and_name(self):
        config = load_config_layer(
            {
                "program": "tanf",
                "state": "federal",
                "pe_name": "tanf",
                "pe_entity": "spm_unit",
                "state_dependency": None,
                "extends": None,
                "additional_inputs": [],
                "pe_period_month": None,
            }
        )

        self.assertEqual(len(config.pe_outputs), 1)
        output_cls = config.pe_outputs[0]
        self.assertEqual(output_cls.field, "tanf")
        self.assertEqual(output_cls.unit, "spm_units")

    def test_unknown_dependency_class_name_raises(self):
        with self.assertRaises(UnknownDependencyClassError):
            load_config_layer(
                {
                    "program": "tanf",
                    "state": "federal",
                    "pe_name": "tanf",
                    "pe_entity": "spm_unit",
                    "state_dependency": None,
                    "extends": None,
                    "additional_inputs": ["ThisClassDoesNotExist"],
                    "pe_period_month": None,
                }
            )

    def test_unsupported_pe_entity_raises(self):
        with self.assertRaises(UnsupportedPeEntityError):
            load_config_layer(
                {
                    "program": "x",
                    "state": "federal",
                    "pe_name": "x",
                    "pe_entity": "family",
                    "state_dependency": None,
                    "extends": None,
                    "additional_inputs": [],
                    "pe_period_month": None,
                }
            )

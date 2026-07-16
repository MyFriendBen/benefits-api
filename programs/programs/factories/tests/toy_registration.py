"""
Test-only registration proving CalculatorFactory + ConfigurableCalculator
slot into the real orchestration layer exactly like a real state's
pe/__init__.py would -- imported BY the tests below, not a test itself.

Deliberately fabricated program identity ("zz_toy_program"/state "zz", PE
field "zz_toy_value") -- see the plan's Context section for why this is a
different kind of artifact than the throwaway SnapCalculator D-010 ruled
out: nothing here will ever be built for real in a later phase, and it
proves orchestration coexistence, not SNAP parity.
"""

from programs.programs.config.loader import load_config_layer
from programs.programs.factories.calculator_factory import CalculatorFactory

_TOY_CONFIG_DICT = {
    "program": "zz_toy_program",
    "state": "zz",
    "pe_name": "zz_toy_value",
    "pe_entity": "spm_unit",
    "state_dependency": None,
    "extends": None,
    "additional_inputs": ["FullTimeCollegeStudentDependency"],
    "pe_period_month": None,
}

toy_config = load_config_layer(_TOY_CONFIG_DICT)

factory = CalculatorFactory()
ZzToyProgram = factory.register("zz_toy_program", toy_config)

zz_toy_calculators = factory.as_dict()  # shaped exactly like co_spm_calculators

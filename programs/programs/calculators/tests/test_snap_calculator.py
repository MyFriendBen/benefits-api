from types import SimpleNamespace

from django.test import SimpleTestCase

from programs.programs.calculators.snap import SnapCalculator
from programs.programs.config.loader import ConfigLayer
from programs.util import Dependencies


class StubSim:
    """Same convention as test_client.py's/test_configurable_calculator.py's
    StubSim -- returns from a dict keyed by (unit, sub_unit, variable, period)."""

    def __init__(self, data):
        self.data = data

    def value(self, unit, sub_unit, variable, period):
        return self.data[(unit, sub_unit, variable, period)]


def make_program(period="2024"):
    return SimpleNamespace(year=SimpleNamespace(period=period))


def make_screen():
    return SimpleNamespace(household_members=SimpleNamespace(all=lambda: []))


class TestSnapCalculatorHouseholdValue(SimpleTestCase):
    def test_reads_at_monthly_output_period_and_multiplies_by_12(self):
        # Real value from Phase 2's Docker cassette, deliberately non-integer:
        # distinguishes int(279.59998) * 12 == 3348 from int(279.59998 * 12)
        # == 3355, matching federal/pe/spm.py:42-43's real cast-then-multiply
        # order exactly (see DECISIONS.md D-013).
        config = ConfigLayer(program="snap", state="co", pe_name="snap", pe_entity="spm_unit", pe_period_month="01")
        calc = SnapCalculator(make_screen(), make_program(period="2024"), Dependencies(), config=config)
        calc.set_engine(StubSim({("spm_units", "spm_unit", "snap", "2024-01"): 279.59998}))

        self.assertEqual(calc.household_value(), 3348)

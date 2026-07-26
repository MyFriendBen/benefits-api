from types import SimpleNamespace

from django.test import SimpleTestCase

from programs.programs.calculators.base import ConfigurableCalculator
from programs.programs.config.loader import ConfigLayer
from programs.programs.policyengine.calculators.dependencies.member import AgeDependency
from programs.programs.data.loader import DataLayer, SourceInfo
from programs.util import DependencyError, Dependencies


class StubSim:
    """Same convention as programs/programs/policyengine/tests/test_client.py's
    StubSim -- records nothing, just returns from a dict keyed by
    (unit, sub_unit, variable, period)."""

    def __init__(self, data):
        self.data = data

    def value(self, unit, sub_unit, variable, period):
        return self.data[(unit, sub_unit, variable, period)]


def make_program(period="2024"):
    year = SimpleNamespace(period=period) if period is not None else None
    return SimpleNamespace(year=year)


def make_screen(member_ids):
    members = [SimpleNamespace(id=member_id) for member_id in member_ids]
    return SimpleNamespace(household_members=SimpleNamespace(all=lambda: members))


class TestPeriodProperties(SimpleTestCase):
    def test_pe_period_raises_when_program_year_is_none(self):
        config = ConfigLayer(program="p", state="s", pe_name="x", pe_entity="spm_unit", pe_period_month=None)
        calc = ConfigurableCalculator(make_screen([]), make_program(period=None), Dependencies(), config=config)

        with self.assertRaises(Exception):
            calc.pe_period

    def test_pe_output_period_raises_attribute_error_when_month_unset(self):
        config = ConfigLayer(program="p", state="s", pe_name="x", pe_entity="spm_unit", pe_period_month=None)
        calc = ConfigurableCalculator(make_screen([]), make_program(), Dependencies(), config=config)

        with self.assertRaises(AttributeError):
            calc.pe_output_period

    def test_pe_output_period_combines_period_and_month_when_set(self):
        config = ConfigLayer(program="p", state="s", pe_name="x", pe_entity="spm_unit", pe_period_month="01")
        calc = ConfigurableCalculator(make_screen([]), make_program(period="2024"), Dependencies(), config=config)

        self.assertEqual(calc.pe_output_period, "2024-01")


class TestCanCalc(SimpleTestCase):
    def test_true_when_no_dependency_is_missing(self):
        config = ConfigLayer(
            program="p", state="s", pe_name="x", pe_entity="spm_unit", pe_period_month=None, pe_inputs=[AgeDependency]
        )
        calc = ConfigurableCalculator(make_screen([]), make_program(), Dependencies(), config=config)

        self.assertTrue(calc.can_calc())

    def test_false_when_a_pe_input_dependency_is_missing(self):
        config = ConfigLayer(
            program="p", state="s", pe_name="x", pe_entity="spm_unit", pe_period_month=None, pe_inputs=[AgeDependency]
        )
        calc = ConfigurableCalculator(make_screen([]), make_program(), Dependencies({"age"}), config=config)

        self.assertFalse(calc.can_calc())

    def test_calc_raises_dependency_error_when_cannot_calc(self):
        config = ConfigLayer(
            program="p", state="s", pe_name="x", pe_entity="spm_unit", pe_period_month=None, pe_inputs=[AgeDependency]
        )
        calc = ConfigurableCalculator(make_screen([]), make_program(), Dependencies({"age"}), config=config)

        with self.assertRaises(DependencyError):
            calc.calc()


class TestSpmUnitCalc(SimpleTestCase):
    def test_household_value_reads_spm_value_via_client(self):
        config = ConfigLayer(program="p", state="s", pe_name="tanf", pe_entity="spm_unit", pe_period_month=None)
        calc = ConfigurableCalculator(make_screen([1]), make_program(period="2024"), Dependencies(), config=config)
        calc.set_engine(StubSim({("spm_units", "spm_unit", "tanf", "2024"): 150.0}))

        eligibility = calc.calc()

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.household_value, 150)


class TestPersonEntityCalc(SimpleTestCase):
    def test_member_value_reads_member_value_via_client(self):
        config = ConfigLayer(program="p", state="s", pe_name="medicaid", pe_entity="person", pe_period_month=None)
        calc = ConfigurableCalculator(make_screen([7]), make_program(period="2024"), Dependencies(), config=config)
        calc.set_engine(StubSim({("people", "7", "medicaid", "2024"): 1}))

        eligibility = calc.calc()

        self.assertTrue(eligibility.eligible)
        self.assertEqual(len(eligibility.eligible_members), 1)
        self.assertEqual(eligibility.eligible_members[0].value, 1)


class TestBenefitDataIsBoundButInert(SimpleTestCase):
    def test_benefit_data_is_stored_and_not_used_by_household_value(self):
        config = ConfigLayer(program="p", state="s", pe_name="tanf", pe_entity="spm_unit", pe_period_month=None)
        data = DataLayer(program="p", state="s", category_amounts={"ADULT": 100}, source=SourceInfo("guessed", None))
        calc = ConfigurableCalculator(
            make_screen([1]), make_program(period="2024"), Dependencies(), config=config, benefit_data=data
        )
        calc.set_engine(StubSim({("spm_units", "spm_unit", "tanf", "2024"): 150.0}))

        self.assertIs(calc.benefit_data, data)
        self.assertEqual(calc.calc().household_value, 150)

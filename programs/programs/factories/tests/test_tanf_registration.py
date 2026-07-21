"""
Real (non-fictional) check that the production tanf_federal.json
(programs/programs/config/data/tanf_federal.json), tx_tanf_config.json, and
wa_tanf_config.json load correctly through tanf_registration.py, and that
TxTanfCalculator/WaTanfCalculator produce the correct household value
end-to-end through calc() -- the TANF-side counterpart to
test_snap_registration.py's CoSnap-specific same-input/same-output
micro-check, against federal Tanf.household_value()'s real
cast-with-no-period-split math (PolicyEngineCalulator's plain
`int(self.get_variable())` default -- see D-019 for why no *12 conversion
applies here, unlike SNAP).
"""

from django.test import SimpleTestCase, TestCase

from programs.models import FederalPoveryLimit, Program
from programs.programs.factories.tanf_registration import (
    TxTanfCalculator,
    WaTanfCalculator,
    tanf_factory,
    tanf_federal_config,
    tx_tanf_config,
    wa_tanf_config,
)
from programs.programs.policyengine.calculators.dependencies.household import (
    TxStateCodeDependency,
    WaStateCodeDependency,
)
from programs.programs.policyengine.calculators.dependencies.member import (
    AgeDependency,
    FullTimeCollegeStudentDependency,
    PregnancyDependency,
)
from programs.programs.policyengine.calculators.dependencies.spm import WaShowAllCashAssistanceProgramsDependency
from programs.util import Dependencies
from screener.models import HouseholdMember, Screen, WhiteLabel


class StubSim:
    def __init__(self, data):
        self.data = data

    def value(self, unit, sub_unit, variable, period):
        return self.data[(unit, sub_unit, variable, period)]


class TestTanfFederalConfigLoadsCorrectly(SimpleTestCase):
    def test_federal_config_matches_federal_tanf_pe_inputs(self):
        self.assertEqual(tanf_federal_config.program, "tanf")
        self.assertEqual(tanf_federal_config.state, "federal")
        self.assertEqual(tanf_federal_config.pe_name, "tanf")
        self.assertEqual(tanf_federal_config.pe_entity, "spm_unit")
        self.assertIsNone(tanf_federal_config.pe_period_month)
        # Matches federal/pe/spm.py's Tanf.pe_inputs exactly (2 entries, no
        # state-code -- this is the federal base, extended per-state later).
        self.assertEqual(tanf_federal_config.pe_inputs, [AgeDependency, FullTimeCollegeStudentDependency])


class TestTxTanfConfigLoadsCorrectly(SimpleTestCase):
    def test_tx_tanf_config_extends_federal_and_appends_tx_state_code(self):
        self.assertEqual(tx_tanf_config.state, "tx")
        self.assertEqual(tx_tanf_config.pe_name, "tx_tanf")
        self.assertIsNone(tx_tanf_config.pe_period_month)
        self.assertIn(TxStateCodeDependency, tx_tanf_config.pe_inputs)


class TestWaTanfConfigLoadsCorrectly(SimpleTestCase):
    def test_wa_tanf_config_extends_federal_and_appends_wa_specific_inputs(self):
        self.assertEqual(wa_tanf_config.state, "wa")
        self.assertEqual(wa_tanf_config.pe_name, "wa_tanf")
        self.assertIsNone(wa_tanf_config.pe_period_month)
        self.assertIn(WaStateCodeDependency, wa_tanf_config.pe_inputs)
        # WaTanf's real pe_inputs list is longer than TxTanf's -- wa_tanf's
        # PolicyEngine formula needs more inputs, not more calculator logic
        # (see tanf_registration.py's docstring).
        self.assertIn(PregnancyDependency, wa_tanf_config.pe_inputs)
        self.assertIn(WaShowAllCashAssistanceProgramsDependency, wa_tanf_config.pe_inputs)


class TestTanfFactoryHasTxAndWaRegistered(SimpleTestCase):
    def test_tx_and_wa_tanf_are_the_only_states_registered_so_far(self):
        # Documents the current, deliberate state (tanf_registration.py's
        # docstring) as an executable assertion, not just a comment -- this
        # test should start failing the moment a third state IS registered,
        # which is the correct signal to update it, not a bug.
        self.assertEqual(
            tanf_factory.as_dict(),
            {"tx_tanf": TxTanfCalculator, "wa_tanf": WaTanfCalculator},
        )


class TestTxTanfCalculatorHouseholdValue(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.white_label = WhiteLabel.objects.create(name="Texas", code="tx", state_code="TX")
        cls.fpl_year = FederalPoveryLimit.objects.create(year="2024", period="2024")

    def test_calc_produces_the_same_value_as_real_tanf_household_value(self):
        screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="79901",
            county="El Paso County",
            household_size=2,
            completed=False,
        )
        HouseholdMember.objects.create(
            screen=screen, relationship="headOfHousehold", age=30, disabled=False, student=False
        )
        HouseholdMember.objects.create(screen=screen, relationship="child", age=8, disabled=False, student=False)
        program = Program.objects.new_program(white_label="tx", name_abbreviated="tx_tanf")
        program.year = self.fpl_year
        program.save()

        calculator = TxTanfCalculator(screen, program, Dependencies())
        # No *12 conversion, unlike SNAP -- federal Tanf never overrides
        # household_value()/pe_output_period (D-019), so the raw PolicyEngine
        # value is read as-is.
        calculator.set_engine(StubSim({("spm_units", "spm_unit", "tx_tanf", "2024"): 275.0}))

        eligibility = calculator.calc()

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.household_value, 275)


class TestWaTanfCalculatorHouseholdValue(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.white_label = WhiteLabel.objects.create(name="Washington", code="wa", state_code="WA")
        cls.fpl_year = FederalPoveryLimit.objects.create(year="2024", period="2024")

    def test_calc_produces_the_same_value_as_real_tanf_household_value(self):
        screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="99201",
            county="Spokane County",
            household_size=2,
            household_assets=0,
            completed=False,
        )
        HouseholdMember.objects.create(
            screen=screen, relationship="headOfHousehold", age=34, disabled=False, student=False
        )
        HouseholdMember.objects.create(screen=screen, relationship="child", age=5, disabled=False, student=False)
        program = Program.objects.new_program(white_label="wa", name_abbreviated="wa_tanf")
        program.year = self.fpl_year
        program.save()

        calculator = WaTanfCalculator(screen, program, Dependencies())
        # No *12 conversion, unlike SNAP -- same reasoning as TxTanf above.
        calculator.set_engine(StubSim({("spm_units", "spm_unit", "wa_tanf", "2024"): 470.0}))

        eligibility = calculator.calc()

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.household_value, 470)

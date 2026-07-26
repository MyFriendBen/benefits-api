"""
Real (non-fictional) counterpart to test_coexistence.py's toy-registration
check: confirms co_snap_config actually loads through snap_registration.py
and CoSnapCalculator produces the correct household value end-to-end
through calc() -- a same-input/same-output micro-check against federal
Snap.household_value()'s real cast-then-multiply-by-12 math
(federal/pe/spm.py:42-43), not the full parallel-verification harness
(DECISIONS.md D-013; that's still gated on the not-yet-made tolerance-
threshold decision).
"""

from django.test import TestCase

from programs.models import FederalPoveryLimit, Program
from programs.programs.factories.snap_registration import CoSnapCalculator, co_snap_config
from programs.programs.policyengine.calculators.dependencies.household import CoStateCodeDependency
from programs.util import Dependencies
from screener.models import HouseholdMember, Screen, WhiteLabel


class StubSim:
    def __init__(self, data):
        self.data = data

    def value(self, unit, sub_unit, variable, period):
        return self.data[(unit, sub_unit, variable, period)]


class TestCoSnapConfigLoadsCorrectly(TestCase):
    def test_co_snap_config_extends_federal_and_appends_co_state_code(self):
        self.assertEqual(co_snap_config.state, "co")
        self.assertEqual(co_snap_config.pe_period_month, "01")
        self.assertIn(CoStateCodeDependency, co_snap_config.pe_inputs)


class TestCoSnapCalculatorHouseholdValue(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.white_label = WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")
        cls.fpl_year = FederalPoveryLimit.objects.create(year="2024", period="2024")

    def test_calc_produces_the_same_annualized_value_as_real_snap_household_value(self):
        screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="80202",
            county="Denver County",
            household_size=1,
            completed=False,
        )
        HouseholdMember.objects.create(
            screen=screen, relationship="headOfHousehold", age=35, disabled=False, student=False
        )
        program = Program.objects.new_program(white_label="co", name_abbreviated="co_snap")
        program.year = self.fpl_year
        program.save()

        calculator = CoSnapCalculator(screen, program, Dependencies())
        # Same real Docker-cassette value used in test_snap_calculator.py --
        # int(279.59998) * 12 == 3348, not int(279.59998 * 12) == 3355.
        calculator.set_engine(StubSim({("spm_units", "spm_unit", "snap", "2024-01"): 279.59998}))

        eligibility = calculator.calc()

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.household_value, 3348)

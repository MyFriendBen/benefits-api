"""
Phase 3 item 3: confirm old and new calculators can coexist and be called
interchangeably by the existing orchestration layer. Mixes the real TxSnap
(programs/programs/tx/pe/spm.py, already used as a fixture in
programs/programs/policyengine/tests/test_pe_input.py) with the fabricated
ZzToyProgram (toy_registration.py) through the *unmodified*
pe_input()/all_eligibility() functions -- no changes to policy_engine.py,
registry.py, or views.py.
"""

from django.test import TestCase

from programs.models import FederalPoveryLimit, Program
from programs.programs.factories.tests.toy_registration import ZzToyProgram
from programs.programs.policyengine.policy_engine import all_eligibility, pe_input
from programs.programs.tx.pe.spm import TxSnap
from programs.util import Dependencies
from screener.models import HouseholdMember, Screen, WhiteLabel


class CoexistenceTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.white_label = WhiteLabel.objects.create(name="Texas", code="tx", state_code="TX")
        cls.fpl_year = FederalPoveryLimit.objects.create(year="2024", period="2024")

    def setUp(self):
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Travis County",
            household_size=1,
            completed=False,
        )
        self.head = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=35,
            disabled=False,
            student=False,
        )

        self.program = Program.objects.new_program(white_label="tx", name_abbreviated="tx_snap")
        self.program.year = self.fpl_year
        self.program.save()

        self.missing_dependencies = Dependencies()
        self.old_calculator = TxSnap(self.screen, self.program, self.missing_dependencies)
        self.new_calculator = ZzToyProgram(self.screen, self.program, self.missing_dependencies)


class TestPeInputMixesOldAndNewCalculators(CoexistenceTestBase):
    def test_old_and_new_calculator_both_contribute_to_the_request(self):
        result = pe_input(self.screen, [self.old_calculator, self.new_calculator])

        people = result["household"]["people"][str(self.head.id)]
        spm_unit = result["household"]["spm_units"]["spm_unit"]

        self.assertIn("age", people)  # TxSnap's real dependency
        self.assertIn("is_full_time_college_student", people)  # toy's additional_input
        self.assertIn("snap", spm_unit)  # TxSnap's output field
        self.assertIn("zz_toy_value", spm_unit)  # toy's output field


class TestAllEligibilityMixesOldAndNewCalculators(CoexistenceTestBase):
    class StubSim:
        def __init__(self, data):
            self.data = data

        def value(self, unit, sub_unit, variable, period):
            return self.data[(unit, sub_unit, variable, period)]

    def test_both_calculators_produce_independently_correct_mergeable_eligibility(self):
        sim = self.StubSim(
            {
                ("spm_units", "spm_unit", "snap", "2024-01"): 300.0,
                ("spm_units", "spm_unit", "zz_toy_value", "2024"): 150.0,
            }
        )

        results = all_eligibility(sim, {"tx_snap": self.old_calculator, "zz_toy_program": self.new_calculator})

        self.assertIn("tx_snap", results)
        self.assertIn("zz_toy_program", results)
        self.assertTrue(results["tx_snap"].eligible)
        self.assertEqual(results["tx_snap"].household_value, 300 * 12)  # Snap.household_value()'s real *12
        self.assertTrue(results["zz_toy_program"].eligible)
        self.assertEqual(results["zz_toy_program"].household_value, 150)

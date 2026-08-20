"""MO tests."""

from screener.models import HouseholdMember
from screener.models import IncomeStream
from programs.programs.cross_white_label.msp.mo import MoMsp
from programs.framework.pe_dependencies.household import MoStateCodeDependency
from unittest.mock import Mock
from programs.programs.cross_white_label.msp.base import Msp
from screener.models import Screen
from django.test import TestCase
from screener.models import WhiteLabel
from integrations.clients.policyengine.policy_engine import pe_input


class TestMoMspWiring(TestCase):
    """
    MO-specific MSP wiring. ``MoMsp`` is the federal ``Msp`` calculator plus the MO state
    code and the Medicaid inputs.

    The shared contract (pe_name, pe_outputs, no federal input dropped, the Medicaid
    input set, exactly one state code matching the slug, no ``member_value`` override) is
    asserted for all registered subclasses in ``federal/pe/tests/test_msp.py``.

    MSP's income tiers are the federal floor in Missouri, so the state code is the only
    MO-keyed input. It resolves PolicyEngine's asset-test-applies parameter, which is
    ``true`` for MO — dropping it would stop applying the resource test and report
    over-resourced households as eligible, the failure Scenario 4 guards.
    """

    def test_is_subclass_of_federal_msp(self):
        self.assertTrue(issubclass(MoMsp, Msp))

    def test_program_code_is_mo_medicare_savings(self):
        self.assertEqual(MoMsp.program_code, "mo_medicare_savings")

    def test_pe_inputs_includes_mo_state_code(self):
        """Resolves the MO asset-test-applies parameter — the one genuine MO delta."""
        self.assertIn(MoStateCodeDependency, MoMsp.pe_inputs)


class TestMoMspPeInput(TestCase):
    """
    The one MSP payload behaviour that is MO's rather than every state's: Social Security
    retirement income must arrive as ``ssi_unearned_income``, because MSP's income test
    uses SSI methodology and that is what places the household in a QMB/SLMB/QI tier.

    The state-agnostic payload contract — the state code, the eligibility inputs, household
    assets, premium-free Part A, the requested ``msp`` output and the Medicaid
    determination inputs — is asserted for all four registered states in
    ``federal/pe/tests/test_msp.py``.
    """

    PERIOD = "2026"

    def setUp(self):
        self.white_label, _ = WhiteLabel.objects.get_or_create(
            code="mo", defaults={"name": "Missouri", "state_code": "MO"}
        )
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            agree_to_tos=True,
            is_test=True,
            household_size=1,
            household_assets=3_000,
            completed=False,
        )
        self.head = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=71,
        )

    def _calculator(self):
        program = Mock()
        program.year.period = self.PERIOD
        return MoMsp(self.screen, program, self.screen.missing_fields())

    def test_sends_social_security_as_ssi_unearned_income(self):
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="sSRetirement",
            amount=1_000,
            frequency="monthly",
        )

        people = pe_input(self.screen, [self._calculator()])["household"]["people"]

        self.assertEqual(people[str(self.head.id)]["ssi_unearned_income"], {self.PERIOD: 12_000})

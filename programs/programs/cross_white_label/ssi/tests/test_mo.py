"""MO tests."""

from programs.programs.cross_white_label.ssi.base import Ssi as FederalSsi
from screener.models import HouseholdMember
from screener.models import IncomeStream
from programs.programs.cross_white_label.ssi.mo import MoSsi
from programs.framework.pe_dependencies.household import MoStateCodeDependency
from unittest.mock import Mock
from programs.framework.pe_base import PolicyEngineMembersCalculator
from screener.models import Screen
from programs.framework.pe_dependencies.member import SsiIfTakesUp
from django.test import TestCase
from screener.models import WhiteLabel
from programs.framework.pe_dependencies.payload import pe_input


class TestMoSsiWiring(TestCase):
    """MoSsi inherits the federal SSI calculator and adds only the MO state code."""

    def test_pe_name_is_the_would_be_ssi_variable(self):
        self.assertEqual(MoSsi.pe_name, "ssi_if_takes_up")

    def test_adds_nothing_but_the_state_code(self):
        """
        Pins "Δ for MO: None". PE's ``ssi`` reads only ``gov.ssa.ssi.*`` params and PE models
        SSI state supplements for NM/SC/TX only, so any extra MO input here would be a new
        claim about state variance that needs its own justification.
        """
        self.assertEqual(set(MoSsi.pe_inputs) - set(FederalSsi.pe_inputs), {MoStateCodeDependency})

    def test_pe_outputs_is_the_would_be_ssi_variable(self):
        """
        ssi_if_takes_up, not ssi: takes_up_ssi_if_eligible is False for anyone not
        reporting SSI, which zeroes ``ssi`` for exactly the people mo_ssi is for.
        """
        self.assertEqual(MoSsi.pe_outputs, [SsiIfTakesUp])

    def test_does_not_override_member_value(self):
        """
        MoSsi returns PolicyEngine's computed dollar amount via the inherited
        ``member_value``. Unlike WIC, there is no zeroed category table to work around,
        so an override here would mean hardcoding an FBR that stops tracking SSA COLAs.
        """
        self.assertIs(MoSsi.member_value, PolicyEngineMembersCalculator.member_value)


class TestMoSsiPeInput(TestCase):
    """MoSsi's dependencies land in the pe_input payload sent to PolicyEngine."""

    PERIOD = "2026"

    @classmethod
    def setUpTestData(cls):
        cls.white_label = WhiteLabel.objects.create(name="Missouri", code="mo", state_code="MO")

    def setUp(self):
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="65101",
            county="Cole County",
            household_size=1,
            household_assets=1_500,
            completed=False,
        )
        self.head = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=67,
            disabled=True,
        )

    def _calculator(self):
        program = Mock()
        program.year.period = self.PERIOD
        return MoSsi(self.screen, program, self.screen.missing_fields())

    def test_sends_mo_state_code(self):
        household = pe_input(self.screen, [self._calculator()])["household"]["households"]["household"]

        self.assertIn("state_code", household)
        self.assertIn("MO", household["state_code"].values())

    def test_sends_ssi_eligibility_inputs_for_the_member(self):
        people = pe_input(self.screen, [self._calculator()])["household"]["people"]
        head = people[str(self.head.id)]

        for field in ("age", "is_blind", "is_disabled", "ssi_countable_resources", "ssi"):
            self.assertIn(field, head)

    def test_splits_household_assets_into_countable_resources(self):
        people = pe_input(self.screen, [self._calculator()])["household"]["people"]
        head = people[str(self.head.id)]

        self.assertEqual(head["ssi_countable_resources"], {self.PERIOD: 1_500})

    def test_sends_earned_and_unearned_income_separately(self):
        """
        SSI's exclusion stack treats the two differently ($20 general, then $65 + 1/2 of
        remaining earned), so collapsing them would understate the benefit.
        """
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="wages",
            amount=500,
            frequency="monthly",
        )
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="sSA",
            amount=300,
            frequency="monthly",
        )

        people = pe_input(self.screen, [self._calculator()])["household"]["people"]
        head = people[str(self.head.id)]

        self.assertEqual(head["ssi_earned_income"], {self.PERIOD: 6_000})
        self.assertEqual(head["ssi_unearned_income"], {self.PERIOD: 3_600})

    def test_requests_ssi_output_for_the_member(self):
        people = pe_input(self.screen, [self._calculator()])["household"]["people"]

        self.assertIn("ssi", people[str(self.head.id)])

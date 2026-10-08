"""Wiring and value arithmetic for ``MoSab``. Nothing here talks to PolicyEngine; the
end-to-end scenarios live in ``test_scenarios.py``."""

from django.test import TestCase

from integrations.clients.policyengine.engines import Sim
from programs.framework.pe_dependencies.payload import pe_input
from programs.programs.testing_fixtures.pe_integration import add_income, add_member, make_program, make_screen
from programs.programs.white_labels.mo.sab.calculator import MoSab
from programs.util import Dependencies
import programs.framework.pe_dependencies as dependency

YEAR = "2026"


class StubSim(Sim):
    """Returns a fixed monthly ``mo_ssp`` and records the period it was asked at."""

    def __init__(self, monthly_by_member):
        super().__init__({})
        self.monthly_by_member = monthly_by_member
        self.periods = []

    def value(self, unit, sub_unit, variable, period):
        assert variable == "mo_ssp", f"unexpected variable {variable}"
        self.periods.append(period)

        return self.monthly_by_member[sub_unit]


class MoSabTestBase(TestCase):
    def build(self):
        screen = make_screen(
            1, white_label_code="mo", state_code="MO", household_size=2, zipcode="65101", county="Cole County"
        )
        self.program = make_program("mo", "mo_sab", YEAR)
        self.head = add_member(screen, 1, "headOfHousehold", 40, visually_impaired=True)
        self.spouse = add_member(screen, 2, "spouse", 38, visually_impaired=False)

        return screen

    def calculator(self, screen):
        return MoSab(screen, self.program, Dependencies())

    def payload(self, screen):
        return pe_input(screen, [self.calculator(screen)])["household"]


class TestMoSabPeInput(MoSabTestBase):
    """What MoSab asks PolicyEngine for."""

    def test_declares_sab_as_the_living_arrangement(self):
        """The arrangement defaults to NONE, which pays $0 to everyone without an error."""
        people = self.payload(self.build())["people"]

        self.assertEqual(people["1"]["mo_ssp_living_arrangement"][YEAR], "SAB")

    def test_sends_blindness_from_the_screener_flag(self):
        people = self.payload(self.build())["people"]

        self.assertTrue(people["1"]["is_blind"][YEAR])
        self.assertFalse(people["2"]["is_blind"][YEAR])

    def test_sends_age_so_the_default_of_40_cannot_clear_the_floor(self):
        people = self.payload(self.build())["people"]

        self.assertEqual(people["1"]["age"][YEAR], 40)
        self.assertEqual(people["2"]["age"][YEAR], 38)

    def test_sends_state_code_mo(self):
        household = self.payload(self.build())["households"]["household"]

        self.assertEqual(household["state_code"][YEAR], "MO")

    def test_boarder_income_is_sent_as_earned_income(self):
        """Missouri counts boarder income as earned; PolicyEngine reads only employment_income."""
        screen = self.build()
        add_income(self.head, 1_200, income_type="boarder")

        people = self.payload(screen)["people"]

        self.assertEqual(people["1"]["employment_income"][YEAR], 1_200 * 12)

    def test_wages_still_count_as_earned_income(self):
        screen = self.build()
        add_income(self.head, 500, income_type="wages")

        people = self.payload(screen)["people"]

        self.assertEqual(people["1"]["employment_income"][YEAR], 500 * 12)

    def test_does_not_use_the_shared_wages_only_mapping(self):
        self.assertNotIn(dependency.member.EmploymentIncomeDependency, MoSab.pe_inputs)
        self.assertIn(dependency.member.MoSabEarnedIncomeDependency, MoSab.pe_inputs)

    def test_adopts_the_receipt_contract(self):
        """The grant is $949 less the SSI received, which the contract is what makes PE read."""
        for dep in dependency.receipt_contract:
            self.assertIn(dep, MoSab.pe_inputs)


class TestMoSabValue(MoSabTestBase):
    """How MoSab turns PolicyEngine's monthly figure into a value."""

    def run_calc(self, monthly_by_member):
        screen = self.build()
        calculator = self.calculator(screen)
        sim = StubSim(monthly_by_member)
        calculator.set_engine(sim)

        return calculator.calc(), sim

    def test_value_is_the_monthly_figure_times_twelve(self):
        eligibility, _ = self.run_calc({"1": 949.0, "2": 0.0})

        self.assertEqual(eligibility.value, 949 * 12)
        self.assertTrue(eligibility.eligible)

    def test_reads_mo_ssp_at_the_pinned_month_not_the_year(self):
        """Read annually, PolicyEngine sums twelve months and blends the July 1 turnover."""
        _, sim = self.run_calc({"1": 949.0, "2": 0.0})

        self.assertEqual(set(sim.periods), {f"{YEAR}-07"})

    def test_the_one_dollar_minimum_survives_as_twelve(self):
        """PolicyEngine pays $1 for a remainder under a dollar; that annualizes to $12."""
        eligibility, _ = self.run_calc({"1": 1.0, "2": 0.0})

        self.assertEqual(eligibility.value, 12)
        self.assertTrue(eligibility.eligible)

    def test_value_is_per_eligible_member(self):
        eligibility, _ = self.run_calc({"1": 949.0, "2": 949.0})

        self.assertEqual(eligibility.value, 2 * 949 * 12)

    def test_zero_from_policyengine_is_ineligible(self):
        eligibility, _ = self.run_calc({"1": 0.0, "2": 0.0})

        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.value, 0)

"""
Spec-scenario tests for MO CSFP — one test per Test Scenario in ``specs/mo.md``.

Every value comes from PolicyEngine via a recorded cassette, and every scenario also asserts
that ``state_code`` reaches PolicyEngine as ``MO``. Ages are fixed integers derived once from
the spec's birth months rather than sent as birth dates: VCR matches on the exact request body,
so an age that moved with the wall clock would break the suite on a calendar boundary.
Scenario 17 therefore pins PolicyEngine's ``>= 60`` at 60, like scenario 5; the
month-precision derivation of that age is the screener's, not this program's.
"""

import pytest

from programs.framework.pe_dependencies.household import CountyDependency, MoStateCodeDependency
from programs.framework.pe_dependencies.payload import pe_input
from programs.programs.cross_white_label.csfp.mo import MoCsfp
from programs.programs.testing_fixtures.pe_integration import (
    PeIntegrationTestCase,
    add_income,
    add_member,
    calc_pe_program,
    make_program,
    make_screen,
    screener_value,
)
from programs.util import Dependencies

PE_VERSION = "2.5.0"
YEAR = "2026"

# gov.usda.csfp.amount for 2026, per qualifying individual.
CSFP_VALUE = 651

BOONE = ("65201", "Boone County")

# Scenarios 8-13 and 15: wages plus $3,000 of the type under test, $24,600 against $23,940.
BASE_WAGES = 21_600
TYPE_UNDER_TEST = 3_000


@pytest.mark.integration
class TestMoCsfpScenarios(PeIntegrationTestCase):
    pe_version = PE_VERSION

    def build(self, screen_id, household_size, location=BOONE):
        zipcode, county = location
        # make_screen creates the white label; make_program looks it up, so it runs second.
        screen = make_screen(
            screen_id,
            white_label_code="mo",
            state_code="MO",
            household_size=household_size,
            zipcode=zipcode,
            county=county,
        )
        self.program = make_program("mo", "mo_csfp", YEAR, state_code="MO")
        return screen

    def person(self, screen, offset, relationship, age):
        return add_member(screen, screen.id * 100 + offset, relationship, age)

    def single_senior(self, screen_id, location=BOONE):
        """The spec's standard applicant: born June 1960, age 66, head of household."""
        screen = self.build(screen_id, household_size=1, location=location)
        return screen, self.person(screen, 1, "headOfHousehold", 66)

    def assert_result(self, screen, expected_eligible, expected_value):
        payload = pe_input(screen, [MoCsfp(screen, self.program, Dependencies())])
        self.assertEqual(payload["household"]["households"]["household"]["state_code"][YEAR], "MO")

        result = calc_pe_program(screen, MoCsfp, self.program)
        self.assertEqual((bool(result.eligible), screener_value(result)), (expected_eligible, expected_value))

    def assert_type_counted(self, screen_id, income_type):
        screen, head = self.single_senior(screen_id)
        add_income(head, BASE_WAGES, frequency="yearly")
        add_income(head, TYPE_UNDER_TEST, income_type=income_type, frequency="yearly")

        self.assert_result(screen, False, 0)

    def test_scenario_1_single_senior_under_limit(self):
        """Scenario 1: age 66, $18,000/yr wages — eligible, $651."""
        screen, head = self.single_senior(1)
        add_income(head, 1_500)

        self.assert_result(screen, True, CSFP_VALUE)

    def test_scenario_2_age_59(self):
        """Scenario 2: age 59, income-eligible — ineligible."""
        screen = self.build(2, household_size=1)
        head = self.person(screen, 1, "headOfHousehold", 59)
        add_income(head, 1_500)

        self.assert_result(screen, False, 0)

    def test_scenario_3_one_dollar_over_limit(self):
        """Scenario 3: $23,941/yr against $23,940 — ineligible."""
        screen, head = self.single_senior(3)
        add_income(head, 23_941, frequency="yearly")

        self.assert_result(screen, False, 0)

    def test_scenario_4_two_seniors(self):
        """Scenario 4: two seniors, $18,000/yr — eligible, $1,302."""
        screen = self.build(4, household_size=2)
        self.person(screen, 1, "headOfHousehold", 68)
        spouse = self.person(screen, 2, "spouse", 66)
        add_income(spouse, 1_500)

        self.assert_result(screen, True, 2 * CSFP_VALUE)

    def test_scenario_5_exactly_age_60(self):
        """Scenario 5: age 60 — eligible, $651."""
        screen = self.build(5, household_size=1)
        head = self.person(screen, 1, "headOfHousehold", 60)
        add_income(head, 1_500)

        self.assert_result(screen, True, CSFP_VALUE)

    def test_scenario_6_income_exactly_at_limit(self):
        """Scenario 6: $23,940/yr — eligible, $651, with no simulated SSI entering the total."""
        screen, head = self.single_senior(6)
        add_income(head, 23_940, frequency="yearly")

        self.assert_result(screen, True, CSFP_VALUE)

    def test_scenario_7_one_senior_one_younger_adult(self):
        """Scenario 7: only the 66-year-old qualifies — $651, not $1,302."""
        screen = self.build(7, household_size=2)
        self.person(screen, 1, "headOfHousehold", 66)
        child = self.person(screen, 2, "child", 40)
        add_income(child, 1_200)

        self.assert_result(screen, True, CSFP_VALUE)

    def test_scenario_8_child_support_counted(self):
        """Scenario 8: wages + child support = $24,600/yr — ineligible."""
        self.assert_type_counted(8, "childSupport")

    def test_scenario_9_workers_comp_counted(self):
        """Scenario 9: wages + workers' comp = $24,600/yr — ineligible."""
        self.assert_type_counted(9, "workersComp")

    def test_scenario_10_alimony_counted(self):
        """Scenario 10: wages + alimony = $24,600/yr — ineligible."""
        self.assert_type_counted(10, "alimony")

    def test_scenario_11_unemployment_counted(self):
        """Scenario 11: wages + unemployment = $24,600/yr — ineligible."""
        self.assert_type_counted(11, "unemployment")

    def test_scenario_12_deferred_comp_counted(self):
        """Scenario 12: wages + deferred compensation = $24,600/yr — ineligible."""
        self.assert_type_counted(12, "deferredComp")

    def test_scenario_13_investment_counted(self):
        """Scenario 13: wages + investment = $24,600/yr — ineligible."""
        self.assert_type_counted(13, "investment")

    def test_scenario_14_harrison_county(self):
        """Scenario 14: scenario 1's household in Harrison County — eligible, $651.

        Asserted on the declared inputs as the spec directs: no county input, and the MO
        state code.
        """
        self.assertFalse(any(issubclass(Data, CountyDependency) for Data in MoCsfp.pe_inputs))
        self.assertIn(MoStateCodeDependency, MoCsfp.pe_inputs)

        screen, head = self.single_senior(14, location=("64424", "Harrison County"))
        add_income(head, 1_500)

        self.assert_result(screen, True, CSFP_VALUE)

    def test_scenario_15_non_tanf_cash_assistance_counted(self):
        """Scenario 15: wages + non-TANF cash assistance = $24,600/yr — ineligible."""
        self.assert_type_counted(15, "cashAssistanceOther")

    def test_scenario_16_two_seniors_between_limits(self):
        """Scenario 16: two seniors at $28,000/yr, over one-person but under two-person — $1,302."""
        screen = self.build(16, household_size=2)
        head = self.person(screen, 1, "headOfHousehold", 66)
        add_income(head, 28_000, frequency="yearly")
        self.person(screen, 2, "spouse", 68)

        self.assert_result(screen, True, 2 * CSFP_VALUE)

    def test_scenario_17_turns_60_in_reference_month(self):
        """Scenario 17: born September 1966, age 60 on 2026-09-17 — eligible, $651."""
        screen = self.build(17, household_size=1)
        head = self.person(screen, 1, "headOfHousehold", 60)
        add_income(head, 1_500)

        self.assert_result(screen, True, CSFP_VALUE)

"""
Spec-scenario tests for KS CSFP — one test per Test Scenario in ``specs/ks.md``.

Every value comes from PolicyEngine via a recorded cassette. Ages are fixed integers derived
once against the spec's reference date (2026-08-27) rather than sent as birth dates: VCR
matches on the exact request body, so an age that moved with the wall clock would break the
suite on a calendar boundary. Scenarios 1 and 4 therefore pin PolicyEngine's ``>= 60`` at 60
and 59; the month-inclusive derivation of those ages is the screener's, not this program's.
"""

import pytest

from programs.programs.cross_white_label.csfp.ks import KsCsfp
from programs.programs.testing_fixtures.households import add_expense
from programs.programs.testing_fixtures.pe_integration import (
    PeIntegrationTestCase,
    add_income,
    add_member,
    calc_pe_program,
    make_program,
    make_screen,
    screener_value,
)
from screener.serializers import _write_current_benefits
from screener.tests.helpers import seed_program

PE_VERSION = "2.5.0"
YEAR = "2026"

# gov.usda.csfp.amount for 2026, per qualifying individual.
CSFP_VALUE = 651

SEDGWICK = ("67214", "Sedgwick County")

# Current Benefits tiles, keyed by the base program the categorical routes resolve through.
CURRENT_BENEFIT_ROWS = {
    "snap": "ks_snap",
    "ssi": "ks_ssi",
    "medicare_savings": "ks_medicare_savings",
    "tanf": "ks_tanf",
}


@pytest.mark.integration
class TestKsCsfpScenarios(PeIntegrationTestCase):
    pe_version = PE_VERSION

    def build(self, screen_id, household_size, location=SEDGWICK):
        zipcode, county = location
        # make_screen creates the white label; make_program looks it up, so it runs second.
        screen = make_screen(
            screen_id,
            white_label_code="ks",
            state_code="KS",
            household_size=household_size,
            zipcode=zipcode,
            county=county,
        )
        self.program = make_program("ks", "ks_csfp", YEAR, state_code="KS")
        return screen

    def person(self, screen, offset, relationship, age):
        return add_member(screen, screen.id * 100 + offset, relationship, age)

    def report_benefit(self, screen, base_program):
        name = CURRENT_BENEFIT_ROWS[base_program]
        # The categorical routes resolve through has_base_benefit, so the row needs its
        # base_program rather than a literal name.
        seed_program(screen.white_label, name, base_program=base_program)
        _write_current_benefits(screen, [name])
        screen.invalidate_current_benefits_cache()

    def assert_result(self, screen, expected_eligible, expected_value):
        result = calc_pe_program(screen, KsCsfp, self.program)
        self.assertEqual((bool(result.eligible), screener_value(result)), (expected_eligible, expected_value))

    def test_scenario_1_turns_60_in_reference_month(self):
        """Scenario 1: age 60 exactly, $1,400/mo Social Security — eligible, $651."""
        screen = self.build(1, household_size=1)
        head = self.person(screen, 1, "headOfHousehold", 60)
        add_income(head, 1_400, income_type="sSRetirement")

        self.assert_result(screen, True, CSFP_VALUE)

    def test_scenario_2_income_at_one_person_limit(self):
        """Scenario 2: $23,940/yr, exactly 150% FPG for one — eligible, $651."""
        screen = self.build(2, household_size=1)
        head = self.person(screen, 1, "headOfHousehold", 68)
        add_income(head, 1_995, income_type="sSRetirement")

        self.assert_result(screen, True, CSFP_VALUE)

    def test_scenario_3_one_dollar_over_limit_with_rent(self):
        """Scenario 3: $23,952/yr gross, rent not deducted — ineligible."""
        screen = self.build(3, household_size=1)
        head = self.person(screen, 1, "headOfHousehold", 68)
        add_income(head, 1_996, income_type="sSRetirement")
        add_expense(head, 900, expense_type="rent")

        self.assert_result(screen, False, 0)

    def test_scenario_4_turns_60_month_after_reference(self):
        """Scenario 4: age 59, comfortably income-eligible — ineligible."""
        screen = self.build(4, household_size=1)
        head = self.person(screen, 1, "headOfHousehold", 59)
        add_income(head, 1_400, income_type="sSRetirement")

        self.assert_result(screen, False, 0)

    def test_scenario_5_two_seniors_at_two_person_limit(self):
        """Scenario 5: two seniors at $32,460/yr — eligible, $1,302."""
        screen = self.build(5, household_size=2)
        head = self.person(screen, 1, "headOfHousehold", 61)
        add_income(head, 1_505, income_type="sSRetirement")
        spouse = self.person(screen, 2, "spouse", 67)
        add_income(spouse, 1_200, income_type="sSRetirement")

        self.assert_result(screen, True, 2 * CSFP_VALUE)

    def test_scenario_6_two_seniors_one_dollar_over_two_person_limit(self):
        """Scenario 6: two seniors at $32,472/yr — ineligible."""
        screen = self.build(6, household_size=2)
        head = self.person(screen, 1, "headOfHousehold", 61)
        add_income(head, 1_506, income_type="sSRetirement")
        spouse = self.person(screen, 2, "spouse", 67)
        add_income(spouse, 1_200, income_type="sSRetirement")

        self.assert_result(screen, False, 0)

    def test_scenario_7_one_senior_one_younger_adult(self):
        """Scenario 7: only the 61-year-old qualifies; both count toward size — $651."""
        screen = self.build(7, household_size=2)
        head = self.person(screen, 1, "headOfHousehold", 61)
        add_income(head, 1_500, income_type="sSRetirement")
        child = self.person(screen, 2, "child", 40)
        add_income(child, 1_200)

        self.assert_result(screen, True, CSFP_VALUE)

    def test_scenario_8_over_limit_with_snap(self):
        """Scenario 8: $24,000/yr, reported SNAP displaces the income test — $651."""
        screen = self.build(8, household_size=1)
        head = self.person(screen, 1, "headOfHousehold", 68)
        add_income(head, 2_000, income_type="sSRetirement")
        add_expense(head, 1_400, expense_type="rent")
        self.report_benefit(screen, "snap")

        self.assert_result(screen, True, CSFP_VALUE)

    def test_scenario_9_senior_on_ssi_household_over_limit(self):
        """Scenario 9: senior's own SSI is a route; household $43,800/yr — $651."""
        screen = self.build(9, household_size=2)
        head = self.person(screen, 1, "headOfHousehold", 68)
        add_income(head, 900, income_type="sSI")
        child = self.person(screen, 2, "child", 40)
        add_income(child, 2_750)
        self.report_benefit(screen, "ssi")

        self.assert_result(screen, True, CSFP_VALUE)

    def test_scenario_10_senior_on_msp_household_over_limit(self):
        """Scenario 10: PolicyEngine's computed MSP is a route; household $48,600/yr — $651."""
        screen = self.build(10, household_size=2)
        head = self.person(screen, 1, "headOfHousehold", 68)
        add_income(head, 1_300, income_type="sSRetirement")
        child = self.person(screen, 2, "child", 40)
        add_income(child, 2_750)
        self.report_benefit(screen, "medicare_savings")

        self.assert_result(screen, True, CSFP_VALUE)

    def test_scenario_11_over_limit_with_tanf(self):
        """Scenario 11: TANF is not one of Kansas's five routes — ineligible."""
        screen = self.build(11, household_size=1)
        head = self.person(screen, 1, "headOfHousehold", 68)
        add_income(head, 2_000, income_type="sSRetirement")
        self.report_benefit(screen, "tanf")

        self.assert_result(screen, False, 0)

    def test_scenario_12_two_income_types_cross_limit(self):
        """Scenario 12: Social Security + unemployment = $24,000/yr — ineligible."""
        screen = self.build(12, household_size=1)
        head = self.person(screen, 1, "headOfHousehold", 68)
        add_income(head, 1_200, income_type="sSRetirement")
        add_income(head, 800, income_type="unemployment")

        self.assert_result(screen, False, 0)

    def test_scenario_13_county_without_distribution_site(self):
        """Scenario 13: scenario 1's household in Allen County — the county gate denies."""
        screen = self.build(13, household_size=1, location=("66749", "Allen County"))
        head = self.person(screen, 1, "headOfHousehold", 68)
        add_income(head, 1_400, income_type="sSRetirement")

        self.assert_result(screen, False, 0)

    def test_scenario_14_gifts_cross_limit(self):
        """Scenario 14: Social Security + gifts = $25,200/yr — ineligible."""
        screen = self.build(14, household_size=1)
        head = self.person(screen, 1, "headOfHousehold", 68)
        add_income(head, 1_900, income_type="sSRetirement")
        add_income(head, 200, income_type="gifts")

        self.assert_result(screen, False, 0)

    def test_scenario_15_adult_child_holds_ssi(self):
        """Scenario 15: the under-60 child's SSI does not qualify the senior — ineligible."""
        screen = self.build(15, household_size=2)
        head = self.person(screen, 1, "headOfHousehold", 68)
        add_income(head, 2_000, income_type="sSRetirement")
        child = self.person(screen, 2, "child", 40)
        add_income(child, 1_600)
        add_income(child, 900, income_type="sSI")
        self.report_benefit(screen, "ssi")

        self.assert_result(screen, False, 0)

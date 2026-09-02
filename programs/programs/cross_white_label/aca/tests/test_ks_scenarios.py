"""KS ACA PTC — one test per ``specs/ks.md`` Test Scenario.

Recorded against PolicyEngine and replayed from the cassettes beside this file, so what is
asserted is PolicyEngine's own answer for the household the spec describes. Nothing about
Kansas ACA eligibility or value is our code's decision; these tests exist to catch the
scenarios drifting away from what PolicyEngine returns.

Scenarios 1 and 2 differ *only* in county, which is what isolates the rating-area effect:
Kansas has 7 rating areas, ``slcsp_rating_area_default`` keys them off ``county_str``, and
anything it can't match silently falls back to rating area 1. Wyandotte is area 1 and
Sedgwick is area 6, so the pair also fails loudly if ``KsCountyDependency`` ever stops
reaching PolicyEngine — a county-less request would return Scenario 1's value twice.
"""

import pytest

from programs.programs.cross_white_label.aca.ks import KsAca
from programs.programs.testing_fixtures.pe_integration import (
    PeIntegrationTestCase,
    add_income,
    add_member,
    calc_pe_program,
    make_program,
    make_screen,
    screener_value,
)
from screener.models import Insurance

# Recorded at "current" rather than "frontier": production and staging both ride the
# floating current alias, so this is the version real households are scored against.
# 1.815.1 and frontier 1.821.2 return identical values for all three scenarios, so no
# PolicyEngineConfig pin is needed to ship.
PE_VERSION = "1.815.1"
YEAR = "2026"

# Age 35 at the 2026 coverage year, stated in the spec as birth month/year March 1991. Fixed
# as an integer rather than a birth date: VCR matches on the exact request body, so an age
# derived from timezone.now() would break every cassette here on a calendar boundary.
AGE = 35


@pytest.mark.integration
class TestKsAcaScenarios(PeIntegrationTestCase):
    pe_version = PE_VERSION

    def _single_adult(self, screen_id, zipcode, county, annual_income):
        """The spec's household: one uninsured adult, no dependents, no employer offer.

        ``Insurance`` is created explicitly with ``none=True`` rather than left to the model
        default so the "no health coverage, no employer offer" half of each scenario is
        stated in the fixture — it is what makes ``has_esi`` False, and ``has_esi`` is the
        difference between the full credit and $0.
        """
        screen = make_screen(
            screen_id=screen_id,
            white_label_code="ks",
            state_code="KS",
            household_size=1,
            zipcode=zipcode,
            county=county,
        )
        adult = add_member(screen, member_id=1, relationship="headOfHousehold", age=AGE)
        Insurance.objects.create(household_member=adult, none=True)
        # Yearly, so the figure in the test is the annual figure the spec states.
        # IncomeDependency sends int(annual income), so a monthly amount would need
        # $18,780/12 = $1,565.00 exactly and $7,825/12 = $652.08 with a cent lost.
        add_income(adult, amount=annual_income, frequency="yearly")

        return screen, make_program("ks", "ks_aca_ptc", year=YEAR)

    def test_scenario_1_wyandotte_120_percent_fpl_coverage_gap(self):
        """Scenario 1: single adult, Wyandotte County (rating area 1), $18,780/yr — 120% FPL
        against the 2025 poverty guideline ($15,650) that 2026 coverage uses.

        This is the non-expansion coverage gap: Kansas has no KanCare expansion, so a
        childless adult here has no Medicaid pathway and the marketplace credit is the only
        subsidy available. PolicyEngine applies the federal 100% FPL floor, which this
        household clears.
        """
        screen, program = self._single_adult(1, "66101", "Wyandotte County", 18_780)

        eligibility = calc_pe_program(screen, KsAca, program)

        self.assertTrue(eligibility.eligible)
        self.assertEqual(screener_value(eligibility), 6_257)

    def test_scenario_2_sedgwick_same_household_different_rating_area(self):
        """Scenario 2: Scenario 1's household moved to Sedgwick County (rating area 6).

        Age, income and household composition are held constant, so the whole difference in
        value is the benchmark-premium delta between rating areas 1 and 6. Both remain
        eligible — the county changes the amount, never the eligibility.
        """
        screen, program = self._single_adult(2, "67202", "Sedgwick County", 18_780)

        eligibility = calc_pe_program(screen, KsAca, program)

        self.assertTrue(eligibility.eligible)
        self.assertEqual(screener_value(eligibility), 7_599)

    def test_scenario_3_below_the_100_percent_fpl_floor_is_ineligible(self):
        """Scenario 3: same adult at $7,825/yr — 50% FPL, below the PTC's 100% floor.

        The credit is $0, not a reduced amount. In an expansion state this household would
        be Medicaid-eligible instead; in Kansas it is the coverage gap proper, which is why
        the scenario asserts a hard $0 rather than just "less".
        """
        screen, program = self._single_adult(3, "66101", "Wyandotte County", 7_825)

        eligibility = calc_pe_program(screen, KsAca, program)

        self.assertFalse(eligibility.eligible)
        self.assertEqual(screener_value(eligibility), 0)

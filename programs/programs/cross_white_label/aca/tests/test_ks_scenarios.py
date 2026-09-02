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

Scenarios 4 and 5 are the two boundaries most likely to break silently: the 400% FPL cap
restored for 2026 by the expiry of the enhanced ARPA/IRA credits, and the employer-coverage
disqualifier that PolicyEngine applies only when ``has_esi`` is sent. Both were added to the
spec during implementation rather than coming from discovery.
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
# 1.815.1 and frontier 1.821.2 return identical values for every scenario here, so no
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

    def _single_adult(self, screen_id, zipcode, county, annual_income, employer_coverage=False):
        """The spec's household: one adult, no dependents.

        ``Insurance`` is created explicitly rather than left to the model default so the
        coverage half of each scenario is stated in the fixture — it is what drives
        ``has_esi``, and ``has_esi`` is the difference between the full credit and $0
        (Scenario 5).
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
        Insurance.objects.create(
            household_member=adult,
            none=not employer_coverage,
            employer=employer_coverage,
        )
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

    def test_scenario_4_above_the_restored_400_percent_fpl_cap_is_ineligible(self):
        """Scenario 4: same adult at $63,000/yr — 402.6% FPL, over the 400% cap.

        The enhanced (ARPA/IRA) credits expired after 2025, so the 400% FPL cap is back in
        force for 2026 and PolicyEngine models it. This is the coverage gap's upper edge and
        the largest behavioral change in the program this year: the same household at
        $62,000 (396.2% FPL) is eligible for $476. Asserting $0 here is what would fail if
        the cap were re-lifted or PolicyEngine's parameter changed.

        Deliberately at 402.6% rather than exactly 400%: PolicyEngine treats exactly 400%
        FPL as ineligible where the statute ("does not exceed 400 percent") makes it
        eligible. See the spec's Data Gaps section — that one-dollar discrepancy is reported
        rather than encoded as an expectation here.
        """
        screen, program = self._single_adult(4, "66101", "Wyandotte County", 63_000)

        eligibility = calc_pe_program(screen, KsAca, program)

        self.assertFalse(eligibility.eligible)
        self.assertEqual(screener_value(eligibility), 0)

    def test_scenario_5_employer_sponsored_coverage_disqualifies(self):
        """Scenario 5: Scenario 1's household, but the adult has job-based coverage.

        Enrollment in an eligible employer plan is a statutory disqualifier
        (26 U.S.C. 36B(c)(2)(C)) that PolicyEngine applies only if we send ``has_esi``.
        Everything else is held identical to Scenario 1, so this isolates that single
        input: $6,257 → $0. If ``HasEsiDependency`` is ever dropped from ``KsAca``, this is
        the only scenario that fails.
        """
        screen, program = self._single_adult(5, "66101", "Wyandotte County", 18_780, employer_coverage=True)

        eligibility = calc_pe_program(screen, KsAca, program)

        self.assertFalse(eligibility.eligible)
        self.assertEqual(screener_value(eligibility), 0)

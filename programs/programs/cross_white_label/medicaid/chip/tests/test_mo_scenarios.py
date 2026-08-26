"""
Spec-scenario tests for MO CHIP — one test per Test Scenario in ``specs/mo.md``.

``MoChip`` sends the household facts and reads PolicyEngine's ``chip_gross`` and
``mo_chip_premium``, so these assert the whole result end to end: the Appendix A income
boundaries at both ends, the under-19 age gate, reported Medicaid enrollment, the Appendix E
premium tiers, premium-charged-once, and the value floor. Each runs its household through
PolicyEngine once and replays from a cassette.

Values are asserted in **annual whole dollars**, which is what the screener reports:
``screener_value`` truncates the way ``screener/views.py`` does. So Scenario 1's
$2,527.85 is asserted as $2,527.

Ages are fixed integers rather than birth dates. The spec evaluates every age against
July 20, 2026; ``birth_year_month`` would make each age a function of ``timezone.now()``,
and VCR matches on the exact request body, so the suite would break on a calendar boundary.

Scenarios 5, 6, 15b, 19 and 21 step **one dollar** past their boundary, not the one cent
the spec originally stated. ``IncomeDependency`` sends PolicyEngine ``int(annual income)``,
so a one-cent-per-month difference — twelve cents a year — is truncated away and the
household arrives identical to the boundary case it is meant to differ from. A dollar a
month is the smallest step that survives the truncation; each still lands in the tier and
on the side of the boundary the spec states, so what the scenario tests is unchanged.
specs/mo.md carries the same amounts. The truncation itself is shared-code behavior, not a
MoChip concern.

Scenario 8 and Scenario 16 are absent from the spec by design, not omitted here: they tested
the private/employer insurance distinction, which specs/mo.md Criterion 3 resolves as an
unmodelable data gap with one committed inclusive rule. ``test_mo.py`` pins that rule
directly instead. The scenario numbers below are the spec's own, so they skip 8 and 16.
"""

import pytest

from programs.programs.cross_white_label.medicaid.chip.mo import MoChip
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

PE_VERSION = "1.815.1"
YEAR = "2026"


class MoChipScenarioTestCase(PeIntegrationTestCase):
    """Shared household builder."""

    pe_version = PE_VERSION

    # Distinct per subclass so each scenario's cassette pins its own household.
    screen_id = 0

    def build(self, household_size, zipcode="63101", county="St. Louis City"):
        # make_screen creates the white label; make_program looks it up, so it has to
        # run second.
        screen = make_screen(
            self.screen_id,
            white_label_code="mo",
            state_code="MO",
            household_size=household_size,
            zipcode=zipcode,
            county=county,
        )
        self.program = make_program("mo", "mo_chip", YEAR)

        return screen

    def add_person(self, screen, offset, relationship, age, on_medicaid=False):
        member = add_member(screen, self.screen_id * 100 + offset, relationship, age)

        if on_medicaid:
            Insurance.objects.create(household_member=member, none=False, medicaid=True)

        return member

    def assert_result(self, screen, expected_eligible, expected_annual_value):
        result = calc_pe_program(screen, MoChip, self.program)
        self.assertEqual(
            (bool(result.eligible), screener_value(result)),
            (expected_eligible, expected_annual_value),
        )


@pytest.mark.integration
class TestScenario01ClearlyEligible(MoChipScenarioTestCase):
    """Happy path: family of 3 at ~183% FPL, first premium tier ($32/mo)."""

    screen_id = 1

    def test_family_of_three_first_premium_tier(self):
        screen = self.build(3, zipcode="65101", county="Cole")
        head = self.add_person(screen, 1, "headOfHousehold", 41)
        add_income(head, amount=4_167)
        self.add_person(screen, 2, "spouse", 39)
        self.add_person(screen, 3, "child", 7)
        self.assert_result(screen, True, 2_527)


@pytest.mark.integration
class TestScenario02FivePercentDisregard(MoChipScenarioTestCase):
    """Above the nominal 300% figure but inside the 5% disregard band — still eligible."""

    screen_id = 2

    def test_family_of_two_inside_the_disregard_band(self):
        screen = self.build(2)
        head = self.add_person(screen, 1, "headOfHousehold", 40)
        add_income(head, amount=5_458.33)
        self.add_person(screen, 2, "child", 18)
        self.assert_result(screen, True, 475)


@pytest.mark.integration
class TestScenario03InfantAtTheMedicaidCeiling(MoChipScenarioTestCase):
    """Exactly at Appendix A's under-1 maximum: the boundary is inclusive toward Medicaid."""

    screen_id = 3

    def test_newborn_exactly_at_the_infant_ceiling(self):
        screen = self.build(3)
        head = self.add_person(screen, 1, "headOfHousehold", 35)
        add_income(head, amount=4_577.00)
        self.add_person(screen, 2, "spouse", 32)
        self.add_person(screen, 3, "child", 0)
        self.assert_result(screen, False, 0)


@pytest.mark.integration
class TestScenario04ExactlyAtTheChipCeiling(MoChipScenarioTestCase):
    """Exactly at Appendix A's HH4 ceiling — still eligible. Two children, one premium."""

    screen_id = 4

    def test_family_of_four_two_children_at_the_ceiling(self):
        screen = self.build(4)
        head = self.add_person(screen, 1, "headOfHousehold", 38)
        add_income(head, amount=8_388.00)
        self.add_person(screen, 2, "spouse", 35)
        self.add_person(screen, 3, "child", 11)
        self.add_person(screen, 4, "child", 7)
        self.assert_result(screen, True, 2_115)


@pytest.mark.integration
class TestScenario05JustAboveTheChipCeiling(MoChipScenarioTestCase):
    """One dollar per month above Appendix A's HH3 ceiling — denied."""

    screen_id = 5

    def test_family_of_three_one_dollar_above_the_ceiling(self):
        screen = self.build(3)
        head = self.add_person(screen, 1, "headOfHousehold", 36)
        add_income(head, amount=6_945.00)
        self.add_person(screen, 2, "spouse", 33)
        self.add_person(screen, 3, "child", 8)
        self.assert_result(screen, False, 0)


@pytest.mark.integration
class TestScenario06InfantJustAboveTheMedicaidCeiling(MoChipScenarioTestCase):
    """Mirror of Scenario 3, one dollar higher: flips from Medicaid to CHIP ($105/mo tier)."""

    screen_id = 6

    def test_newborn_one_dollar_above_the_infant_ceiling(self):
        screen = self.build(3)
        head = self.add_person(screen, 1, "headOfHousehold", 35)
        add_income(head, amount=4_578.00)
        self.add_person(screen, 2, "spouse", 32)
        self.add_person(screen, 3, "child", 0)
        self.assert_result(screen, True, 1_651)


@pytest.mark.integration
class TestScenario07AgeNineteen(MoChipScenarioTestCase):
    """Income is comfortably in range, isolating age as the only exclusion."""

    screen_id = 7

    def test_nineteen_year_old_is_excluded(self):
        screen = self.build(2)
        head = self.add_person(screen, 1, "headOfHousehold", 46)
        add_income(head, amount=3_000)
        self.add_person(screen, 2, "child", 19)
        self.assert_result(screen, False, 0)


@pytest.mark.integration
class TestScenario09BelowThePremiumChipFloor(MoChipScenarioTestCase):
    """Below Appendix A's ages-1-18 boundary: routes to CHIP 4M, outside this calculator."""

    screen_id = 9

    def test_below_the_lower_routing_boundary(self):
        screen = self.build(3)
        head = self.add_person(screen, 1, "headOfHousehold", 36)
        add_income(head, amount=3_417)
        self.add_person(screen, 2, "spouse", 33)
        self.add_person(screen, 3, "child", 10)
        self.assert_result(screen, False, 0)


@pytest.mark.integration
class TestScenario10ValueFloor(MoChipScenarioTestCase):
    """Top tier, one child: the premium exceeds the gross value.

    The spec expects the child to stay eligible with the value floored. It floors at
    ``MoChip.min_value`` rather than $0 — a $0 program is reported ineligible
    (``eligible = value > 0``) and dropped by the frontend's ``programValue > 0`` filter,
    so a $0 floor would hide the program from exactly the families it applies to. See
    ``test_mo.py::TestMoChipValue::test_value_floors_at_one_dollar_rather_than_zero``.
    """

    screen_id = 10

    def test_single_child_top_tier_floors(self):
        screen = self.build(3)
        head = self.add_person(screen, 1, "headOfHousehold", 36)
        add_income(head, amount=5_833.33)
        self.add_person(screen, 2, "spouse", 33)
        self.add_person(screen, 3, "child", 8)
        self.assert_result(screen, True, MoChip.min_value)


@pytest.mark.integration
class TestScenario11ChildAlreadyOnMedicaid(MoChipScenarioTestCase):
    """Reported Medicaid enrollment reaches PolicyEngine as an input and it excludes the
    child — 42 CFR 457.350(d). Income is above the routing boundary, so this isolates the
    enrollment check from the income check in Scenario 9."""

    screen_id = 11

    def test_child_on_medicaid_is_excluded(self):
        screen = self.build(3)
        head = self.add_person(screen, 1, "headOfHousehold", 36)
        add_income(head, amount=2_500)
        spouse = self.add_person(screen, 2, "spouse", 33)
        add_income(spouse, amount=1_800)
        self.add_person(screen, 3, "child", 8, on_medicaid=True)
        self.assert_result(screen, False, 0)


@pytest.mark.integration
class TestScenario12MixedHousehold(MoChipScenarioTestCase):
    """Two children under 19 qualify, the 19-year-old does not, one premium ($127/mo)."""

    screen_id = 12

    def test_two_of_three_children_qualify(self):
        screen = self.build(4)
        head = self.add_person(screen, 1, "headOfHousehold", 42)
        add_income(head, amount=5_500)
        self.add_person(screen, 2, "child", 19)
        self.add_person(screen, 3, "child", 11)
        self.add_person(screen, 4, "child", 5)
        self.assert_result(screen, True, 4_299)


@pytest.mark.integration
class TestScenario13ThreeEligibleChildren(MoChipScenarioTestCase):
    """Three children, top tier for family size 5 ($363/mo), premium charged once."""

    screen_id = 13

    def test_family_of_five_three_children(self):
        screen = self.build(5)
        head = self.add_person(screen, 1, "headOfHousehold", 38)
        add_income(head, amount=5_500)
        spouse = self.add_person(screen, 2, "spouse", 36)
        add_income(spouse, amount=2_000)
        self.add_person(screen, 3, "child", 15)
        self.add_person(screen, 4, "child", 11)
        self.add_person(screen, 5, "child", 5)
        self.assert_result(screen, True, 4_379)


@pytest.mark.integration
class TestScenario14ChildInTheLastEligibleBirthYear(MoChipScenarioTestCase):
    """The eligible side of the under-19 gate; Scenario 7 covers the excluded side at 19.

    The spec states this child as born January 2008 rather than one month shy of their
    nineteenth birthday. The screener has no birth day, so a birth month at the boundary
    leaves the outcome turning on a day it cannot see; a January 2008 child reads 18 in
    every month of 2026 and is 17 at worst, both under 19. First tier ($25/mo).
    """

    screen_id = 14

    def test_eighteen_year_old_still_qualifies(self):
        screen = self.build(2)
        head = self.add_person(screen, 1, "headOfHousehold", 46)
        add_income(head, amount=3_000)
        self.add_person(screen, 2, "child", 18)
        self.assert_result(screen, True, 2_611)


@pytest.mark.integration
class TestScenario15aExactlyAtTheLowerBoundary(MoChipScenarioTestCase):
    """Exactly at Appendix A's HH3 ages-1-18 maximum: inclusive, so out of scope here."""

    screen_id = 15

    def test_exactly_at_the_lower_routing_boundary(self):
        screen = self.build(3)
        head = self.add_person(screen, 1, "headOfHousehold", 36)
        add_income(head, amount=3_484.00)
        self.add_person(screen, 2, "spouse", 33)
        self.add_person(screen, 3, "child", 10)
        self.assert_result(screen, False, 0)


@pytest.mark.integration
class TestScenario15bJustAboveTheLowerBoundary(MoChipScenarioTestCase):
    """Mirror of 15a, one dollar higher: a genuine premium-CHIP case ($32/mo tier)."""

    screen_id = 16

    def test_one_dollar_above_the_lower_routing_boundary(self):
        screen = self.build(3)
        head = self.add_person(screen, 1, "headOfHousehold", 36)
        add_income(head, amount=3_485.00)
        self.add_person(screen, 2, "spouse", 33)
        self.add_person(screen, 3, "child", 10)
        self.assert_result(screen, True, 2_527)


@pytest.mark.integration
class TestScenario17FamilySizeEight(MoChipScenarioTestCase):
    """The largest household the screener UI accepts. Six children, one premium
    ($214/mo), and the gross summed unrounded: 6 x $2,911.851 = $17,471.106."""

    screen_id = 17

    def test_six_children_at_family_size_eight(self):
        screen = self.build(8)
        head = self.add_person(screen, 1, "headOfHousehold", 41)
        add_income(head, amount=114_000, frequency="yearly")
        self.add_person(screen, 2, "spouse", 39)
        for offset, age in enumerate((3, 5, 7, 9, 11, 13), start=3):
            self.add_person(screen, offset, "child", age)
        self.assert_result(screen, True, 14_903)


@pytest.mark.integration
class TestScenario18ExactlyAtTheTierOneTwoCutoff(MoChipScenarioTestCase):
    """Appendix E publishes rounded monthly dollars; HH2's >150% band ends at $3,337.00.
    Exactly on the line stays in tier 1 ($25/mo)."""

    screen_id = 18

    def test_exactly_at_the_published_cutoff_stays_tier_one(self):
        screen = self.build(2)
        head = self.add_person(screen, 1, "headOfHousehold", 40)
        add_income(head, amount=3_337.00)
        self.add_person(screen, 2, "child", 10)
        self.assert_result(screen, True, 2_611)


@pytest.mark.integration
class TestScenario19JustIntoTierTwo(MoChipScenarioTestCase):
    """$3,337.01 is the published start of HH2's >185% band ($83/mo)."""

    screen_id = 19

    def test_one_dollar_above_the_cutoff_enters_tier_two(self):
        screen = self.build(2)
        head = self.add_person(screen, 1, "headOfHousehold", 40)
        add_income(head, amount=3_338.00)
        self.add_person(screen, 2, "child", 10)
        self.assert_result(screen, True, 1_915)


@pytest.mark.integration
class TestScenario20ExactlyAtTheTierTwoThreeCutoff(MoChipScenarioTestCase):
    """HH2's >185% band ends at $4,058.00. Exactly on the line stays in tier 2."""

    screen_id = 20

    def test_exactly_at_the_published_cutoff_stays_tier_two(self):
        screen = self.build(2)
        head = self.add_person(screen, 1, "headOfHousehold", 40)
        add_income(head, amount=4_058.00)
        self.add_person(screen, 2, "child", 10)
        self.assert_result(screen, True, 1_915)


@pytest.mark.integration
class TestScenario21JustIntoTheTopTier(MoChipScenarioTestCase):
    """$4,058.01 is the published start of HH2's >225% band ($203/mo)."""

    screen_id = 21

    def test_one_dollar_above_the_cutoff_enters_the_top_tier(self):
        screen = self.build(2)
        head = self.add_person(screen, 1, "headOfHousehold", 40)
        add_income(head, amount=4_059.00)
        self.add_person(screen, 2, "child", 10)
        self.assert_result(screen, True, 475)

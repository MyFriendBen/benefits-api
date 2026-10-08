"""
Spec-scenario tests for MO Supplemental Aid to the Blind — one test per Test Scenario in
``spec.md``.

``MoSab`` is a thin wrapper around PolicyEngine's ``mo_ssp``, so each of these runs the
scenario's household through PolicyEngine once and replays from a cassette, asserting the
eligibility verdict and the annual value ``MoSab`` reports.

Every scenario states a birth month and year; these tests state the age that month gives at
the run date the spec's Steps blocks were written for (``R`` = 2026-10) as a fixed integer, so
the request body, and so the cassette, does not drift with the calendar. Scenarios 5 and 6 are
the age-gate pair: 17 and exactly 18. The spec's offsets table is what to re-derive if their
meaning ever changes.

``mo_ssp`` is monthly and Missouri's figures turn over on July 1, so ``MoSab`` reads it at one
pinned month and multiplies by twelve. Every full-grant Expected here is $11,388 ($949 x 12);
read at the program year it would come back $192 low.
"""

from programs.programs.testing_fixtures.pe_integration import (
    PeIntegrationTestCase,
    add_income,
    add_member,
    calc_pe_program,
    make_program,
    make_screen,
    screener_value,
)
from programs.programs.white_labels.mo.sab.calculator import MoSab
from screener.models import WhiteLabel
from screener.serializers import _write_current_benefits
from screener.tests.helpers import seed_program

PE_VERSION = "2.18.0"

FULL_GRANT = 11_388  # ($949 - $0 SSI) x 12


class MoSabScenarioTestCase(PeIntegrationTestCase):
    """Shared builders. Every scenario is a Missouri screen with the claimant as member 1."""

    pe_version = PE_VERSION

    def screen(self, screen_id, household_size=1, assets=1_000, zipcode="65101", county="Cole County"):
        # make_screen creates the white label; make_program looks it up, so it has to run second.
        screen = make_screen(
            screen_id,
            white_label_code="mo",
            state_code="MO",
            household_size=household_size,
            zipcode=zipcode,
            county=county,
            household_assets=assets,
        )
        self.program = make_program("mo", "mo_sab", "2026")

        return screen

    def claimant(self, screen, age=40, blind=True, **kwargs):
        return add_member(screen, 1, "headOfHousehold", age, visually_impaired=blind, **kwargs)

    def run_sab(self, screen):
        return calc_pe_program(screen, MoSab, self.program)

    def assertEligible(self, eligibility, value):
        self.assertTrue(eligibility.eligible)
        self.assertEqual(screener_value(eligibility), value)

    def assertIneligible(self, eligibility):
        self.assertFalse(eligibility.eligible)
        self.assertEqual(screener_value(eligibility), 0)


class TestMoSabScenarios(MoSabScenarioTestCase):
    def test_scenario_1_ssi_plus_other_income_exceeds_the_standard(self):
        """SSI is excluded from the income test, not merely offset: ($949 - $500) x 12."""
        screen = self.screen(1)
        head = self.claimant(screen, disabled=False)
        add_income(head, 500, income_type="sSI")
        add_income(head, 700, income_type="pension")

        self.assertEligible(self.run_sab(screen), 5_388)

    def test_scenario_2_partial_ssi(self):
        """The grant is the difference between SSI received and $949."""
        screen = self.screen(2, zipcode="63101", county="St. Louis City")
        head = self.claimant(screen)
        add_income(head, 300, income_type="sSI")

        self.assertEligible(self.run_sab(screen), 7_788)

    def test_scenario_3_ssi_above_the_grant_ceiling(self):
        """$949 - $994 floors at zero, and a $0 program is not eligible."""
        screen = self.screen(3)
        head = self.claimant(screen)
        add_income(head, 994, income_type="sSI")

        self.assertIneligible(self.run_sab(screen))

    def test_scenario_4_not_blind(self):
        """SAB is a blindness program, not a disability program."""
        screen = self.screen(4)
        head = self.claimant(screen, blind=False, disabled=True)
        add_income(head, 500, income_type="pension")

        self.assertIneligible(self.run_sab(screen))

    def test_scenario_5_one_month_under_age_18(self):
        """Age 17 fails the gate, which also detects an omitted AgeDependency (PE defaults to 40)."""
        screen = self.screen(5, assets=500)
        head = self.claimant(screen, age=17)
        add_income(head, 300, income_type="pension")

        self.assertIneligible(self.run_sab(screen))

    def test_scenario_6_age_exactly_18(self):
        """The gate is inclusive at 18."""
        screen = self.screen(6, assets=500)
        head = self.claimant(screen, age=18)
        add_income(head, 300, income_type="pension")

        self.assertEligible(self.run_sab(screen), FULL_GRANT)

    def test_scenario_7_income_one_dollar_under_the_standard(self):
        """$12,864/year is $1,072/month, one dollar under the $1,073 Consolidated Standard."""
        screen = self.screen(7)
        head = self.claimant(screen)
        add_income(head, 12_864, income_type="pension", frequency="yearly")

        self.assertEligible(self.run_sab(screen), FULL_GRANT)

    def test_scenario_8_income_exactly_at_the_standard(self):
        """The test is exclusive: $1,073 leaves no remainder."""
        screen = self.screen(8)
        head = self.claimant(screen)
        add_income(head, 1_073, income_type="pension")

        self.assertIneligible(self.run_sab(screen))

    def test_scenario_9_married_couple_tests_the_applicants_own_income(self):
        """The couple's $1,800/month is over the standard; the applicant's own $500 is not."""
        screen = self.screen(9, household_size=2, assets=8_000, zipcode="63101", county="St. Louis City")
        head = self.claimant(screen)
        add_income(head, 500, income_type="pension")
        spouse = add_member(screen, 2, "spouse", 42, visually_impaired=False)
        add_income(spouse, 1_300, income_type="wages")

        eligibility = self.run_sab(screen)

        self.assertEligible(eligibility, FULL_GRANT)
        self.assertEqual([m.member.id for m in eligibility.eligible_members if m.eligible], [head.id])

    def test_scenario_10_resources_over_the_limit(self):
        """$10,000 exceeds the $6,220.50 individual limit."""
        screen = self.screen(10, assets=10_000)
        head = self.claimant(screen)
        add_income(head, 500, income_type="pension")

        self.assertIneligible(self.run_sab(screen))

    def test_scenario_11_two_blind_adults(self):
        """The grant is per eligible member: $11,388 each."""
        screen = self.screen(11, household_size=2, zipcode="63101", county="St. Louis City")
        head = self.claimant(screen)
        add_income(head, 500, income_type="pension")
        spouse = add_member(screen, 2, "spouse", 38, visually_impaired=True)
        add_income(spouse, 400, income_type="pension")

        self.assertEligible(self.run_sab(screen), 2 * FULL_GRANT)

    def test_scenario_12_earned_income_well_above_the_standard(self):
        """$4,000/month of wages stays over $1,073 after every published exemption."""
        screen = self.screen(12)
        head = self.claimant(screen)
        add_income(head, 4_000, income_type="wages")

        self.assertIneligible(self.run_sab(screen))

    def test_scenario_13_temporary_assistance_does_not_suppress(self):
        """TA and SAB are an election, not a bar, so reported TA must not gate the program."""
        screen = self.screen(13, household_size=2)
        head = self.claimant(screen)
        add_income(head, 400, income_type="pension")
        add_income(head, 400, income_type="cashAssistance")
        add_member(screen, 2, "child", 10, visually_impaired=False)
        seed_program(WhiteLabel.objects.get(code="mo"), "mo_tanf", base_program="tanf")
        _write_current_benefits(screen, ["mo_tanf"])
        screen.invalidate_current_benefits_cache()

        self.assertEligible(self.run_sab(screen), FULL_GRANT)

    def test_scenario_14_blind_adult_living_with_a_parent(self):
        """Unmarried, so the individual limit applies to her $8,000 share and denies."""
        screen = self.screen(14, household_size=2, assets=16_000)
        head = self.claimant(screen, age=60, blind=False)
        add_income(head, 3_000, income_type="wages")
        child = add_member(screen, 2, "child", 22, visually_impaired=True)
        add_income(child, 400, income_type="pension")

        self.assertIneligible(self.run_sab(screen))

    def test_scenario_15_boarder_income_is_earned(self):
        """$1,200/month of boarder income carries the earned-income exemptions."""
        screen = self.screen(15)
        head = self.claimant(screen)
        add_income(head, 1_200, income_type="boarder")

        self.assertEligible(self.run_sab(screen), FULL_GRANT)

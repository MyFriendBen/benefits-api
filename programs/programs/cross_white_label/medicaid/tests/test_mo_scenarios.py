"""
Smoke test for MO Medicaid — proves Missouri's ``medicaid`` pathway resolves end to end.

``MoHealthNet`` adds only Missouri's state code and the two disability inputs to the federal
``medicaid`` calculator, so the federal math is already covered by the other states' medicaid
tests and re-testing it per state would only duplicate them.

What this pins first is the one thing that is Missouri-specific and could silently break: that
Missouri is read as an ACA expansion state, so a childless adult under 138% FPL comes back
eligible in the ``ADULT`` category rather than $0. That is the distinction between MO and a
non-expansion state like Kansas, and it is the whole reason the MO state code is wired in.

The value asserted is KFF's ACA-expansion-adult rate, which is what PE's ``ADULT`` category
maps to in an expansion state, so this also catches a category mapped to the wrong rate.

``TestMoHealthNetValueRouting`` then covers the ``specs/mo.md`` scenarios where PolicyEngine's
routing and the member's own age/disability flags disagree — the four that production QA found
mis-valued. They run end to end so the assertion is against PolicyEngine's real answer rather
than a stub of it; the same four are pinned as stubbed unit tests in ``test_base.py``, which is
what keeps them covered when a cassette is re-recorded at a newer model version.

The remaining ``specs/mo.md`` scenarios exercise the shared federal MAGI math and are covered by
the other states' medicaid tests; they are not duplicated here.
"""

import math

import pytest

from programs.programs.cross_white_label.medicaid.mo import MoHealthNet
from programs.programs.testing_fixtures.pe_integration import (
    PeIntegrationTestCase,
    add_income,
    add_member,
    calc_pe_program,
    make_program,
    make_screen,
    screener_value,
)

PE_VERSION = "1.815.1"
YEAR = "2026"


@pytest.mark.integration
class TestMoHealthNetSmoke(PeIntegrationTestCase):
    """Cole County, ZIP 65101 — the same household shape MO PTS uses."""

    pe_version = PE_VERSION

    def test_expansion_adult_under_income_limit_is_eligible(self):
        """Childless adult at $1,200/month (~92% FPL) → eligible via ACA expansion.

        Missouri's adult limit is 138% FPL, so this household sits well inside it. A
        non-expansion state would return $0 for the same household.
        """
        screen = make_screen(
            screen_id=1,
            white_label_code="mo",
            state_code="MO",
            household_size=1,
            zipcode="65101",
            county="Cole County",
        )
        adult = add_member(screen, member_id=1, relationship="headOfHousehold", age=34)
        add_income(adult, amount=1_200)
        program = make_program("mo", "mo_medicaid", year=YEAR)

        eligibility = calc_pe_program(screen, MoHealthNet, program)

        self.assertTrue(eligibility.eligible)
        self.assertEqual(screener_value(eligibility), MoHealthNet.KFF_EXPANSION_ADULTS)

    def _member_values(self, eligibility):
        """Per-member values keyed by member id, so a scenario can assert each person."""
        return {me.member.id: math.trunc(me.value) for me in eligibility.eligible_members if me.eligible}

    def _parent_and_child(self, parent_monthly_wages):
        """HH2: a parent at the given monthly wage plus their 11-year-old child."""
        screen = make_screen(
            screen_id=2,
            white_label_code="mo",
            state_code="MO",
            household_size=2,
            zipcode="63101",
            county="St. Louis City",
        )
        parent = add_member(screen, member_id=1, relationship="headOfHousehold", age=36)
        add_income(parent, amount=parent_monthly_wages)
        add_member(screen, member_id=2, relationship="child", age=11)
        program = make_program("mo", "mo_medicaid", year=YEAR)

        return self._member_values(calc_pe_program(screen, MoHealthNet, program))

    def test_parent_at_the_mhf_standard_is_valued_as_a_mandatory_adult(self):
        """Parent at Missouri's flat MHF standard -> the non-expansion Adults rate.

        MHF is mandatory and takes precedence over adult expansion, so this parent must not
        be valued at the expansion rate even though their income also clears the much higher
        expansion ceiling.
        """
        values = self._parent_and_child(241)

        self.assertEqual(values[1], MoHealthNet.KFF_ADULTS)
        self.assertEqual(values[2], MoHealthNet.KFF_CHILDREN)

    def test_parent_one_dollar_over_the_mhf_standard_falls_through_to_expansion(self):
        """Parent one dollar over the flat MHF standard -> expansion, not denial.

        Their income is nowhere near the expansion ceiling, so failing MHF re-routes them to
        adult expansion rather than dropping them.
        """
        values = self._parent_and_child(242)

        self.assertEqual(values[1], MoHealthNet.KFF_EXPANSION_ADULTS)
        self.assertEqual(values[2], MoHealthNet.KFF_CHILDREN)


@pytest.mark.integration
class TestMoHealthNetValueRouting(PeIntegrationTestCase):
    """specs/mo.md scenarios where PE's category and the member's own flags disagree.

    Missouri's value-priority rule assigns the KFF group from the member's own facts, and PE's
    routing decides which pathway found them eligible. Each scenario below is a case where
    reading the aged/disabled pathway ahead of PE's category produced the wrong answer in
    production: either the disabled rate over an expansion one, or no answer at all.
    """

    pe_version = PE_VERSION

    def _single_adult(self, screen_id, age, income_type, monthly_amount, **flags):
        """One-person Cole County household, as Scenarios 6/19/21/24 describe it."""
        screen = make_screen(
            screen_id=screen_id,
            white_label_code="mo",
            state_code="MO",
            household_size=1,
            zipcode="65101",
            county="Cole County",
        )
        member = add_member(screen, member_id=1, relationship="headOfHousehold", age=age, **flags)
        add_income(member, amount=monthly_amount, income_type=income_type)
        program = make_program("mo", "mo_medicaid", year=YEAR)

        return calc_pe_program(screen, MoHealthNet, program)

    def test_scenario_6_disabled_adult_over_the_mhabd_standard_falls_through_to_expansion(self):
        """Scenario 6. Adjusted MHABD income $1,680 exceeds the $1,131 standard, so MHABD is
        only reachable via spend-down and PE routes them to expansion instead. Gross income is
        under the $1,836 HH1 expansion ceiling, so they must be shown the expansion value —
        production returned $0 and dropped the program from results entirely.
        """
        eligibility = self._single_adult(10, age=40, income_type="pension", monthly_amount=1_700, disabled=True)

        self.assertTrue(eligibility.eligible)
        self.assertEqual(screener_value(eligibility), MoHealthNet.KFF_EXPANSION_ADULTS)

    def test_scenario_19_disabled_adult_routed_to_expansion_keeps_the_expansion_value(self):
        """Scenario 19. Adjusted MHABD income $747 is under the standard, so the aged/disabled
        pathway does qualify — but PE still routes them to expansion, and PE's routing decides
        the group. Production applied the disabled rate, overstating by $22,965.
        """
        eligibility = self._single_adult(11, age=40, income_type="wages", monthly_amount=1_600, disabled=True)

        self.assertTrue(eligibility.eligible)
        self.assertEqual(screener_value(eligibility), MoHealthNet.KFF_EXPANSION_ADULTS)

    def test_scenario_21_blind_adult_at_the_mhabd_boundary_keeps_the_expansion_value(self):
        """Scenario 21. $1,350/mo pension leaves adjusted income at exactly the $1,330 blind
        non-spend-down standard, reaching the same routing as Scenario 19 through blindness
        rather than a disability flag.
        """
        eligibility = self._single_adult(
            12, age=46, income_type="pension", monthly_amount=1_350, visually_impaired=True
        )

        self.assertTrue(eligibility.eligible)
        self.assertEqual(screener_value(eligibility), MoHealthNet.KFF_EXPANSION_ADULTS)

    def test_scenario_24_disabled_senior_is_valued_at_the_seniors_rate(self):
        """Scenario 24. KFF defines Seniors as 65+ regardless of disability, so a disabled
        70-year-old on MHABD is a senior enrollee. Production applied the under-65 disabled
        rate, overstating by $8,553.
        """
        eligibility = self._single_adult(
            13, age=70, income_type="pension", monthly_amount=1_000, long_term_disability=True
        )

        self.assertTrue(eligibility.eligible)
        self.assertEqual(screener_value(eligibility), MoHealthNet.KFF_SENIORS)

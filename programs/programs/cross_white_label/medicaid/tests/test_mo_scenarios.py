"""
Smoke test for MO Medicaid — proves Missouri's ``medicaid`` pathway resolves end to end.

``MoHealthNet`` adds only Missouri's state code and the two disability inputs to the federal
``medicaid`` calculator, so the federal math is already covered by the other states' medicaid
tests and re-testing it per state would only duplicate them.

This file is a smoke test rather than the per-scenario suite the ``specs/mo.md`` scenarios call
for. Those scenarios exist and are not yet covered here.

What this does pin is the one thing that is Missouri-specific and could silently break: that
Missouri is read as an ACA expansion state, so a childless adult under 138% FPL comes back
eligible in the ``ADULT`` category rather than $0. That is the distinction between MO and a
non-expansion state like Kansas, and it is the whole reason the MO state code is wired in.

The value asserted is KFF's ACA-expansion-adult rate, which is what PE's ``ADULT`` category
maps to in an expansion state, so this also catches a category mapped to the wrong rate.
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

PE_VERSION = "1.794.2"
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
        """Parent at Missouri's flat $241/mo MHF standard -> the non-expansion Adults rate.

        MHF is a mandatory pre-expansion category and takes precedence over adult expansion,
        so this parent must not be valued at the higher expansion rate even though their
        income also clears the far higher expansion ceiling. Pairs with the $242 test below:
        together they are what makes categorical precedence observable in the result at all.
        """
        values = self._parent_and_child(241)

        self.assertEqual(values[1], MoHealthNet.KFF_ADULTS)
        self.assertEqual(values[2], MoHealthNet.KFF_CHILDREN)

    def test_parent_one_dollar_over_the_mhf_standard_falls_through_to_expansion(self):
        """Parent one dollar over the flat MHF standard -> expansion, not denial.

        $242/mo is nowhere near the expansion ceiling, so failing MHF re-routes them to
        adult expansion at KFF's higher expansion rate rather than dropping them.
        """
        values = self._parent_and_child(242)

        self.assertEqual(values[1], MoHealthNet.KFF_EXPANSION_ADULTS)
        self.assertEqual(values[2], MoHealthNet.KFF_CHILDREN)

"""
Smoke test for MO Medicaid — proves Missouri's ``medicaid`` pathway resolves end to end.

MO HealthNet is a Fed-tier passthrough: ``MoHealthNet`` adds only Missouri's state code to
the federal ``medicaid`` calculator, so there is no ``spec.md`` and no per-scenario suite
here. The federal math is already covered by the other states' medicaid tests; re-testing
it per state would only duplicate them.

What this does pin is the one thing that is Missouri-specific and could silently break: that
Missouri is read as an ACA expansion state, so a childless adult under 138% FPL comes back
eligible in the ``ADULT`` category rather than $0. That is the distinction between MO and a
non-expansion state like Kansas, and it is the whole reason the MO state code is wired in.

The value asserted is the KFF per-enrollee ``ADULT`` rate × 12, so this also catches a
category the calculator maps to the wrong rate.
"""

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
        self.assertEqual(screener_value(eligibility), 6_384)

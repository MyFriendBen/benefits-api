"""
Smoke test for MO SNAP.

Missouri is a federal passthrough: ``MoSnap`` adds the state code and nothing else, so the
eligibility rules and the benefit amount are PolicyEngine's federal SNAP calculator running
against Missouri's state-keyed parameters. Federal SNAP math is already covered by the
shared base and the other states' suites, so this does not re-test it per state — it proves
one thing, which is the thing a new state can actually get wrong: that ``snap_if_takes_up``
resolves for a Missouri household and comes back with a benefit.

Asserted in **annual** dollars, which is what the screener reports (``estimated_value``);
``Snap.household_value`` multiplies PolicyEngine's monthly figure by 12.
"""

import pytest

from programs.programs.cross_white_label.snap.mo import MoSnap
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
class TestMoSnapResolves(PeIntegrationTestCase):
    """A Missouri household PolicyEngine should find eligible comes back with a benefit."""

    pe_version = PE_VERSION

    def test_single_parent_two_children_under_the_income_limit(self):
        """Three-person St. Louis City household on $1,500/month in wages.

        Well under Missouri's 130% FPL gross-income limit for a household of three, with no
        assets, so the ordinary pathway applies — Missouri did not adopt BBCE, and nothing
        here is categorically eligible.
        """
        screen = make_screen(
            1,
            white_label_code="mo",
            state_code="MO",
            household_size=3,
            zipcode="63101",
            county="St. Louis City",
        )
        parent = add_member(screen, 1, "headOfHousehold", 34)
        add_income(parent, amount=1_500)
        add_member(screen, 2, "child", 7)
        add_member(screen, 3, "child", 4)
        program = make_program("mo", "mo_snap", YEAR)

        eligibility = calc_pe_program(screen, MoSnap, program)

        self.assertTrue(eligibility.eligible)
        # $487/month. Missouri's FY2026 three-person max allotment less 30% of net income:
        # $1,500 gross, less the 20% earned-income deduction and the household-of-three
        # standard deduction, leaves ~$992 net. Asserted exactly so a re-record at a newer
        # PolicyEngine version surfaces a value change instead of passing on any nonzero
        # number. `household_value` truncates the monthly figure before annualizing it.
        self.assertEqual(screener_value(eligibility), 487 * 12)

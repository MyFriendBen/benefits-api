"""Harness test for the PolicyEngine spec-scenario helpers.

This validates the record/replay machinery itself — explicit primary keys, the pinned
version, the pre-seeded token, and the body matcher in conftest — using one household as its
subject. A program's own spec-scenario tests live next to the program
(``programs/programs/{state}/{program}/tests/``), not here.

If this test fails to replay, the harness is broken; see docs/TESTING.md.
"""

import pytest

from ...tx.pe.member import TxHeadStart
from .spec_scenarios import (
    PeSpecScenarioTestCase,
    add_income,
    add_member,
    calc_pe_program,
    make_program,
    make_screen,
    screener_value,
)


@pytest.mark.integration
class TestPeSpecScenarioHarness(PeSpecScenarioTestCase):
    pe_version = "1.779.3"

    def test_replays_a_member_level_program_from_a_cassette(self):
        """One household, one POST, one cassette: a 3-year-old under the income limit.

        Member-level on purpose — the response is keyed by household member id, so this is
        what proves the explicit-pk rule actually makes a cassette replayable.
        """
        screen = make_screen(
            screen_id=1,
            white_label_code="tx",
            state_code="TX",
            household_size=2,
            zipcode="78701",
            county="Travis County",
        )
        parent = add_member(screen, member_id=1, relationship="headOfHousehold", age=34)
        add_income(parent, amount=1_496)
        add_member(screen, member_id=2, relationship="child", age=3)

        program = make_program("tx", "tx_head_start", year="2025")

        eligibility = calc_pe_program(screen, TxHeadStart, program)

        self.assertTrue(eligibility.eligible)
        self.assertEqual(screener_value(eligibility), 12_076)

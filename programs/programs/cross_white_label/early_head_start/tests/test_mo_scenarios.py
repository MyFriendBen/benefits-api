"""
Receipt-contract regression scenarios for MO Early Head Start — one test per Test Scenario
in ``specs/mo.md``.

The Head Start suite's module docstring
(``cross_white_label/head_start/tests/test_mo_scenarios.py``) explains the contract and the
income band these scenarios depend on; both suites run the same Missouri household and
differ only in which calculator reads it. Kept as two suites rather than one because a
cassette records one calculator's payload, and ``mo_early_head_start`` sends a
``PregnancyDependency`` that ``mo_head_start`` does not.

In short: $2,600/month is above ``spm_unit_fpg`` ($27,320 for this household of three), so
Early Head Start's ordinary income pathway is closed, and below Missouri SNAP's
simulated-eligibility ceiling, so PolicyEngine still returns a would-be SNAP benefit the
receipt contract has to suppress for a non-reporter. Moving the income out of that band
makes the negative scenario pass for the wrong reason.
"""

import pytest

from programs.programs.cross_white_label.early_head_start.mo import MoEarlyHeadStart
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

PE_VERSION = "1.821.2"
YEAR = "2026"

# See the Head Start suite: above the Head Start/EHS income test, below MO SNAP's ceiling.
MONTHLY_WAGES = 2_600

# PolicyEngine's per-participant Missouri EHS figure is $19,616.668; the screener truncates.
MO_PER_PARTICIPANT_VALUE = 19_616


class MoEarlyHeadStartReceiptTestCase(PeIntegrationTestCase):
    """Shared household builder — the same one the Head Start suite uses."""

    pe_version = PE_VERSION

    # Distinct per subclass so each scenario's cassette pins its own household.
    screen_id = 0

    def build(self, reports_snap):
        # make_screen creates the white label; make_program looks it up, so it has to run
        # second.
        screen = make_screen(
            self.screen_id,
            white_label_code="mo",
            state_code="MO",
            household_size=3,
            zipcode="65101",
            county="Cole County",
        )
        self.program = make_program("mo", "mo_early_head_start", YEAR)

        adult = self.add_person(screen, 1, "headOfHousehold", 30)
        add_income(adult, MONTHLY_WAGES)
        # The 4-year-old is Head Start's participant, not EHS's, and is kept so both suites
        # describe one household. Only the 1-year-old can be an EHS participant here, which
        # is what makes the expected value the single-participant figure.
        self.add_person(screen, 2, "child", 4)
        self.add_person(screen, 3, "child", 1)

        if reports_snap:
            # `screen_reports_snap` resolves the tile through `has_base_benefit`, so the row
            # needs `base_program="snap"` rather than a literal name.
            seed_program(screen.white_label, "mo_snap_current", base_program="snap")
            _write_current_benefits(screen, ["mo_snap_current"])
            screen.invalidate_current_benefits_cache()

        return screen

    def add_person(self, screen, offset, relationship, age):
        """A member at a fixed age — VCR matches the request body exactly, so an age derived
        from the wall clock would break the suite on a calendar boundary."""
        return add_member(screen, self.screen_id * 100 + offset, relationship, age)

    def assert_result(self, screen, expected_eligible, expected_annual_value):
        result = calc_pe_program(screen, MoEarlyHeadStart, self.program)
        self.assertEqual(
            (bool(result.eligible), screener_value(result)),
            (expected_eligible, expected_annual_value),
        )


@pytest.mark.integration
class TestScenarioSnapNotReported(MoEarlyHeadStartReceiptTestCase):
    """Simulated SNAP eligibility alone must not confer Early Head Start eligibility."""

    screen_id = 3

    def test_income_above_the_test_and_no_reported_snap_is_ineligible(self):
        """PolicyEngine would pay this household $2,765/year of SNAP, but it reports none.
        The receipt contract suppresses that would-be benefit, so the categorical pathway is
        shut and the income pathway is already closed at $31,200 — the under-3 child is not
        an eligible participant.

        Before #1685 the same household was found eligible for $19,616.
        """
        screen = self.build(reports_snap=False)
        self.assert_result(screen, False, 0)


@pytest.mark.integration
class TestScenarioSnapReported(MoEarlyHeadStartReceiptTestCase):
    """Reported SNAP receipt confers Early Head Start eligibility above the income test."""

    screen_id = 4

    def test_reported_snap_qualifies_the_participant_categorically(self):
        """Identical household, SNAP ticked on the Current Benefits tile. One participant —
        the under-3 child — so this also re-pins Missouri's per-participant value.
        """
        screen = self.build(reports_snap=True)
        self.assert_result(screen, True, MO_PER_PARTICIPANT_VALUE)

"""Harness test for the PolicyEngine integration-test helpers.

This validates the record/replay machinery itself — explicit primary keys, the pinned
version, the pre-seeded token, and the body matcher in conftest — using one household as its
subject. A program's own PolicyEngine tests live next to the program
(``programs/programs/{state}/{program}/tests/``), not here.

If this test fails to replay, the harness is broken; see docs/TESTING.md.

One caveat when it *does* fail: the subject is a real calculator, ``TxHeadStart``, which
inherits its inputs from the federal ``HeadStart``. Adding an input there changes the request
body and so breaks this test with a body mismatch — that is a signal about the calculator
change, not about the harness. Re-record after reviewing the new body.
"""

import pytest
from django.test import SimpleTestCase, TestCase

from programs.programs.testing_fixtures.pe_integration import (
    PE_TEST_VERSION,
    PeIntegrationTestCase,
    check_pe_version_pin,
    check_program_vintage,
    add_income,
    add_member,
    calc_pe_program,
    make_program,
    make_screen,
    screener_value,
)
from programs.programs.cross_white_label.head_start.tx import TxHeadStart

PE_VERSION = "1.786.5"
PE_VERSION_REASON = (
    "Recorded before the suite-wide pin. Remove PE_VERSION and this reason once the module is "
    "re-recorded at PE_TEST_VERSION."
)


@pytest.mark.integration
class TestPeIntegrationHarness(PeIntegrationTestCase):
    # The asserted value has held across 1.779.3 → 1.784.3 → 1.786.5.
    pe_version = PE_VERSION
    pe_version_reason = PE_VERSION_REASON

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


class TestCheckPeVersionPin(SimpleTestCase):
    """A module may sit behind the suite pin, but only with a stated reason."""

    def test_the_suite_pin_needs_no_reason(self) -> None:
        check_pe_version_pin("TestSomething", PE_TEST_VERSION, "")

    def test_an_override_with_a_reason_passes(self) -> None:
        check_pe_version_pin("TestSomething", "1.0.0", "recorded before the suite-wide pin")

    def test_an_override_without_a_reason_fails(self) -> None:
        with self.assertRaisesMessage(AssertionError, "Set pe_version_reason"):
            check_pe_version_pin("TestSomething", "1.0.0", "  ")

    def test_an_empty_pin_fails(self) -> None:
        with self.assertRaisesMessage(AssertionError, "must set pe_version"):
            check_pe_version_pin("TestSomething", "", "")

    def test_the_default_pin_is_the_suite_pin(self) -> None:
        self.assertEqual(PeIntegrationTestCase.pe_version, PE_TEST_VERSION)


class TestCheckProgramVintage(TestCase):
    """A scenario runs at the edition programs/vintage.py records, unless it says why not."""

    def test_the_recorded_edition_passes(self) -> None:
        check_program_vintage(make_program("mo", "mo_pts", year="2025", state_code="MO"))

    def test_another_year_fails(self) -> None:
        program = make_program("mo", "mo_pts", year="2026", state_code="MO")

        with self.assertRaisesMessage(AssertionError, "programs/vintage.py records 2025"):
            check_program_vintage(program)

    def test_another_year_with_a_reason_passes(self) -> None:
        check_program_vintage(make_program("mo", "mo_pts", year="2026", state_code="MO"), "year-parameter guard")

    def test_a_program_with_no_recorded_vintage_is_not_checked(self) -> None:
        check_program_vintage(make_program("mo", "not_in_vintage", year="1999", state_code="MO"))

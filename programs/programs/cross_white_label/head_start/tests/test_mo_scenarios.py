"""
Receipt-contract regression scenarios for MO Head Start — one test per Test Scenario in
``specs/mo.md``.

``head_start`` is categorically eligible for a household receiving SNAP, TANF or SSI. Since
PR #1685 that means *reported* receipt: ``receives_snap`` and its take-up siblings, not a
SNAP amount PolicyEngine simulated the household as eligible for. These two scenarios pin
that distinction end to end, because it is the one thing about Head Start that has already
regressed once and that no wiring test can catch — ``pe_inputs`` can list every receipt
dependency while PolicyEngine still answers from simulated eligibility.

Both scenarios are the same Missouri household, changing only whether SNAP is reported. The
$2,600/month income is load-bearing and deliberately narrow:

* $31,200/year is **above** ``spm_unit_fpg`` ($27,320 for this household of three), so Head
  Start's ordinary income pathway is closed and categorical eligibility is the only way in;
* it is **below** Missouri SNAP's simulated-eligibility ceiling, so PolicyEngine still
  returns ``is_snap_eligible = True`` and ``snap_if_takes_up = $2,765.17`` for the
  non-reporter — a would-be benefit the receipt contract has to suppress.

Raise the income and the negative case starts passing for the wrong reason: PolicyEngine
stops simulating SNAP at all, so $0 proves nothing about receipt versus simulation. Anyone
adjusting these households has to keep them inside that band.

Verified against pre-#1685 behavior at the recorded version: stripping the receipt/take-up
inputs from the payload and leaving everything else alone makes the non-reporter eligible
for $16,314 again. So the negative scenario fails if that contract is ever undone.
"""

import pytest

from programs.programs.cross_white_label.head_start.mo import MoHeadStart
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

# Above spm_unit_fpg ($27,320 for a household of three), below MO SNAP's simulated ceiling.
# See the module docstring — this is the band the scenarios depend on.
MONTHLY_WAGES = 2_600

# PolicyEngine's per-child Missouri Head Start figure is $16,314.723; the screener truncates.
MO_PER_CHILD_VALUE = 16_314


class MoHeadStartReceiptTestCase(PeIntegrationTestCase):
    """Shared household builder. Jefferson City, ZIP 65101, matching the spec's other
    scenarios: Head Start's value is state-keyed, so the county is presentation only."""

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
        self.program = make_program("mo", "mo_head_start", YEAR)

        adult = self.add_person(screen, 1, "headOfHousehold", 30)
        add_income(adult, MONTHLY_WAGES)
        # One child in the Head Start band (3-5) and one under 3. The under-3 child is not
        # Head Start eligible at any income and is here so a single household serves both
        # this suite and the Early Head Start one, which asserts on the same two scenarios.
        self.add_person(screen, 2, "child", 4)
        self.add_person(screen, 3, "child", 1)

        if reports_snap:
            # The Current Benefits tile is the only SNAP signal the screener captures --
            # there is no reported amount -- and `screen_reports_snap` resolves it through
            # `has_base_benefit`, so the row needs `base_program="snap"` rather than a
            # literal name.
            seed_program(screen.white_label, "mo_snap_current", base_program="snap")
            _write_current_benefits(screen, ["mo_snap_current"])
            screen.invalidate_current_benefits_cache()

        return screen

    def add_person(self, screen, offset, relationship, age):
        """A member at a fixed age.

        Ages are stated outright rather than derived from a birth year: VCR matches on the
        exact request body, so an age that moved with the wall clock would break the whole
        suite on a calendar boundary.
        """
        return add_member(screen, self.screen_id * 100 + offset, relationship, age)

    def assert_result(self, screen, expected_eligible, expected_annual_value):
        result = calc_pe_program(screen, MoHeadStart, self.program)
        self.assertEqual(
            (bool(result.eligible), screener_value(result)),
            (expected_eligible, expected_annual_value),
        )


@pytest.mark.integration
class TestScenarioSnapNotReported(MoHeadStartReceiptTestCase):
    """Simulated SNAP eligibility alone must not confer Head Start eligibility."""

    screen_id = 1

    def test_income_above_the_test_and_no_reported_snap_is_ineligible(self):
        """PolicyEngine finds this household SNAP-eligible and would pay it $2,765/year, but
        the household reports no SNAP. Under the actual-receipt contract that would-be
        benefit is suppressed, so nothing satisfies Head Start's categorical test and the
        income pathway is already closed at $31,200.

        This is the case that regressed before #1685: the same household was told it
        qualified for $16,314 of Head Start on the strength of a SNAP benefit it was not
        receiving.
        """
        screen = self.build(reports_snap=False)
        self.assert_result(screen, False, 0)


@pytest.mark.integration
class TestScenarioSnapReported(MoHeadStartReceiptTestCase):
    """Reported SNAP receipt confers Head Start eligibility above the income test."""

    screen_id = 2

    def test_reported_snap_qualifies_the_child_categorically(self):
        """Identical household, SNAP ticked on the Current Benefits tile. Receipt satisfies
        the categorical test on its own, so the age-eligible child qualifies despite income
        above ``spm_unit_fpg`` — the positive half of the contract, asserted alongside the
        negative one so a change that simply denies everyone cannot pass this suite.
        """
        screen = self.build(reports_snap=True)
        self.assert_result(screen, True, MO_PER_CHILD_VALUE)

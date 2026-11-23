"""
Cassette-backed scenarios for NC Work First.

``NcTanf`` sends each member's earned income and our own unearned total, and reads PolicyEngine's
``nc_tanf``. PE derives NC's countable earned income itself, and since 2.74.1 that applies three rules
these tests pin: 27.5% of gross earnings is excluded, children's earnings are not counted, and a family
whose payment falls under $25 a month is not eligible. PE applies none of them if ``NcTanf`` sends
``nc_tanf_countable_earned_income``, so a regression that adds that input fails here. Sending the
unearned total must not switch the exclusions off either; the earnings scenarios below would fail if it did.

There is no NC TANF spec yet (it comes with the move off PolicyEngine), so the expected values
are worked from PE's NC parameters, not from a spec:

* need standard, monthly: size 2 = $472; the payment is 50% of (need standard − countable income)
* earned-income exclusion 27.5%; the minimum monthly payment is $25
* annual figures, as the screener reports them: size 2 need standard = $472 × 12 = $5,664

Every household is a parent and one child, size 2. The cassettes are recorded at the suite pin
(``PE_TEST_VERSION``), which must be 2.74.1 or later for the exclusions to exist.

Recording: ``PE_RECORD=1 VCR_MODE=once venv/bin/pytest programs/programs/cross_white_label/tanf/tests/test_nc_scenarios.py``
"""

import pytest

from programs.programs.cross_white_label.tanf.nc import NcTanf
from programs.programs.testing_fixtures.pe_integration import (
    PeIntegrationTestCase,
    add_income,
    add_member,
    calc_pe_program,
    make_program,
    make_screen,
    screener_value,
)

YEAR = "2026"


class NcTanfScenarioTestCase(PeIntegrationTestCase):
    # Cassette identity: seeds the member ids in the recorded request body. Distinct per subclass.
    screen_id = 0

    def build(self, parent_age=30, child_age=8):
        screen = make_screen(
            self.screen_id,
            white_label_code="nc",
            state_code="NC",
            household_size=2,
            zipcode="27601",
            county="Wake County",
        )
        self.program = make_program("nc", "nc_tanf", YEAR)
        parent = add_member(screen, self.screen_id * 100 + 1, "headOfHousehold", parent_age)
        child = add_member(screen, self.screen_id * 100 + 2, "child", child_age)
        return screen, parent, child

    def assert_result(self, screen, expected_eligible, expected_annual_value):
        result = calc_pe_program(screen, NcTanf, self.program)
        self.assertEqual(
            (bool(result.eligible), screener_value(result)),
            (expected_eligible, expected_annual_value),
        )


@pytest.mark.integration
class TestNoIncomeBaseline(NcTanfScenarioTestCase):
    """Baseline, no income → half the $5,664 need standard."""

    screen_id = 1

    def test_parent_and_child_no_income(self):
        screen, _, _ = self.build()
        self.assert_result(screen, True, 2_832)


@pytest.mark.integration
class TestEarnedIncomeExclusion(NcTanfScenarioTestCase):
    """27.5% of gross earnings is excluded.

    Parent earns $400/month = $4,800/year. Countable = 4,800 × 0.725 = $3,480, so the payment is
    (5,664 − 3,480) × 0.5 = $1,092. With the aggregates sent (no exclusion) it would be
    (5,664 − 4,800) × 0.5 = $432.
    """

    screen_id = 2

    def test_twenty_seven_point_five_percent_of_earnings_excluded(self):
        screen, parent, _ = self.build()
        add_income(parent, 400, "wages", "monthly")
        self.assert_result(screen, True, 1_092)


@pytest.mark.integration
class TestChildEarningsExcluded(NcTanfScenarioTestCase):
    """A child's earnings are not counted.

    Child, 16, earns $500/month; the parent has no income. Countable income is $0, so the payment
    is the same $2,832 as the baseline. If the child's earnings counted it would be
    (5,664 − 6,000 × 0.725) × 0.5 = $657.
    """

    screen_id = 3

    def test_sixteen_year_old_earnings_not_counted(self):
        screen, _, child = self.build(child_age=16)
        add_income(child, 500, "wages", "monthly")
        self.assert_result(screen, True, 2_832)


@pytest.mark.integration
class TestMinimumPaymentJustMet(NcTanfScenarioTestCase):
    """Payment of $25.03/month clears the $25 minimum.

    Parent earns $582/month = $6,984/year. Countable = 6,984 × 0.725 = $5,063.40, so the payment
    is (5,664 − 5,063.40) × 0.5 = $300.30/year, i.e. $25.03/month.
    """

    screen_id = 4

    def test_payment_just_over_twenty_five_dollars(self):
        screen, parent, _ = self.build()
        add_income(parent, 582, "wages", "monthly")
        self.assert_result(screen, True, 300)


@pytest.mark.integration
class TestMinimumPaymentNotMet(NcTanfScenarioTestCase):
    """Payment of $24.66/month is under the $25 minimum, so the family is not eligible.

    Parent earns $583/month = $6,996/year. Countable = 6,996 × 0.725 = $5,072.10, so the payment
    would be (5,664 − 5,072.10) × 0.5 = $295.95/year, i.e. $24.66/month. PE returns no payment
    (``nc_tanf`` is only defined for eligible units).
    """

    screen_id = 5

    def test_payment_just_under_twenty_five_dollars(self):
        screen, parent, _ = self.build()
        add_income(parent, 583, "wages", "monthly")
        self.assert_result(screen, False, 0)


@pytest.mark.integration
class TestChildSupportCounts(NcTanfScenarioTestCase):
    """Child support received counts in full as unearned income (no exclusion).

    Parent receives $100/month = $1,200/year. Payment = (5,664 − 1,200) × 0.5 = $2,232.
    """

    screen_id = 6

    def test_child_support_received_counted(self):
        screen, parent, _ = self.build()
        add_income(parent, 100, "childSupport", "monthly")
        self.assert_result(screen, True, 2_232)

"""
PolicyEngine tests for MA CCFA, configured as ``ma_ccdf``.

The program had no test coverage while it read the federal CCDF passthrough. These pin
the Massachusetts model that replaced it: the 85%-of-SMI income test, the $1M asset
limit, the child age thresholds, the activity test as our inputs actually populate it,
and the four tiers of the age-based value table.

Eligibility comes from PolicyEngine and the value is ours, so every scenario runs the
household through PolicyEngine once and replays from a cassette.

Massachusetts applies two age limits, and both have tests of their own rather than a
comment: 13 for a child in general (``TestChildAgeThreshold``) and 16 for a child with a
diagnosed special need (``TestDisabledChildAgeThreshold``), which is the only way to
reach the top of the age table.
"""

from programs.framework.base import PaymentUnit
from programs.programs.cross_white_label.ccdf.ma import MaCcdf
from programs.programs.testing_fixtures.pe_integration import (
    PeIntegrationTestCase,
    add_income,
    add_member,
    calc_pe_program,
    make_program,
    make_screen,
    screener_value,
)
from programs.programs.testing_fixtures.households import birth_year_month_for_age

PE_VERSION = "2.116.16"
PE_VERSION_REASON = (
    "Recorded at PolicyEngine frontier when Social Security, SSI and child support were dropped from "
    "the inputs, since frontier is the version PolicyEngine promotes to current next. Remove "
    "PE_VERSION and this reason once PE_TEST_VERSION reaches 2.116.16."
)

#: The period ``ma_ccdf`` is configured for. It decides which CCFA income limit applies:
#: PolicyEngine holds the new-applicant limit at 50% of SMI before 2026-01-01 and 85%
#: from it, and screening asks the new-applicant question.
YEAR = "2026"


class MaCcfaTestCase(PeIntegrationTestCase):
    """Shared household builder. Every scenario is Suffolk County, ZIP 02108."""

    pe_version = PE_VERSION
    pe_version_reason = PE_VERSION_REASON

    # Distinct per subclass so each scenario's cassette pins its own household.
    screen_id = 0

    def build(self, household_size, household_assets=0):
        # make_screen creates the white label; make_program looks it up, so it
        # has to run second.
        screen = make_screen(
            self.screen_id,
            white_label_code="ma",
            state_code="MA",
            household_size=household_size,
            zipcode="02108",
            county="Suffolk County",
            household_assets=household_assets,
        )
        self.program = make_program("ma", "ma_ccdf", YEAR)
        return screen

    def add_parent(self, screen, wages=30_000, income_type="wages", age=35, **kwargs):
        parent = add_member(screen, self.screen_id * 10 + 1, "headOfHousehold", age, **kwargs)
        if wages:
            add_income(parent, wages, income_type, "yearly")
        return parent

    def add_child(self, screen, age, offset=2, **kwargs):
        return add_member(screen, self.screen_id * 10 + offset, "child", age, **kwargs)

    def run_ccfa(self, screen):
        return calc_pe_program(screen, MaCcdf, self.program)


class TestValueByAge(MaCcfaTestCase):
    """The age table pays four tiers, and only for a child PolicyEngine can claim."""

    screen_id = 7301

    def test_infant_under_two(self):
        screen = self.build(2)
        self.add_parent(screen)
        self.add_child(screen, 1)
        result = self.run_ccfa(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(screener_value(result), 23_191)

    def test_toddler_under_three(self):
        screen = self.build(2)
        self.add_parent(screen)
        self.add_child(screen, 2)
        result = self.run_ccfa(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(screener_value(result), 21_125)

    def test_preschooler_under_four_and_a_half(self):
        """A stated age with no birth month is read as exactly 4.0.

        The screener always sends a birth month, so production prices a four-year-old by
        their fractional age instead. The two tests below cover that, one either side of
        the 4.5 split.
        """
        screen = self.build(2)
        self.add_parent(screen)
        self.add_child(screen, 4)
        result = self.run_ccfa(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(screener_value(result), 16_572)

    def test_four_and_two_months_is_paid_the_preschool_rate(self) -> None:
        self.assert_four_year_old_paid(months_past_fourth_birthday=2, cost=16_572)

    def test_four_and_eight_months_is_paid_the_school_age_rate(self) -> None:
        """Still stated as age 4, but past the 4.5 split, so a tier lower."""
        self.assert_four_year_old_paid(months_past_fourth_birthday=8, cost=12_632)

    def assert_four_year_old_paid(self, months_past_fourth_birthday: int, cost: int) -> None:
        """Price a child the screener reports as 4, who turned 4 ``months_past_fourth_birthday`` months ago.

        The birth month is counted back from the screening date rather than fixed, so
        ``calc_age()`` reads 4 whenever the suite runs: PolicyEngine is sent the same age
        and the cassette keeps matching. Only ``fraction_age()``, which prices the child,
        sees the extra months.
        """
        screen = self.build(2)
        self.add_parent(screen)
        birth_year_month = birth_year_month_for_age(4 + months_past_fourth_birthday / 12, screen.get_reference_date())
        child = self.add_child(screen, 4, birth_year_month=birth_year_month)
        self.assertEqual(child.calc_age(), 4)
        result = self.run_ccfa(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(screener_value(result), cost)

    def test_school_age(self):
        screen = self.build(2)
        self.add_parent(screen)
        self.add_child(screen, 10)
        result = self.run_ccfa(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(screener_value(result), 12_632)

    def test_two_children_are_paid_separately(self):
        """The unit boolean gates; the per-child boolean picks who is paid. So the children,
        not the household, are the eligible party, whatever the SPM base says."""
        screen = self.build(3)
        self.add_parent(screen)
        self.add_child(screen, 1, offset=2)
        self.add_child(screen, 10, offset=3)
        result = self.run_ccfa(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(screener_value(result), 23_191 + 12_632)
        self.assertEqual(result.payment_unit, PaymentUnit.MEMBER)
        self.assertEqual(result.household_value, 0)
        self.assertEqual([m.value for m in result.eligible_members], [0, 23_191, 12_632])


class TestIncomeLimit(MaCcfaTestCase):
    """85% of state median income, the same share the federal test applied."""

    screen_id = 7302

    def test_just_under_the_limit(self):
        screen = self.build(2)
        self.add_parent(screen, wages=95_000)
        self.add_child(screen, 4)
        result = self.run_ccfa(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(screener_value(result), 16_572)

    def test_just_over_the_limit(self):
        screen = self.build(2)
        self.add_parent(screen, wages=96_000)
        self.add_child(screen, 4)
        result = self.run_ccfa(screen)
        self.assertFalse(result.eligible)
        self.assertEqual(screener_value(result), 0)

    def test_benefit_income_counts(self):
        """CCFA counts benefit income; the federal CCDF test this replaced did not.

        The federal gate read ``market_income``, which carried none of the benefit
        streams, so a household living on them read as having no income at all. CCFA
        names its own sources and unemployment compensation is one of them.

        Not Social Security: Massachusetts stopped counting it for CCFA, so it isn't sent.
        """
        screen = self.build(2)
        self.add_parent(screen, wages=96_000, income_type="unemployment")
        self.add_child(screen, 4)
        result = self.run_ccfa(screen)
        self.assertFalse(result.eligible)
        self.assertEqual(screener_value(result), 0)


class TestAssetLimit(MaCcfaTestCase):
    """$1,000,000, asserted either side rather than on it.

    PolicyEngine has allowed a household holding exactly $1,000,000 since 2.5.0 (measured
    again at 2.94.7 and 2.116.16); versions before it denied one. These two sit above and
    below the limit, where every version agrees.
    """

    screen_id = 7303

    def test_just_under_the_limit(self):
        screen = self.build(2, household_assets=999_999)
        self.add_parent(screen)
        self.add_child(screen, 4)
        result = self.run_ccfa(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(screener_value(result), 16_572)

    def test_just_over_the_limit(self):
        screen = self.build(2, household_assets=1_000_001)
        self.add_parent(screen)
        self.add_child(screen, 4)
        result = self.run_ccfa(screen)
        self.assertFalse(result.eligible)
        self.assertEqual(screener_value(result), 0)


class TestChildAgeThreshold(MaCcfaTestCase):
    """Under 13 for a child with no diagnosed special need."""

    screen_id = 7304

    def test_twelve_is_eligible(self):
        screen = self.build(2)
        self.add_parent(screen)
        self.add_child(screen, 12)
        result = self.run_ccfa(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(screener_value(result), 12_632)

    def test_thirteen_is_not(self):
        screen = self.build(2)
        self.add_parent(screen)
        self.add_child(screen, 13)
        result = self.run_ccfa(screen)
        self.assertFalse(result.eligible)
        self.assertEqual(screener_value(result), 0)


class TestDisabledChildAgeThreshold(MaCcfaTestCase):
    """Under 16 when the child has a diagnosed special need.

    Ages 13 to 15 are the only ones that reach the school-age tier, since the general
    limit already stops everyone else at 13. Both ends of that range are pinned here.
    """

    screen_id = 7305

    def test_disabled_thirteen_year_old_is_paid(self):
        """The age the general limit turns away, kept by the disability limit."""
        screen = self.build(2)
        self.add_parent(screen)
        self.add_child(screen, 13, disabled=True)
        result = self.run_ccfa(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(screener_value(result), 12_632)

    def test_disabled_fifteen_year_old_is_paid(self):
        screen = self.build(2)
        self.add_parent(screen)
        self.add_child(screen, 15, disabled=True)
        result = self.run_ccfa(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(screener_value(result), 12_632)

    def test_disabled_fifteen_year_old_is_paid_alongside_a_sibling(self):
        screen = self.build(3)
        self.add_parent(screen)
        self.add_child(screen, 15, offset=2, disabled=True)
        self.add_child(screen, 4, offset=3)
        result = self.run_ccfa(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(screener_value(result), 12_632 + 16_572)


class TestActivityTest(MaCcfaTestCase):
    """CCFA requires 20 weekly hours per parent, which our inputs always satisfy.

    ``MaTotalHoursWorkedDependency`` floors reported hours at 40 for anyone 16 or older,
    so ``ma_ccfa_activity_eligible`` is vacuously true as we populate it. This pins that:
    a parent reporting no earned income is still eligible. If the floor is ever removed,
    this test is where the activity gate becomes live.
    """

    screen_id = 7306

    def test_parent_with_no_earned_income_still_passes(self):
        screen = self.build(2)
        self.add_parent(screen, wages=0)
        self.add_child(screen, 4)
        result = self.run_ccfa(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(screener_value(result), 16_572)


class TestDependentEarnings(MaCcfaTestCase):
    """A dependent's earnings do not count toward the income test.

    New in PolicyEngine 2.5.0, per EEC policy; before it a teenager's wages counted like
    a parent's. This household clears the three-person ceiling on the parent's wages
    alone and exceeds it once the teenager's are added, so it pins the exclusion itself
    rather than the ceiling.

    The exclusion does not read the ``is_tax_unit_dependent`` we send -- measured against
    the private API, PolicyEngine drops the earnings even for a member we report as not a
    dependent -- so it reaches every household with a working child, not only those our
    own dependent test claims.

    The teenager is 16 and not disabled, so CCFA cannot be claimed for them and only the
    four-year-old is priced.
    """

    screen_id = 7307

    def test_a_working_teenagers_wages_are_excluded(self):
        screen = self.build(3)
        self.add_parent(screen, wages=100_000)
        teen = self.add_child(screen, 16, offset=2)
        add_income(teen, 40_000, "wages", "yearly")
        self.add_child(screen, 4, offset=3)
        result = self.run_ccfa(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(screener_value(result), 16_572)

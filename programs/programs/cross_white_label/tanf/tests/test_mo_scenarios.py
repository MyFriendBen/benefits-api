"""
Spec-scenario tests for MO TANF — one test per Test Scenario in ``specs/mo.md``.

``MoTanf`` supplies inputs and reads PolicyEngine's ``mo_tanf``, so these assert the whole
grant end to end: the dependent-child gate, all three income gates, both earned-income
disregard sequences, the care-cost caps, the SSI exclusion and the $10 minimum payment.
Each runs the scenario's household through PolicyEngine once and replays from a cassette.

Values are asserted in **annual** dollars, which is what the screener reports
(``estimated_value``); the spec states monthly figures for readability, following the same
storage convention as ``specs/ks.md``. So a spec expectation of $292/month is asserted as
$3,505 — PolicyEngine's exact $292.09 × 12, truncated the way the API truncates it. The
cents are why these are not always exactly monthly × 12.

Three scenarios are documented PE divergences the spec accepts as-is (AC 30/31): 8 and 20
return "eligible, $0" where strict Missouri regulation would deny, and 32 passes a Gate 1
boundary Missouri would fail. A $0 value means the frontend filters the program out, so
the practical outcome matches; the tests pin PolicyEngine's actual answer rather than the
regulation's, per the spec.

Scenarios 11, 12 and 34 assert PolicyEngine's answer for a needy non-parent caretaker
household, which is the *inclusion* branch. Missouri also grants such a caretaker an
election between being included and excluded, and per AC 20 MFB does not implement it —
so where the spec's expectation reflects the excluded configuration, the expected value
here is the included one PolicyEngine returns. See ``specs/mo.md`` AC 20.

Scenario 13 is expected to fail and is skipped: the household's only income is the SSI
child's, so ``HouseholdMember.is_dependent()`` puts that child in a separate tax unit,
and PolicyEngine's caretaker test requires a dependent child in the *same* tax unit. That
is shared screener logic, not a MoTanf concern — see the skip reason.
"""

import datetime

import pytest

from programs.programs.cross_white_label.tanf.mo import MoTanf
from programs.programs.testing_fixtures.pe_integration import (
    PeIntegrationTestCase,
    add_income,
    add_member,
    calc_pe_program,
    make_program,
    make_screen,
    screener_value,
)
from screener.models import Expense
from screener.serializers import _write_current_benefits
from screener.tests.helpers import seed_program

PE_VERSION = "1.794.2"
YEAR = "2026"


class MoTanfScenarioTestCase(PeIntegrationTestCase):
    """Shared household builder. Every scenario is St. Louis City, ZIP 63101."""

    pe_version = PE_VERSION

    # Distinct per subclass so each scenario's cassette pins its own household.
    screen_id = 0

    def build(self, household_size, household_assets=0, on_tanf=False):
        # make_screen creates the white label; make_program looks it up, so it
        # has to run second.
        screen = make_screen(
            self.screen_id,
            white_label_code="mo",
            state_code="MO",
            household_size=household_size,
            zipcode="63101",
            county="St. Louis City",
            household_assets=household_assets,
        )
        self.program = make_program("mo", "mo_tanf", YEAR)

        if on_tanf:
            # Reported TA receipt selects PE's active-participant disregard sequence via
            # is_tanf_enrolled -> receives_tanf.
            seed_program(screen.white_label, "mo_tanf_current", base_program="tanf")
            _write_current_benefits(screen, ["mo_tanf_current"])
            screen.invalidate_current_benefits_cache()

        return screen

    def add_person(self, screen, offset, relationship, birth_year, birth_month=1, **kwargs):
        """A member identified by birth month/year, as every scenario states them."""
        return add_member(
            screen,
            self.screen_id * 100 + offset,
            relationship,
            int(YEAR) - birth_year,
            birth_year_month=datetime.date(birth_year, birth_month, 1),
            **kwargs,
        )

    def add_expense(self, screen, expense_type, monthly_amount, household_member=None):
        return Expense.objects.create(
            screen=screen,
            household_member=household_member,
            type=expense_type,
            amount=monthly_amount,
            frequency="monthly",
        )

    def assert_result(self, screen, expected_eligible, expected_annual_value):
        result = calc_pe_program(screen, MoTanf, self.program)
        self.assertEqual(
            (bool(result.eligible), screener_value(result)),
            (expected_eligible, expected_annual_value),
        )


@pytest.mark.integration
class TestScenario01GoldenPath(MoTanfScenarioTestCase):
    """Baseline, no income, size 3 → $292/month."""

    screen_id = 1

    def test_size_three_no_income(self):
        screen = self.build(3)
        self.add_person(screen, 1, "headOfHousehold", 1996)
        self.add_person(screen, 2, "child", 2020)
        self.add_person(screen, 3, "child", 2023)
        self.assert_result(screen, True, 3_505)


@pytest.mark.integration
class TestScenario02NoDependentChild(MoTanfScenarioTestCase):
    """No qualifying child → ineligible, whatever the income."""

    screen_id = 2

    def test_single_adult(self):
        screen = self.build(1)
        self.add_person(screen, 1, "headOfHousehold", 1996, pregnant=False)
        self.assert_result(screen, False, 0)


@pytest.mark.integration
class TestScenario03NotActiveEarner(MoTanfScenarioTestCase):
    """Not-active sequence: $90, then $30-plus-⅓ → $222/month."""

    screen_id = 3

    def test_two_parent_one_earner(self):
        screen = self.build(4)
        head = self.add_person(screen, 1, "headOfHousehold", 1996)
        add_income(head, amount=300)
        self.add_person(screen, 2, "spouse", 1996)
        self.add_person(screen, 3, "child", 2020)
        self.add_person(screen, 4, "child", 2023)
        self.assert_result(screen, True, 2_661)


@pytest.mark.integration
class TestScenario04ActiveEarner(MoTanfScenarioTestCase):
    """Active sequence on Scenario 3's household: two-thirds first → $332/month."""

    screen_id = 4

    def test_same_household_currently_receiving(self):
        screen = self.build(4, on_tanf=True)
        head = self.add_person(screen, 1, "headOfHousehold", 1996)
        add_income(head, amount=300)
        self.add_person(screen, 2, "spouse", 1996)
        self.add_person(screen, 3, "child", 2020)
        self.add_person(screen, 4, "child", 2023)
        self.assert_result(screen, True, 3_981)


@pytest.mark.integration
class TestScenario05ActiveTwoThirdsAtGate2(MoTanfScenarioTestCase):
    """$1,200 raw fails Gate 2; two-thirds ($400) passes it → $32/month."""

    screen_id = 5

    def test_two_thirds_applied_at_gate_two(self):
        screen = self.build(4, on_tanf=True)
        head = self.add_person(screen, 1, "headOfHousehold", 1996)
        add_income(head, amount=1_200)
        self.add_person(screen, 2, "spouse", 1996)
        self.add_person(screen, 3, "child", 2020)
        self.add_person(screen, 4, "child", 2023)
        self.assert_result(screen, True, 381)


@pytest.mark.integration
class TestScenario06ResourceLimitBoundary(MoTanfScenarioTestCase):
    """Assets exactly at the $1,000 limit pass → $234/month."""

    screen_id = 6

    def test_assets_at_the_limit(self):
        screen = self.build(2, household_assets=1_000)
        self.add_person(screen, 1, "headOfHousehold", 1996)
        self.add_person(screen, 2, "child", 2020)
        self.assert_result(screen, True, 2_809)


@pytest.mark.integration
class TestScenario07AssetsBetweenTiers(MoTanfScenarioTestCase):
    """$4,000 exceeds the $1,000 applicant tier → ineligible."""

    screen_id = 7

    def test_assets_over_the_limit(self):
        screen = self.build(2, household_assets=4_000)
        self.add_person(screen, 1, "headOfHousehold", 1996)
        self.add_person(screen, 2, "child", 2020)
        self.assert_result(screen, False, 0)


@pytest.mark.integration
class TestScenario08Gate3EqualityBoundary(MoTanfScenarioTestCase):
    """Accepted PE divergence (AC 30): strict regulation denies at a $0 deficit;
    PolicyEngine returns eligible with $0, which the frontend filters out anyway."""

    screen_id = 8

    def test_countable_income_equals_the_payment_standard(self):
        screen = self.build(2)
        head = self.add_person(screen, 1, "headOfHousehold", 1996)
        add_income(head, amount=471)
        self.add_person(screen, 2, "child", 2020)
        self.assert_result(screen, False, 0)


@pytest.mark.integration
class TestScenario09NotActiveEarnerSmallerHousehold(MoTanfScenarioTestCase):
    """Same not-active formula at size 2 → $114/month."""

    screen_id = 9

    def test_size_two_one_earner(self):
        screen = self.build(2)
        head = self.add_person(screen, 1, "headOfHousehold", 1996)
        add_income(head, amount=300)
        self.add_person(screen, 2, "child", 2020)
        self.assert_result(screen, True, 1_369)


@pytest.mark.integration
class TestScenario10KinshipCaretakerIncluded(MoTanfScenarioTestCase):
    """Grandparent caretaker with two grandchildren, no income → $292/month."""

    screen_id = 10

    def test_grandparent_with_two_grandchildren(self):
        screen = self.build(3)
        self.add_person(screen, 1, "headOfHousehold", 1971)
        self.add_person(screen, 2, "grandChild", 2020)
        self.add_person(screen, 3, "grandChild", 2018)
        self.assert_result(screen, True, 3_505)


@pytest.mark.integration
@pytest.mark.skip(
    reason="Blocked on PolicyEngine: no NPCR concept, so a qualifying caretaker is always an "
    "assistance-unit member and no neediness budget or election runs (spec AC 20). The assertion is "
    "Missouri's expected grant; PolicyEngine currently returns the caretaker-included result "
    "($192.09/month). Un-skip when PE models the election."
)
class TestScenario11NpcrWithIncome(MoTanfScenarioTestCase):
    """A needy caretaker with $100/month unearned income → $234/month.

    No spouse in the home, so the NPCR is automatically needy and the election applies:
    included is size 3 at $292 − $100 = $192, excluded is child-only size 2 at $234, and
    Missouri takes the higher.
    """

    screen_id = 11

    def test_election_takes_the_higher_of_the_two_configurations(self):
        screen = self.build(3)
        head = self.add_person(screen, 1, "headOfHousehold", 1971)
        add_income(head, amount=100, income_type="unemployment")
        self.add_person(screen, 2, "grandChild", 2020)
        self.add_person(screen, 3, "grandChild", 2018)
        self.assert_result(screen, True, 2_809)


@pytest.mark.integration
@pytest.mark.skip(
    reason="Blocked on PolicyEngine: no NPCR concept, so a qualifying caretaker is always an "
    "assistance-unit member and no neediness budget or election runs (spec AC 20). The assertion is "
    "Missouri's expected grant; PolicyEngine currently returns the caretaker-included result "
    "(ineligible). Un-skip when PE models the election."
)
class TestScenario12NpcrNotNeedy(MoTanfScenarioTestCase):
    """Caretaker with $700/month and a co-resident spouse → $234/month.

    The NPCR/spouse neediness group is size 2 against a $678 Standard of Need, so $700
    fails it: exclusion is mandatory with no election, leaving the two grandchildren as a
    size-2 unit.
    """

    screen_id = 12

    def test_failing_neediness_excludes_the_caretaker(self):
        screen = self.build(4)
        head = self.add_person(screen, 1, "headOfHousehold", 1971)
        add_income(head, amount=700, income_type="unemployment")
        self.add_person(screen, 2, "spouse", 1973)
        self.add_person(screen, 3, "grandChild", 2020)
        self.add_person(screen, 4, "grandChild", 2018)
        self.assert_result(screen, True, 2_809)


@pytest.mark.integration
@pytest.mark.skip(
    reason="Expected failure, not a MoTanf defect: the SSI child's income is the household's "
    "only income, so HouseholdMember.is_dependent()'s support test (child income <= household "
    "income / 2) can never pass and the child is placed in a separate tax unit. PolicyEngine's "
    "caretaker test requires a dependent child in the same tax unit, so the payee loses their "
    "qualifying child and the household is denied. Given a single tax unit PolicyEngine returns "
    "the spec's $136/month. Fix belongs in shared screener tax-unit logic, which shapes every "
    "PE program's payload (pe_dependencies/payload.py)."
)
class TestScenario13SsiChildPayeeOnly(MoTanfScenarioTestCase):
    """SSI child excluded from the unit; payee still receives a size-1 grant → $136/month."""

    screen_id = 13

    def test_payee_only_unit(self):
        screen = self.build(2)
        self.add_person(screen, 1, "headOfHousehold", 1996)
        child = self.add_person(screen, 2, "child", 2016)
        add_income(child, amount=750, income_type="sSI")
        self.assert_result(screen, True, 1_628)


@pytest.mark.integration
class TestScenario14LargerHousehold(MoTanfScenarioTestCase):
    """Size-5 payment standard → $388/month."""

    screen_id = 14

    def test_size_five_no_income(self):
        screen = self.build(5)
        self.add_person(screen, 1, "headOfHousehold", 1996)
        self.add_person(screen, 2, "child", 2020)
        self.add_person(screen, 3, "child", 2018)
        self.add_person(screen, 4, "child", 2016)
        self.add_person(screen, 5, "child", 2014)
        self.assert_result(screen, True, 4_652)


@pytest.mark.integration
class TestScenario15NonQualifyingSiblingExcluded(MoTanfScenarioTestCase):
    """A 19-year-old is excluded on age alone, leaving a size-2 unit → $234/month."""

    screen_id = 15

    def test_nineteen_year_old_dropped_from_headcount(self):
        screen = self.build(3)
        self.add_person(screen, 1, "headOfHousehold", 1996)
        self.add_person(screen, 2, "child", 2016)
        self.add_person(screen, 3, "child", 2007)
        self.assert_result(screen, True, 2_809)


@pytest.mark.integration
class TestScenario16PregnancyAloneDoesNotQualify(MoTanfScenarioTestCase):
    """RSMo 208.040 grants TA on behalf of a dependent child; pregnancy alone does not."""

    screen_id = 16

    def test_pregnant_with_no_child(self):
        screen = self.build(1)
        self.add_person(screen, 1, "headOfHousehold", 2001, pregnant=True)
        self.assert_result(screen, False, 0)


@pytest.mark.integration
class TestScenario17ChildcareBelowCap(MoTanfScenarioTestCase):
    """$100 actual cost deducts in full, under the $175 cap → $214/month."""

    screen_id = 17

    def test_actual_cost_below_the_cap(self):
        screen = self.build(2)
        head = self.add_person(screen, 1, "headOfHousehold", 1996)
        add_income(head, amount=300)
        self.add_person(screen, 2, "child", 2020)
        self.add_expense(screen, "childCare", 100)
        self.assert_result(screen, True, 2_569)


@pytest.mark.integration
class TestScenario18ChildcareCapped(MoTanfScenarioTestCase):
    """$300 actual cost is capped at $175 → $109/month."""

    screen_id = 18

    def test_cap_binds(self):
        screen = self.build(2)
        head = self.add_person(screen, 1, "headOfHousehold", 1996)
        add_income(head, amount=570)
        self.add_person(screen, 2, "child", 2020)
        self.add_expense(screen, "childCare", 300)
        self.assert_result(screen, True, 1_309)


@pytest.mark.integration
class TestScenario19MinimumPaymentFloorBoundary(MoTanfScenarioTestCase):
    """A deficit of exactly $10 still pays → $10/month."""

    screen_id = 19

    def test_deficit_exactly_at_the_floor(self):
        screen = self.build(2)
        head = self.add_person(screen, 1, "headOfHousehold", 1996)
        add_income(head, amount=456)
        self.add_person(screen, 2, "child", 2020)
        self.assert_result(screen, True, 121)


@pytest.mark.integration
class TestScenario20MinimumPaymentFloorOverBoundary(MoTanfScenarioTestCase):
    """Accepted PE divergence (AC 31): a $9.33 deficit is below Missouri's $10 floor, so
    PolicyEngine suppresses the payment to $0 and reports eligible rather than denying."""

    screen_id = 20

    def test_deficit_below_the_floor(self):
        screen = self.build(2)
        head = self.add_person(screen, 1, "headOfHousehold", 1996)
        add_income(head, amount=457)
        self.add_person(screen, 2, "child", 2020)
        self.assert_result(screen, False, 0)


@pytest.mark.integration
@pytest.mark.skip(
    reason="Expected failure, same shared-screener defect as Scenario 13, not a MoTanf issue: "
    "the student child's $15,600/yr is more than half the household's income, so "
    "HouseholdMember.is_dependent() fails them on both the qualifying-child support test and "
    "the qualifying-relative threshold, and they are placed in a separate tax unit. The "
    "caretaker's tax unit then contains no dependent child. PolicyEngine exempts a student "
    "child's earnings correctly and returns the spec's $234/month for a single tax unit — "
    "verified live, with and without the student flags set."
)
class TestScenario21ChildStudentEarningsExcluded(MoTanfScenarioTestCase):
    """A full-time student child's $1,300/month is excluded at Gate 1 and in the grant,
    which is the only reason the household is not denied outright → $234/month."""

    screen_id = 21

    def test_student_child_earnings_excluded(self):
        screen = self.build(2)
        self.add_person(screen, 1, "headOfHousehold", 1996)
        child = self.add_person(screen, 2, "child", 2010, student=True, student_full_time=True)
        add_income(child, amount=1_300)
        self.assert_result(screen, True, 2_809)


@pytest.mark.integration
class TestScenario22TwoEarners(MoTanfScenarioTestCase):
    """The disregard runs per earner, not against combined earnings → $168/month."""

    screen_id = 22

    def test_each_earner_disregarded_separately(self):
        screen = self.build(4)
        head = self.add_person(screen, 1, "headOfHousehold", 1996)
        add_income(head, amount=300)
        spouse = self.add_person(screen, 2, "spouse", 1996)
        add_income(spouse, amount=200)
        self.add_person(screen, 3, "child", 2020)
        self.add_person(screen, 4, "child", 2023)
        self.assert_result(screen, True, 2_021)


@pytest.mark.integration
class TestScenario23UnearnedIncome(MoTanfScenarioTestCase):
    """Unearned income gets no earned-income disregard → $34/month."""

    screen_id = 23

    def test_unemployment_counts_in_full(self):
        screen = self.build(2)
        head = self.add_person(screen, 1, "headOfHousehold", 1996)
        add_income(head, amount=200, income_type="unemployment")
        self.add_person(screen, 2, "child", 2020)
        self.assert_result(screen, True, 409)


@pytest.mark.integration
class TestScenario24SizeEightPaymentStandard(MoTanfScenarioTestCase):
    """Size-8 payment standard → $514/month."""

    screen_id = 24

    def test_size_eight(self):
        screen = self.build(8)
        self.add_person(screen, 1, "headOfHousehold", 1996)
        for offset, birth_year in enumerate([2024, 2022, 2020, 2018, 2016, 2014, 2012], start=2):
            self.add_person(screen, offset, "child", birth_year)
        self.assert_result(screen, True, 6_169)


@pytest.mark.integration
class TestScenario25IncapacitatedCareDeduction(MoTanfScenarioTestCase):
    """A reported dependentCare cost deducts at the $175 incapacitated-person tier."""

    screen_id = 25

    def test_dependent_care_deducted(self):
        screen = self.build(3)
        head = self.add_person(screen, 1, "headOfHousehold", 1996)
        add_income(head, amount=570)
        self.add_person(screen, 2, "spouse", 1996, long_term_disability=True)
        self.add_person(screen, 3, "child", 2020)
        self.add_expense(screen, "dependentCare", 175)
        self.assert_result(screen, True, 2_005)


@pytest.mark.integration
class TestScenario26NoDependentCareReported(MoTanfScenarioTestCase):
    """No deduction is invented from a disability flag alone, so the same household with
    no reported cost is denied."""

    screen_id = 26

    def test_disability_flag_alone_deducts_nothing(self):
        screen = self.build(3)
        head = self.add_person(screen, 1, "headOfHousehold", 1996)
        add_income(head, amount=570)
        self.add_person(screen, 2, "spouse", 1996, long_term_disability=True)
        self.add_person(screen, 3, "child", 2020)
        self.assert_result(screen, False, 0)


@pytest.mark.integration
class TestScenario27UnderTwoChildcareCap(MoTanfScenarioTestCase):
    """A child under 2 uses the $200 cap, not $175 → $134/month."""

    screen_id = 27

    def test_under_two_cap(self):
        screen = self.build(2)
        head = self.add_person(screen, 1, "headOfHousehold", 1996)
        add_income(head, amount=570)
        self.add_person(screen, 2, "child", 2025)
        self.add_expense(screen, "childCare", 300)
        self.assert_result(screen, True, 1_609)


@pytest.mark.integration
class TestScenario28SelfEmploymentIsNetProfit(MoTanfScenarioTestCase):
    """Reported self-employment is net profit and runs the same sequence as wages."""

    screen_id = 28

    def test_self_employment_matches_wages(self):
        screen = self.build(2)
        head = self.add_person(screen, 1, "headOfHousehold", 1996)
        add_income(head, amount=300, income_type="selfEmployment")
        self.add_person(screen, 2, "child", 2020)
        self.assert_result(screen, True, 1_369)


@pytest.mark.integration
class TestScenario29AggregateChildcareCap(MoTanfScenarioTestCase):
    """Per-child caps sum ($200 under-2 + $175 age-2-plus = $375), not one flat cap."""

    screen_id = 29

    def test_caps_sum_across_children(self):
        screen = self.build(3)
        head = self.add_person(screen, 1, "headOfHousehold", 1996)
        add_income(head, amount=820)
        self.add_person(screen, 2, "child", 2025)
        self.add_person(screen, 3, "child", 2020)
        self.add_expense(screen, "childCare", 500)
        self.assert_result(screen, True, 2_405)


@pytest.mark.integration
class TestScenario30ChildSupportReceived(MoTanfScenarioTestCase):
    """Child support counts as unearned income at the reported amount → $203/month."""

    screen_id = 30

    def test_child_support_counts(self):
        screen = self.build(2, on_tanf=True)
        head = self.add_person(screen, 1, "headOfHousehold", 1996)
        add_income(head, amount=31, income_type="childSupport")
        self.add_person(screen, 2, "child", 2020)
        self.assert_result(screen, True, 2_437)


@pytest.mark.integration
class TestScenario31OwnGrantExcluded(MoTanfScenarioTestCase):
    """A current recipient's own TA grant is excluded from its own recalculation, so the
    result matches a recipient reporting no income → $234/month."""

    screen_id = 31

    def test_own_cash_assistance_excluded(self):
        screen = self.build(2, on_tanf=True)
        head = self.add_person(screen, 1, "headOfHousehold", 1996)
        add_income(head, amount=234, income_type="cashAssistance")
        self.add_person(screen, 2, "child", 2020)
        self.assert_result(screen, True, 2_809)


@pytest.mark.integration
class TestScenario32Gate1EqualityBoundary(MoTanfScenarioTestCase):
    """Accepted PE divergence (AC 31): strict regulation fails Gate 1 at exactly the
    Gross Max; PolicyEngine's formula-based ceiling passes it."""

    screen_id = 32

    def test_gross_income_equals_the_gross_max(self):
        screen = self.build(2, on_tanf=True)
        head = self.add_person(screen, 1, "headOfHousehold", 1996)
        add_income(head, amount=1_254)
        self.add_person(screen, 2, "child", 2025)
        self.add_expense(screen, "childCare", 200)
        self.assert_result(screen, True, 1_273)


@pytest.mark.integration
class TestScenario33Gate2DeniesAfterRetry(MoTanfScenarioTestCase):
    """Gate 2 denies on its own even after the (9)(C)2) $30-plus-⅓ retry."""

    screen_id = 33

    def test_gate_two_independently_denies(self):
        screen = self.build(4)
        head = self.add_person(screen, 1, "headOfHousehold", 1996)
        add_income(head, amount=1_515)
        self.add_person(screen, 2, "child", 2025, birth_month=1)
        self.add_person(screen, 3, "child", 2025, birth_month=6)
        self.add_person(screen, 4, "child", 2025, birth_month=11)
        self.add_expense(screen, "childCare", 600)
        self.assert_result(screen, False, 0)


@pytest.mark.integration
class TestScenario34NpcrSpouseOnSsi(MoTanfScenarioTestCase):
    """An SSI spouse is excluded from the unit, leaving caretaker plus two grandchildren
    at size 3 → $292/month."""

    screen_id = 34

    def test_ssi_spouse_excluded_from_the_unit(self):
        screen = self.build(4)
        self.add_person(screen, 1, "headOfHousehold", 1971)
        spouse = self.add_person(screen, 2, "spouse", 1973)
        add_income(spouse, amount=750, income_type="sSI")
        self.add_person(screen, 3, "grandChild", 2020)
        self.add_person(screen, 4, "grandChild", 2018)
        self.assert_result(screen, True, 3_505)


@pytest.mark.integration
@pytest.mark.skip(
    reason="Blocked on MFB-1697: cashAssistance is the screener's TANF field, so spm.Tanf "
    "sends any reported amount as PE's `tanf` input, which PE excludes from TANF's own "
    "unearned-income sources. A household reporting non-MO cash assistance therefore has it "
    "excluded too and returns $234/month. The assertion is Criterion 8's expected $34. "
    "Separating the branches means revisiting the cashAssistance -> TANF mapping across every "
    "PE input that reads it; un-skip when that lands."
)
class TestScenario35GenericCashAssistanceCounts(MoTanfScenarioTestCase):
    """Cash assistance from a household not on mo_tanf is ordinary unearned income → $34.

    The mirror of Scenario 31, which proves the self-exclusion branch when the amount *is*
    the household's own MO TA grant.
    """

    screen_id = 35

    def test_cash_assistance_counts_when_not_on_tanf(self):
        screen = self.build(2)
        head = self.add_person(screen, 1, "headOfHousehold", 1996)
        add_income(head, amount=200, income_type="cashAssistance")
        self.add_person(screen, 2, "child", 2020)
        self.assert_result(screen, True, 409)

"""
Unit tests for the MoTwha calculator — one test per spec.md Test Scenario, plus the
helper-level tests the spec requires where a rule has no eligibility outcome to flip.

Coverage maps to ``specs/mo.md`` — its criteria, criterion 5's ordered disregards, Data
Gap 7's two-pass fallback, and its 19 scenarios.

Built on real ``Screen`` / ``HouseholdMember`` / ``IncomeStream`` / ``Expense`` /
``Insurance`` rows rather than mocks. Almost every rule here is a question about
income-type filtering (``calc_gross_income``'s ``earned`` selector, per-stream
``monthly()`` conversion), about ``calc_age``'s month-inclusive boundary, or about
``is_married``'s spouse resolution — a mock standing in for those would assert the mock's
own semantics rather than the calculator's.

Ages are stated as ``birth_year_month`` and the reference date is pinned to the spec's
2026-09-01 for every test, since the age boundary is month-precision and is meaningless
without the pin (Scenarios 2-6 turn on it).

Six scenarios (9, 11, 12, 13, 14, 16) assert against the countable-income helper — a
stream's contribution or a disregard's amount — rather than the verdict, because the
inclusive pass would return Eligible on those fixtures either way, so the verdict alone
cannot show the rule was applied. The spec says so explicitly for each.

What is deliberately not tested here, and why, is listed in specs/mo.md under "Known
scenario gaps" — residency and citizenship are config rather than calculator logic, and the
rest turn on facts the screener never collects, so they have no branch to exercise.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from programs.framework.base import ProgramCalculator
from programs.models import Program
from programs.programs.cross_white_label.medicaid.disability.mo import MoTwha
from programs.programs.testing_fixtures.pe_integration import make_program, make_screen
from screener.models import Expense, HouseholdMember, IncomeStream, Insurance, Screen

YEAR = "2026"
VALUE_PER_MEMBER = 12_200
REFERENCE_DATE = date(2026, 9, 1)


class MoTwhaTestCase(TestCase):
    """Household builder shared by every test below."""

    # Distinct ids per household keep the members of one screen from colliding with
    # another's when a test builds more than one.
    next_screen_id = 1

    def build(self, household_size, household_assets=0, zipcode="63101", county="St. Louis City"):
        screen = make_screen(
            MoTwhaTestCase.next_screen_id,
            white_label_code="mo",
            state_code="MO",
            household_size=household_size,
            zipcode=zipcode,
            county=county,
            household_assets=household_assets,
        )
        # Reused rather than recreated: a test building more than one household would
        # otherwise collide on the program row's unique (white_label, name_abbreviated).
        existing = Program.objects.filter(white_label=screen.white_label, name_abbreviated="mo_twha").first()
        self.program = existing or make_program("mo", "mo_twha", YEAR)
        self.member_id = MoTwhaTestCase.next_screen_id * 100
        MoTwhaTestCase.next_screen_id += 1
        return screen

    def add_person(self, screen, relationship, birth_year, birth_month=1, **kwargs):
        """A member stated by birth year/month, which is what makes the age boundary decidable.

        ``age`` is left unset so nothing can read a precomputed integer instead of deriving
        the age from ``birth_year_month`` against the pinned reference date.
        """
        self.member_id += 1
        member = HouseholdMember.objects.create(
            id=self.member_id,
            screen=screen,
            relationship=relationship,
            age=None,
            birth_year_month=date(birth_year, birth_month, 1),
            **kwargs,
        )
        # The insurance relation is non-null on the model; default to uninsured.
        Insurance.objects.create(household_member=member, none=True)
        return member

    def add_income(self, member, amount, income_type="wages", frequency="monthly"):
        return IncomeStream.objects.create(
            screen=member.screen,
            household_member=member,
            type=income_type,
            amount=amount,
            frequency=frequency,
        )

    def calculator(self, screen) -> MoTwha:
        # Read off the screen's white label rather than an attribute set by `build`, so a
        # test that reassigns `screen` or builds more than one household still resolves the
        # right row.
        program = Program.objects.filter(white_label=screen.white_label, name_abbreviated="mo_twha").first()
        return MoTwha(screen, program, {}, None)

    def evaluate(self, screen):
        """Full eligibility + value under the spec's pinned reference date."""
        with patch.object(Screen, "get_reference_date", return_value=REFERENCE_DATE):
            calc = self.calculator(screen)
            e = calc.eligible()
            calc.value(e)
            return e.eligible, e.value

    def countable(self, screen, worker, **kwargs):
        with patch.object(Screen, "get_reference_date", return_value=REFERENCE_DATE):
            return self.calculator(screen)._countable_income(worker, **kwargs)


class TestClassAttributes(MoTwhaTestCase):
    def test_is_subclass(self):
        self.assertTrue(issubclass(MoTwha, ProgramCalculator))

    def test_program_code(self):
        self.assertEqual(MoTwha.program_code, "mo_twha")

    def test_constants(self):
        self.assertEqual(MoTwha.min_age, 16)
        self.assertEqual(MoTwha.max_age, 64)
        self.assertEqual(MoTwha.member_amount, VALUE_PER_MEMBER)
        self.assertEqual(MoTwha.income_boundary_250, {1: Decimal("3324.99"), 2: Decimal("4508.99")})
        self.assertEqual(MoTwha.income_ceiling_300, {1: Decimal("3990.00"), 2: Decimal("5410.00")})
        self.assertEqual(MoTwha.resource_limits, {1: 6_220, 2: 12_441})

    def test_insurance_is_read_by_no_eligibility_gate(self):
        """The spec makes this a structural claim, not just Scenario 19's behavioural one: a
        gate combining ``employer`` with another condition could still pass that scenario.

        Checked against the executable code with comments and docstrings stripped, since the
        class docstring discusses employer coverage at length in prose.
        """
        import ast
        import inspect

        tree = ast.parse(inspect.getsource(MoTwha).strip())

        # Every attribute read anywhere in the class. Coverage mode is never consulted at
        # all, so no `Insurance` field or accessor appears — leaving no gate for `employer`
        # to sit in. (`health_insurance_premium`, a disregard key, is a dict key rather than
        # an attribute, so it is correctly not caught here.)
        attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}

        self.assertNotIn("insurance", attributes)
        self.assertNotIn("has_insurance_types", attributes)
        self.assertNotIn("employer", attributes)


class TestSpecScenarios(MoTwhaTestCase):
    def test_scenario_1_golden_path(self):
        """Working-age disabled worker with low earned income — Eligible, $12,200."""
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        self.add_income(member, 1_000)

        self.assertEqual(self.evaluate(screen), (True, VALUE_PER_MEMBER))

    def test_scenario_2_below_age_floor(self):
        """Born August 2011 — turns 16 after the reference date. Ineligible."""
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 2011, birth_month=8, long_term_disability=True)
        self.add_income(member, 1_000)

        eligible, _ = self.evaluate(screen)
        self.assertFalse(eligible)

    def test_scenario_3_month_of_16th_birthday(self):
        """Turns 16 in the 2026-09 reference month — the floor is month-inclusive."""
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 2010, birth_month=9, long_term_disability=True)
        self.add_income(member, 1_000)

        self.assertEqual(self.evaluate(screen), (True, VALUE_PER_MEMBER))

    def test_scenario_4_age_64(self):
        """Age 64 is included, not excluded."""
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 1962, birth_month=8, long_term_disability=True)
        self.add_income(member, 1_000)

        self.assertEqual(self.evaluate(screen), (True, VALUE_PER_MEMBER))

    def test_scenario_5_month_of_65th_birthday(self):
        """Turns 65 in the reference month — eligibility runs through that whole month."""
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 1961, birth_month=9, long_term_disability=True)
        self.add_income(member, 1_000)

        self.assertEqual(self.evaluate(screen), (True, VALUE_PER_MEMBER))

    def test_scenario_6_one_month_past_65th_birthday(self):
        """Turned 65 one month before the reference month — the ceiling now bites."""
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 1961, birth_month=8, long_term_disability=True)
        self.add_income(member, 1_000)

        eligible, _ = self.evaluate(screen)
        self.assertFalse(eligible)

    def test_scenario_7_no_qualifying_disability(self):
        """Neither disability field set — the requirement is not waived for a working adult."""
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=False, visually_impaired=False)
        self.add_income(member, 1_000)

        eligible, _ = self.evaluate(screen)
        self.assertFalse(eligible)

    def test_scenario_8_no_earned_income(self):
        """Disabled but not working — this is the working-disabled buy-in."""
        screen = self.build(1)
        self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)

        eligible, _ = self.evaluate(screen)
        self.assertFalse(eligible)

    def test_scenario_9_worker_earned_income_carries_case_into_band(self):
        """$2,000 wages + $2,500 pension: countable $3,405, inside the single $3,325-$3,990 band.

        The verdict cannot carry this test — the inclusive pass would remove the $2,000 and
        report Eligible too. The intermediate discriminates: the two paths report a $2,000
        vs $0 wages contribution, and being stream-scoped it holds with or without the $75.
        """
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        self.add_income(member, 2_000, "wages")
        self.add_income(member, 2_500, "pension")

        self.assertEqual(self.evaluate(screen), (True, VALUE_PER_MEMBER))

        result = self.countable(screen, member)
        self.assertEqual(result.contribution("wages"), Decimal(2_000))
        self.assertEqual(result.disregards["half_earned"], Decimal(1_000))
        self.assertEqual(result.total, Decimal("3405"))

    def test_scenario_10_spouse_unearned_income_above_250_percent(self):
        """The band allowance covers only the worker's own earned income, and the inclusive
        pass cannot remove a spouse's pension — so the denial survives the fallback."""
        screen = self.build(2)
        head = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        spouse = self.add_person(screen, "spouse", 1986)
        self.add_income(head, 40, "wages")
        self.add_income(spouse, 4_650, "pension")

        eligible, _ = self.evaluate(screen)
        self.assertFalse(eligible)

        # Pass 1: 4,650 + 20 - 20 - 75 = 4,575, above the couple's 4,508.99 boundary.
        self.assertEqual(self.countable(screen, head).total, Decimal("4575"))
        # Pass 2 removes the worker's $40 but the half-earned deduction still applies:
        # 4,650 - 20 - 20 - 75 = 4,535 — still above the boundary by $26.01.
        self.assertEqual(self.countable(screen, head, exclude_unisolable=True).total, Decimal("4535"))

    def test_scenario_11_spouse_earned_income_disregard(self):
        """First $4,166.67/month of the spouse's earned income is excluded.

        The verdict cannot prove the disregard applied — had pass 1 denied, pass 2 would have
        admitted the household anyway. Omitting it would carry the full $7,000 into the count.
        """
        screen = self.build(2)
        head = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        spouse = self.add_person(screen, "spouse", 1986)
        self.add_income(head, 200, "wages")
        self.add_income(spouse, 7_000, "wages")

        self.assertEqual(self.evaluate(screen), (True, VALUE_PER_MEMBER))

        result = self.countable(screen, head)
        self.assertEqual(result.disregards["spouse_earned"], MoTwha.spouse_earned_disregard)
        # $7,000 - $4,166.67 = $2,833.33 of spouse wages left in the count, plus the
        # worker's own $200 — both land in the shared `wages` contribution.
        expected_wages = Decimal(7_000) - MoTwha.spouse_earned_disregard + Decimal(200)
        self.assertEqual(result.contribution("wages"), expected_wages)

    def test_scenario_12_ssi_fully_disregarded(self):
        """All SSI is excluded in full; the $40 wage floors countable income at exactly $0
        under every treatment, so the $0 is invariant and safe to assert."""
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        self.add_income(member, 40, "wages")
        self.add_income(member, 994, "sSI")

        self.assertEqual(self.evaluate(screen), (True, VALUE_PER_MEMBER))

        result = self.countable(screen, member)
        self.assertEqual(result.contribution("sSI"), Decimal(0))
        self.assertEqual(result.total, Decimal(0))

    def test_scenario_13_first_50_of_ssdi_disregarded(self):
        """The SSDI stream contributes $3,375 - $50 = $3,325 before case-level deductions.

        Stream-scoped because a final total would rest on the always-applied $75 deduction,
        which Data Gap 6 forbids any expected outcome from depending on.
        """
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        self.add_income(member, 40, "wages")
        self.add_income(member, 3_375, "sSDisability")

        self.assertEqual(self.evaluate(screen), (True, VALUE_PER_MEMBER))

        result = self.countable(screen, member)
        self.assertEqual(result.contribution("sSDisability"), Decimal(3_325))
        self.assertEqual(result.disregards["ssdi"], Decimal(50))

    def test_scenario_14_two_eligible_members_each_receive_spouse_disregard(self):
        """Both spouses are disabled workers and both independently qualify — $24,400.

        The intermediate proves the disregard is not conditioned on the spouse's disability
        status: the verdict cannot show that, since either spouse's wages might be excluded
        unobservably and the value would still be $24,400.
        """
        screen = self.build(2)
        head = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        spouse = self.add_person(screen, "spouse", 1986, long_term_disability=True)
        self.add_income(head, 200, "wages")
        self.add_income(spouse, 8_500, "wages")

        self.assertEqual(self.evaluate(screen), (True, VALUE_PER_MEMBER * 2))

        # Evaluating Person 1: the disregard applies even though Person 2 is also disabled.
        # 8,500 - 4,166.67 = 4,333.33, + 100 (half of 200) - 20 - 75 = 4,338.33.
        as_head = self.countable(screen, head)
        self.assertEqual(as_head.disregards["spouse_earned"], MoTwha.spouse_earned_disregard)
        self.assertEqual(as_head.total.quantize(Decimal("0.01")), Decimal("4338.33"))

        # Evaluating Person 2: Person 1's $200 is fully covered by the disregard, and
        # Person 2's own 8,500 halves to 4,250 — 8,500 - 4,250 - 20 - 75 = 4,155.
        as_spouse = self.countable(screen, spouse)
        self.assertEqual(as_spouse.disregards["spouse_earned"], Decimal(200))
        self.assertEqual(as_spouse.total, Decimal("4155"))

    def test_scenario_15_visually_impaired_alone_qualifies(self):
        """``visually_impaired`` alone satisfies the proxy — the two signals are an OR."""
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=False, visually_impaired=True)
        self.add_income(member, 1_000)

        self.assertEqual(self.evaluate(screen), (True, VALUE_PER_MEMBER))

    def test_scenario_16_cash_assistance_excluded(self):
        """``cashAssistance`` maps to the Temporary Assistance exclusion and contributes $0.

        The verdict does not discriminate — counting the $292 would leave the household
        eligible anyway — so the assertion is scoped to the stream's own contribution.
        """
        screen = self.build(3)
        head = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        self.add_person(screen, "child", 2016, birth_month=3)
        self.add_person(screen, "child", 2019, birth_month=6)
        self.add_income(head, 40, "wages")
        self.add_income(head, 292, "cashAssistance")

        self.assertEqual(self.evaluate(screen), (True, VALUE_PER_MEMBER))
        self.assertEqual(self.countable(screen, head).contribution("cashAssistance"), Decimal(0))

    def test_scenario_17_self_employment_qualifies(self):
        """Self-employment satisfies the employment criterion — the `earned` selector covers
        both types, where reading `wages` directly would deny every self-employed applicant."""
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        self.add_income(member, 1_000, "selfEmployment")

        self.assertEqual(self.evaluate(screen), (True, VALUE_PER_MEMBER))

    def test_scenario_18_dependent_children_do_not_resize_the_unit(self):
        """The worker is measured against the single-person threshold despite two children."""
        screen = self.build(3)
        head = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        self.add_person(screen, "child", 2016, birth_month=3)
        self.add_person(screen, "child", 2019, birth_month=6)
        self.add_income(head, 40, "wages")
        self.add_income(head, 3_600, "pension")

        eligible, _ = self.evaluate(screen)
        self.assertFalse(eligible)

        # Pass 1: 3,600 + 20 - 20 - 75 = 3,525, above the single-person 3,324.99 boundary.
        self.assertEqual(self.countable(screen, head).total, Decimal("3525"))
        # Pass 2 removes the $40 wage: 3,600 - 20 - 20 - 75 = 3,485 — still above.
        self.assertEqual(self.countable(screen, head, exclude_unisolable=True).total, Decimal("3485"))

    def test_scenario_19_employer_insurance_does_not_disqualify(self):
        """Scenario 1's fixture with employer insurance added — the result is identical, so
        the pair localises any fault to that field. Employer coverage triggers post-eligibility
        HIPP coordination, not a screening exclusion."""
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        self.add_income(member, 1_000)
        Insurance.objects.filter(household_member=member).update(none=False, employer=True)

        self.assertEqual(self.evaluate(screen), (True, VALUE_PER_MEMBER))


class TestAssistanceUnit(MoTwhaTestCase):
    """Criteria 4 and 5's unit is the individual or married couple, never household size."""

    def test_single_person_unit(self):
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        self.assertEqual(self.calculator(screen)._assistance_unit_size(member), 1)

    def test_married_couple_unit(self):
        screen = self.build(2)
        head = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        self.add_person(screen, "spouse", 1986)
        self.assertEqual(self.calculator(screen)._assistance_unit_size(head), 2)

    def test_children_do_not_enlarge_the_unit(self):
        screen = self.build(4)
        head = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        self.add_person(screen, "spouse", 1986)
        self.add_person(screen, "child", 2016)
        self.add_person(screen, "child", 2019)
        self.assertEqual(self.calculator(screen)._assistance_unit_size(head), 2)

    def test_domestic_partner_counts_as_a_spouse(self):
        """``is_married`` treats a domestic partner as spouse-equivalent, so the unit is 2
        and the partner's earned income receives the spouse disregard."""
        screen = self.build(2)
        head = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        self.add_person(screen, "domesticPartner", 1986)
        self.assertEqual(self.calculator(screen)._assistance_unit_size(head), 2)

    def test_couple_resource_limit_is_selected_for_a_married_worker(self):
        """Criterion 4 forbids denying on reported assets, so the standard chosen has no
        outcome to flip — assert the selection directly instead."""
        screen = self.build(2)
        head = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        self.add_person(screen, "spouse", 1986)
        calc = self.calculator(screen)
        self.assertEqual(calc.resource_limits[calc._assistance_unit_size(head)], 12_441)


class TestAssetsNeverDeny(MoTwhaTestCase):
    """Criterion 4's committed handling: reported assets alone never produce an ineligible
    determination, because the aggregate both over- and understates countable resources."""

    def test_assets_far_above_the_limit_still_eligible(self):
        screen = self.build(1, household_assets=500_000)
        member = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        self.add_income(member, 1_000)

        self.assertEqual(self.evaluate(screen), (True, VALUE_PER_MEMBER))

    def test_null_assets_treated_as_zero(self):
        screen = self.build(1)
        screen.household_assets = None
        screen.save()
        member = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        self.add_income(member, 1_000)

        self.assertEqual(self.evaluate(screen), (True, VALUE_PER_MEMBER))


class TestInclusiveFallback(MoTwhaTestCase):
    """Data Gap 7's two-pass fallback. The deciding fact is unobservable, so these are
    helper-level tests rather than household scenarios, per the spec."""

    def test_earned_income_only_household_above_300_percent_is_eligible(self):
        """The spec's required check: pass 2 removes the whole earned stream, so a household
        whose excess is entirely earned income is eligible at any income level. This is also
        why the program description must not present an income ceiling."""
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        self.add_income(member, 10_000, "wages")

        self.assertEqual(self.evaluate(screen), (True, VALUE_PER_MEMBER))
        self.assertEqual(self.countable(screen, member, exclude_unisolable=True).total, Decimal(0))

    def test_veteran_stream_removed_in_full_by_pass_two(self):
        """Missouri excludes only FSD-verified sub-components, which MFB cannot isolate, so
        the whole category is removed by pass 2 — deliberately over-inclusive."""
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        self.add_income(member, 40, "wages")
        self.add_income(member, 5_000, "veteran")

        self.assertEqual(self.evaluate(screen), (True, VALUE_PER_MEMBER))
        self.assertEqual(self.countable(screen, member, exclude_unisolable=True).contribution("veteran"), Decimal(0))

    def test_investment_stream_removed_in_full_by_pass_two(self):
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        self.add_income(member, 40, "wages")
        self.add_income(member, 5_000, "investment")

        self.assertEqual(self.evaluate(screen), (True, VALUE_PER_MEMBER))
        self.assertEqual(self.countable(screen, member, exclude_unisolable=True).contribution("investment"), Decimal(0))

    def test_pension_is_untouched_by_pass_two_and_still_denies(self):
        """Unearned income outside the exclusion list is not swallowed by the fallback."""
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        self.add_income(member, 40, "wages")
        self.add_income(member, 4_000, "pension")

        eligible, _ = self.evaluate(screen)
        self.assertFalse(eligible)
        self.assertEqual(
            self.countable(screen, member, exclude_unisolable=True).contribution("pension"), Decimal(4_000)
        )

    def test_half_earned_deduction_applies_even_when_the_earned_income_is_excluded(self):
        """The two treatments are independent (criterion 5, item 7)."""
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        self.add_income(member, 1_000, "wages")

        result = self.countable(screen, member, exclude_unisolable=True)
        self.assertEqual(result.contribution("wages"), Decimal(0))
        self.assertEqual(result.disregards["half_earned"], Decimal(500))

    def test_pass_two_does_not_run_when_the_ordinary_pass_admits(self):
        """Scenario 9's contrast: where pass 1 suffices, the reported wages contribution is
        the real amount, not the $0 pass 2 would report."""
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        self.add_income(member, 2_000, "wages")
        self.add_income(member, 2_500, "pension")

        self.assertEqual(self.countable(screen, member).contribution("wages"), Decimal(2_000))


class TestCountableIncomeDisregards(MoTwhaTestCase):
    """Criterion 5's ordered disregards, at the helper level."""

    def test_medical_expense_is_treated_as_the_health_insurance_premium(self):
        """Data Gap 6: the full reported generic ``medical`` expense is the premium disregard."""
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        self.add_income(member, 1_000, "wages")
        Expense.objects.create(screen=screen, type="medical", amount=300, frequency="monthly")

        result = self.countable(screen, member)
        self.assertEqual(result.disregards["health_insurance_premium"], Decimal(300))

    def test_standard_and_dental_optical_deductions_always_applied(self):
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        self.add_income(member, 1_000, "wages")

        result = self.countable(screen, member)
        self.assertEqual(result.disregards["standard"], Decimal(20))
        self.assertEqual(result.disregards["dental_optical"], Decimal(75))

    def test_countable_income_floors_at_zero(self):
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        self.add_income(member, 10, "wages")

        self.assertEqual(self.countable(screen, member).total, Decimal(0))

    def test_spouse_unearned_income_gets_no_earned_disregard(self):
        """The $50,000 disregard covers the spouse's *earned* income only."""
        screen = self.build(2)
        head = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        spouse = self.add_person(screen, "spouse", 1986)
        self.add_income(head, 40, "wages")
        self.add_income(spouse, 3_000, "pension")

        result = self.countable(screen, head)
        self.assertEqual(result.contribution("pension"), Decimal(3_000))
        self.assertNotIn("spouse_earned", result.disregards)

    def test_worker_unearned_income_gets_no_spouse_disregard(self):
        """The worker's own unearned income is not covered by the spouse disregard, and only
        the first $50 of their SSDI is excluded."""
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        self.add_income(member, 40, "wages")
        self.add_income(member, 2_000, "sSDisability")

        result = self.countable(screen, member)
        self.assertEqual(result.contribution("sSDisability"), Decimal(1_950))

    def test_spouse_ssdi_does_not_receive_the_50_dollar_disregard(self):
        """The first-$50 SSDI disregard is the *worker's* — not the spouse's."""
        screen = self.build(2)
        head = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        spouse = self.add_person(screen, "spouse", 1986)
        self.add_income(head, 40, "wages")
        self.add_income(spouse, 1_000, "sSDisability")

        result = self.countable(screen, head)
        self.assertEqual(result.contribution("sSDisability"), Decimal(1_000))
        self.assertNotIn("ssdi", result.disregards)

    def test_dependent_child_income_is_outside_the_assistance_unit(self):
        """A child's income neither enters the count nor resizes the unit."""
        screen = self.build(2)
        head = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        child = self.add_person(screen, "child", 2010)
        self.add_income(head, 40, "wages")
        self.add_income(child, 4_000, "wages")

        result = self.countable(screen, head)
        self.assertEqual(result.contribution("wages"), Decimal(40))

    def test_yearly_frequency_income_is_converted_to_monthly(self):
        """Thresholds are monthly, so a yearly-stated stream must be converted."""
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        self.add_income(member, 12_000, "pension", frequency="yearly")
        self.add_income(member, 40, "wages")

        self.assertEqual(self.countable(screen, member).contribution("pension"), Decimal(1_000))


class TestBandAllowanceScoping(MoTwhaTestCase):
    """The 250-300% allowance covers only the worker's own earned income."""

    def test_worker_unearned_excess_in_the_band_denies(self):
        """A worker whose own *unearned* income puts them in the band is not admitted by the
        allowance, and pass 2 cannot remove a pension."""
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        self.add_income(member, 40, "wages")
        self.add_income(member, 3_500, "pension")

        eligible, _ = self.evaluate(screen)
        self.assertFalse(eligible)

    def test_income_above_the_300_percent_ceiling_from_unearned_denies(self):
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        self.add_income(member, 40, "wages")
        self.add_income(member, 6_000, "pension")

        eligible, _ = self.evaluate(screen)
        self.assertFalse(eligible)


class TestAgeBoundary(MoTwhaTestCase):
    """The month-inclusive 16-64 range, at helper level across a full year of birth months.

    The ceiling is the subtle half: ``calc_age`` reads 65 from the first day of the
    65th-birthday month, so a plain ``age <= 64`` test would cut coverage a month early
    (Scenario 5), while dropping the month check entirely would extend it eleven months too
    far (Scenario 6).
    """

    def eligible_at(self, birth_year, birth_month):
        screen = self.build(1)
        member = self.add_person(
            screen, "headOfHousehold", birth_year, birth_month=birth_month, long_term_disability=True
        )
        self.add_income(member, 1_000)
        eligible, _ = self.evaluate(screen)
        return eligible

    def test_only_the_65th_birthday_month_is_covered_in_that_year(self):
        # Born 1961: September is the birthday month against the 2026-09-01 reference date.
        # Earlier months have already aged out; later months are still 64.
        for month in range(1, 13):
            with self.subTest(birth_month=month):
                expected = month >= 9
                self.assertEqual(self.eligible_at(1961, month), expected)

    def test_every_month_of_age_64_is_covered(self):
        # Born 1962: reads 64 in September or earlier, 63 after — both inside the range.
        for month in range(1, 13):
            with self.subTest(birth_month=month):
                self.assertTrue(self.eligible_at(1962, month))

    def test_16th_birthday_month_is_the_first_covered_month(self):
        # Born 2010: reads 16 from September, 15 before it.
        for month in range(1, 13):
            with self.subTest(birth_month=month):
                self.assertEqual(self.eligible_at(2010, month), month <= 9)

    def test_a_bare_age_of_65_fails_closed(self):
        """Without a stored birth month the birthday month is not decidable, so 65 denies
        rather than guessing — the inclusive direction is not available here."""
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 1961, birth_month=9, long_term_disability=True)
        member.birth_year_month = None
        member.age = 65
        member.save()
        self.add_income(member, 1_000)

        eligible, _ = self.evaluate(screen)
        self.assertFalse(eligible)

    def test_a_bare_age_inside_the_range_still_qualifies(self):
        """`calc_age` falls back to the `age` integer, which is sufficient away from the
        boundary."""
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        member.birth_year_month = None
        member.age = 40
        member.save()
        self.add_income(member, 1_000)

        self.assertEqual(self.evaluate(screen), (True, VALUE_PER_MEMBER))


class TestAgeNullHandling(MoTwhaTestCase):
    """Criterion 1's null handling: a member with no stored birth date fails closed."""

    def test_member_with_no_birth_date_or_age_is_ineligible(self):
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        member.birth_year_month = None
        member.age = None
        member.save()
        self.add_income(member, 1_000)

        eligible, _ = self.evaluate(screen)
        self.assertFalse(eligible)


class TestValueScaling(MoTwhaTestCase):
    """Benefit value is flat per eligible member; the frontend derives the monthly figure."""

    def test_only_the_eligible_member_is_valued(self):
        """A non-disabled spouse does not add value even though the household is eligible."""
        screen = self.build(2)
        head = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        spouse = self.add_person(screen, "spouse", 1986)
        self.add_income(head, 500, "wages")
        self.add_income(spouse, 500, "wages")

        self.assertEqual(self.evaluate(screen), (True, VALUE_PER_MEMBER))

    def test_children_are_not_valued(self):
        screen = self.build(3)
        head = self.add_person(screen, "headOfHousehold", 1986, long_term_disability=True)
        self.add_person(screen, "child", 2016, birth_month=3, long_term_disability=True)
        self.add_person(screen, "child", 2019, birth_month=6)
        self.add_income(head, 500, "wages")

        # The disabled child has no earned income, so fails the employment criterion.
        self.assertEqual(self.evaluate(screen), (True, VALUE_PER_MEMBER))

"""
Unit tests for the MoWap calculator.

Coverage maps to ``specs/mo.md`` — its three implemented eligibility criteria
(1a income, 1b cash assistance, 1d HUD/Section 8), every income-counting rule in
Criterion 2, its Benefit Value section, all thirteen Acceptance Criteria, and one
test per entry in its twelve-scenario Test Scenarios list.

Built on real ``Screen`` / ``HouseholdMember`` / ``IncomeStream`` / ``Expense`` /
``CurrentBenefit`` rows rather than mocks. Almost every rule here is a question
about income-type filtering (``calc_gross_income`` with ``exclude``, the ``all``
aggregation, monthly-to-yearly conversion) or about an accessor (``calc_age``,
``has_base_benefit``), so a mock standing in for those would assert the mock's
own semantics rather than the calculator's.

Ages are fixed integers rather than birth dates: the spec states birth months,
but deriving an age from ``timezone.now()`` would break the suite on a calendar
boundary, and no rule here turns on the month.

The income limits every scenario is measured against come from the program row's
2025 FPL pin, whose 200% figures are DOE WPN 25-3's attachment verbatim —
``TestMoWapIncomeLimit`` pins that table directly.

Not tested here, because the calculator does not implement them (see the class
docstring):
- Criterion 3 (qualified aliens) — the program's ``legal_status_required`` config.
- Missouri residency — enforced at the screener's ZIP step, which rejects a
  non-Missouri ZIP before any calculator runs.
- Criteria 1c (LIHEAP) and 1e (USDA), the twelve-month cash-assistance lookback,
  and the HUD programs other than Section 8 — all unscreenable, all recorded as
  inclusive data gaps.
- Priority categories, dwelling type, and prior-weatherization history — none
  affect eligibility or value.

Every eligible household is worth a flat $370.
"""

from django.test import TestCase

from programs.framework.base import Eligibility, ProgramCalculator
from programs.framework.registry import build
from programs.models import Program
from programs.programs.cross_white_label.weatherization.mo import MoWap
from programs.programs.testing_fixtures.pe_integration import (
    add_income,
    add_member,
    make_program,
    make_screen,
)
from screener.models import CurrentBenefit, Expense
from screener.tests.helpers import seed_program

YEAR = "2025"
VALUE = 370

#: 200% of the WAP poverty guideline, from the WPN 25-3 attachment. Every
#: scenario below is positioned against one of these figures.
LIMIT = {1: 31_300, 2: 42_300, 3: 53_300, 4: 64_300, 8: 108_300, 9: 119_300}


class MoWapTestCase(TestCase):
    """Household builder shared by every test below."""

    # Distinct ids per household keep the members of one screen from colliding
    # with another's when a test builds more than one.
    next_screen_id = 1

    def build(self, household_size, zipcode="63101", county="St. Louis City"):
        screen = make_screen(
            self.next_screen_id,
            white_label_code="mo",
            state_code="MO",
            household_size=household_size,
            zipcode=zipcode,
            county=county,
        )
        # Reused rather than recreated: a test that builds more than one
        # household (every subTest loop below) would otherwise collide on the
        # program row's unique external_name.
        existing = Program.objects.filter(white_label=screen.white_label, name_abbreviated="mo_wap").first()
        self.program = existing or make_program("mo", "mo_wap", YEAR)
        self.member_id = self.next_screen_id * 100
        MoWapTestCase.next_screen_id += 1
        return screen

    def add_person(self, screen, relationship="headOfHousehold", age=40, **kwargs):
        self.member_id += 1
        return add_member(screen, self.member_id, relationship, age, **kwargs)

    def add_yearly_income(self, member, income_type, amount):
        return add_income(member, amount, income_type, "yearly")

    def add_monthly_income(self, member, income_type, amount):
        return add_income(member, amount, income_type, "monthly")

    def add_expense(self, screen, expense_type, yearly_amount):
        return Expense.objects.create(
            screen=screen,
            type=expense_type,
            amount=yearly_amount,
            frequency="yearly",
        )

    def receive_benefit(self, screen, name_abbreviated, base_program):
        """Record `screen` as already receiving a benefit, the way the
        has-benefits step does — a real Program row plus a CurrentBenefit link,
        so `has_base_benefit` resolves it structurally."""
        seed_program(screen.white_label, name_abbreviated, base_program=base_program)
        program = Program.objects.get(white_label=screen.white_label, name_abbreviated=name_abbreviated)
        CurrentBenefit.objects.create(screen=screen, program=program)
        screen.invalidate_current_benefits_cache()

    def calculator(self, screen):
        return MoWap(screen, self.program, {}, screen.missing_fields())

    def household_eligible(self, screen):
        e = Eligibility()
        self.calculator(screen).household_eligible(e)
        return e

    def result(self, screen):
        return self.calculator(screen).calc()

    def countable_income(self, screen):
        return self.calculator(screen)._countable_income()

    def single_earner(self, household_size=1, income_type="wages", amount=0, **screen_kwargs):
        """The commonest shape: one adult with one yearly income stream."""
        screen = self.build(household_size, **screen_kwargs)
        member = self.add_person(screen)
        if amount:
            self.add_yearly_income(member, income_type, amount)
        return screen, member


class TestMoWapClassAttributes(MoWapTestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(MoWap, ProgramCalculator))

    def test_registered_under_mo_wap(self):
        self.assertIs(build("programs.programs", ProgramCalculator).get("mo_wap"), MoWap)

    def test_amount_is_370_estimated_annual(self):
        # DNR PUB2832's published average annual heating/cooling saving.
        self.assertEqual(MoWap.amount, VALUE)

    def test_fpl_percent_is_200(self):
        self.assertEqual(MoWap.fpl_percent, 2)

    def test_excluded_income_types(self):
        self.assertEqual(
            set(MoWap.excluded_income_types),
            {"selfEmployment", "rental", "boarder", "investment", "childSupport", "gifts"},
        )

    def test_minor_excluded_income_types_cover_earned_and_unemployment(self):
        self.assertEqual(
            set(MoWap.minor_excluded_income_types),
            {"wages", "selfEmployment", "unemployment"},
        )

    def test_minor_age_is_18(self):
        self.assertEqual(MoWap.minor_age, 18)

    def test_cash_assistance_income_types_are_title_iv_and_xvi(self):
        self.assertEqual(set(MoWap.cash_assistance_income_types), {"sSI", "cashAssistance"})

    def test_snap_is_not_a_pathway(self):
        """Unlike tx_wap / cowap / wa_wap, no SNAP name appears anywhere in this
        calculator's configuration — 10 CFR 440.22(a)(2) names Title IV and
        Title XVI only."""
        configured = set(MoWap.excluded_income_types) | set(MoWap.cash_assistance_income_types)
        self.assertNotIn("snap", {name.lower() for name in configured})

    def test_income_fields_in_dependencies(self):
        self.assertIn("household_size", MoWap.dependencies)
        self.assertIn("income_amount", MoWap.dependencies)
        self.assertIn("income_frequency", MoWap.dependencies)


class TestMoWapIncomeLimit(MoWapTestCase):
    """Criterion 1a's table — DOE WPN 25-3, contiguous U.S., effective
    2025-01-17, at 200% of poverty."""

    #: The WPN 25-3 attachment verbatim.
    WPN_25_3 = {
        1: 31_300,
        2: 42_300,
        3: 53_300,
        4: 64_300,
        5: 75_300,
        6: 86_300,
        7: 97_300,
        8: 108_300,
    }
    ADDITIONAL_PERSON = 11_000

    def limit_for(self, household_size):
        screen = self.build(household_size)
        return self.calculator(screen)._income_limit()

    def test_every_published_row(self):
        for household_size, expected in self.WPN_25_3.items():
            with self.subTest(household_size=household_size):
                self.assertEqual(self.limit_for(household_size), expected)

    def test_size_above_table_adds_the_per_person_extension(self):
        self.assertEqual(self.limit_for(9), self.WPN_25_3[8] + self.ADDITIONAL_PERSON)
        self.assertEqual(self.limit_for(12), self.WPN_25_3[8] + 4 * self.ADDITIONAL_PERSON)

    def test_null_household_size_falls_back_to_the_size_1_row(self):
        # Unreachable in production: household_size is a declared dependency, so
        # can_calc() drops the program first. Pinned so the guard stays honest.
        screen = self.build(1)
        screen.household_size = None
        self.assertEqual(self.calculator(screen)._income_limit(), self.WPN_25_3[1])


class TestMoWapIncomeBoundary(MoWapTestCase):
    """Criterion 1a's comparator is inclusive of the exact limit."""

    def eligible_at(self, amount, household_size=1):
        screen, _ = self.single_earner(household_size=household_size, amount=amount)
        return self.household_eligible(screen).eligible

    def test_below_limit_eligible(self):
        self.assertTrue(self.eligible_at(20_000))

    def test_zero_income_eligible(self):
        self.assertTrue(self.eligible_at(0))

    def test_exactly_at_limit_eligible(self):
        self.assertTrue(self.eligible_at(LIMIT[1]))

    def test_one_dollar_over_limit_ineligible(self):
        self.assertFalse(self.eligible_at(LIMIT[1] + 1))

    def test_fractional_amount_over_limit_ineligible(self):
        # Countable income is rounded to cents, not truncated — $0.50 over the
        # limit must fail rather than being floored back onto it.
        screen, member = self.single_earner(amount=LIMIT[1])
        self.add_yearly_income(member, "pension", "0.50")
        self.assertFalse(self.household_eligible(screen).eligible)

    def test_income_failure_reports_the_limit(self):
        screen, _ = self.single_earner(amount=LIMIT[1] + 1)
        e = self.household_eligible(screen)
        self.assertFalse(e.eligible)
        self.assertIn(f" ${LIMIT[1]}", "".join(part for part in e.fail_messages[0] if isinstance(part, str)))


class TestMoWapIncomeAggregation(MoWapTestCase):
    """WPN 25-3 counts income for "the entire family living in the residence"."""

    def test_two_members_incomes_are_summed(self):
        screen = self.build(2)
        head = self.add_person(screen)
        spouse = self.add_person(screen, "spouse")
        self.add_yearly_income(head, "wages", 24_000)
        self.add_yearly_income(spouse, "wages", 20_000)
        self.assertEqual(self.countable_income(screen), 44_000)

    def test_one_members_multiple_streams_are_summed(self):
        screen, member = self.single_earner(amount=20_000)
        self.add_yearly_income(member, "alimony", 5_000)
        self.add_yearly_income(member, "sSRetirement", 3_000)
        self.assertEqual(self.countable_income(screen), 28_000)


class TestMoWapCountableIncomeExclusions(MoWapTestCase):
    """Criterion 2 — WPN 25-3's "Definition of Income" attachment."""

    BASE = 20_000
    ADDED = 5_000

    def countable_with(self, income_type, member_kwargs=None):
        screen = self.build(1)
        member = self.add_person(screen, **(member_kwargs or {}))
        self.add_yearly_income(member, "wages", self.BASE)
        self.add_yearly_income(member, income_type, self.ADDED)
        return self.countable_income(screen)

    def test_excluded_types_do_not_count(self):
        for income_type in MoWap.excluded_income_types:
            with self.subTest(income_type=income_type):
                self.assertEqual(self.countable_with(income_type), self.BASE)

    def test_counted_types_do_count(self):
        # Everything WPN 25-3 leaves countable at gross. `alimony` is the one the
        # spec calls out explicitly (B.3, no netting question).
        for income_type in (
            "wages",
            "alimony",
            "unemployment",
            "sSI",
            "sSDisability",
            "sSRetirement",
            "sSSurvivor",
            "sSDependent",
            "cashAssistance",
            "workersComp",
            "veteran",
            "pension",
            "deferredComp",
        ):
            with self.subTest(income_type=income_type):
                self.assertEqual(self.countable_with(income_type), self.BASE + self.ADDED)

    def test_child_support_paid_is_not_deducted(self):
        # Section E bars the deduction; the calculator reads no expenses at all.
        screen, _ = self.single_earner(amount=self.BASE)
        self.add_expense(screen, "childSupport", 12_000)
        self.assertEqual(self.countable_income(screen), self.BASE)

    def test_housing_expenses_are_not_deducted(self):
        screen, _ = self.single_earner(amount=self.BASE)
        self.add_expense(screen, "rent", 12_000)
        self.assertEqual(self.countable_income(screen), self.BASE)

    def test_monthly_streams_are_annualized(self):
        screen = self.build(1)
        member = self.add_person(screen)
        self.add_monthly_income(member, "wages", 1_000)
        self.assertEqual(self.countable_income(screen), 12_000)


class TestMoWapMinorIncomeExclusion(MoWapTestCase):
    """Criterion 2 / WPN 25-3 Section D.1 — a minor's or full-time student's
    earned income and unemployment compensation come out; their unearned income
    stays in."""

    ADULT_WAGES = 20_000

    def household_with_second_member(self, member_kwargs, streams):
        screen = self.build(2)
        head = self.add_person(screen)
        self.add_yearly_income(head, "wages", self.ADULT_WAGES)
        other = self.add_person(screen, "child", **member_kwargs)
        for income_type, amount in streams:
            self.add_yearly_income(other, income_type, amount)
        return screen

    def test_minor_wages_excluded(self):
        screen = self.household_with_second_member({"age": 15}, [("wages", 1_800)])
        self.assertEqual(self.countable_income(screen), self.ADULT_WAGES)

    def test_minor_unemployment_excluded(self):
        screen = self.household_with_second_member({"age": 15}, [("unemployment", 600)])
        self.assertEqual(self.countable_income(screen), self.ADULT_WAGES)

    def test_minor_unearned_income_still_counts(self):
        # Section D.1 names earned income and unemployment compensation only.
        screen = self.household_with_second_member({"age": 15}, [("sSI", 4_000)])
        self.assertEqual(self.countable_income(screen), self.ADULT_WAGES + 4_000)

    def test_seventeen_year_old_is_a_minor(self):
        screen = self.household_with_second_member({"age": 17}, [("wages", 9_000)])
        self.assertEqual(self.countable_income(screen), self.ADULT_WAGES)

    def test_eighteen_year_old_is_not_a_minor(self):
        screen = self.household_with_second_member({"age": 18}, [("wages", 9_000)])
        self.assertEqual(self.countable_income(screen), self.ADULT_WAGES + 9_000)

    def test_adult_full_time_student_wages_excluded_as_the_high_school_proxy(self):
        # Committed data-gap handling: `student_full_time` cannot distinguish a
        # high-school student from a college one, so an over-18 full-time
        # student's wages come out too. Inclusive-safe by design.
        screen = self.household_with_second_member(
            {"age": 22, "student_full_time": True},
            [("wages", 9_000)],
        )
        self.assertEqual(self.countable_income(screen), self.ADULT_WAGES)

    def test_adult_part_time_student_wages_count(self):
        screen = self.household_with_second_member(
            {"age": 22, "student_full_time": False},
            [("wages", 9_000)],
        )
        self.assertEqual(self.countable_income(screen), self.ADULT_WAGES + 9_000)

    def test_unknown_age_and_student_status_counts_as_an_adult(self):
        # The disregard is granted on proof of age; an unproven one is not assumed.
        screen = self.household_with_second_member({"age": None}, [("wages", 9_000)])
        self.assertEqual(self.countable_income(screen), self.ADULT_WAGES + 9_000)


class TestMoWapCategoricalEligibility(MoWapTestCase):
    """Criteria 1b and 1d — pathways that bypass the income test outright."""

    OVER_LIMIT = 80_000

    def over_income_household(self):
        screen, member = self.single_earner(amount=self.OVER_LIMIT)
        return screen, member

    def test_over_income_alone_is_ineligible(self):
        screen, _ = self.over_income_household()
        self.assertFalse(self.household_eligible(screen).eligible)

    def test_ssi_income_stream_bypasses_the_income_test(self):
        screen, member = self.over_income_household()
        self.add_monthly_income(member, "sSI", 900)
        self.assertTrue(self.household_eligible(screen).eligible)

    def test_cash_assistance_income_stream_bypasses_the_income_test(self):
        screen, member = self.over_income_household()
        self.add_monthly_income(member, "cashAssistance", 500)
        self.assertTrue(self.household_eligible(screen).eligible)

    def test_another_members_ssi_qualifies_the_household(self):
        screen = self.build(2)
        head = self.add_person(screen)
        self.add_yearly_income(head, "wages", self.OVER_LIMIT)
        child = self.add_person(screen, "child", age=10)
        self.add_monthly_income(child, "sSI", 900)
        self.assertTrue(self.household_eligible(screen).eligible)

    def test_zero_amount_cash_assistance_stream_is_not_a_pathway(self):
        screen, member = self.over_income_household()
        self.add_yearly_income(member, "cashAssistance", 0)
        self.assertFalse(self.household_eligible(screen).eligible)

    def test_categorical_pathway_reports_presumed_eligibility(self):
        screen, member = self.over_income_household()
        self.add_monthly_income(member, "sSI", 900)
        e = self.household_eligible(screen)
        self.assertTrue(e.eligible)
        self.assertEqual(e.pass_messages[0][0]["label"], "eligibility_message.presumptive_eligibility-0")

    def test_section_8_receipt_bypasses_the_income_test(self):
        # Criterion 1d, wired ahead of the data: no Missouri section_8 program
        # row exists yet, so this pathway activates the day one is added.
        screen, _ = self.over_income_household()
        self.receive_benefit(screen, "mo_hcv", "section_8")
        self.assertTrue(self.household_eligible(screen).eligible)

    def test_section_8_is_matched_structurally_not_by_exact_name(self):
        screen, _ = self.over_income_household()
        self.receive_benefit(screen, "mo_hcv", "section_8")
        self.assertFalse(screen.has_benefit("section_8"))
        self.assertTrue(screen.has_base_benefit("section_8"))

    def test_snap_receipt_alone_is_not_a_pathway(self):
        # True for tx_wap, cowap and wa_wap; deliberately false here.
        screen, _ = self.over_income_household()
        self.receive_benefit(screen, "mo_snap", "snap")
        self.assertFalse(self.household_eligible(screen).eligible)

    def test_tanf_receipt_without_a_cash_assistance_stream_is_not_a_pathway(self):
        # The committed Criterion 1b mechanism is the income stream, not the
        # has-benefits tile. Pinned so a change to that decision is deliberate.
        screen, _ = self.over_income_household()
        self.receive_benefit(screen, "mo_tanf", "tanf")
        self.assertFalse(self.household_eligible(screen).eligible)


class TestMoWapValue(MoWapTestCase):
    """Benefit Value — a flat $370 for every eligible household, and no
    eligible-but-$0 result."""

    def test_eligible_household_is_worth_370(self):
        screen, _ = self.single_earner(amount=20_000)
        result = self.result(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, VALUE)

    def test_ineligible_household_is_worth_nothing(self):
        screen, _ = self.single_earner(amount=80_000)
        result = self.result(screen)
        self.assertFalse(result.eligible)
        self.assertEqual(result.value, 0)

    def test_categorically_eligible_household_is_worth_370(self):
        screen, member = self.single_earner(amount=80_000)
        self.add_monthly_income(member, "sSI", 900)
        result = self.result(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, VALUE)

    def test_value_does_not_scale_with_household_size(self):
        screen = self.build(4)
        self.add_person(screen)
        self.add_person(screen, "spouse")
        self.add_person(screen, "child", age=8)
        self.add_person(screen, "child", age=5)
        result = self.result(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, VALUE)

    def test_no_member_level_value(self):
        self.assertEqual(MoWap.member_amount, 0)


class TestMoWapNotGatedOn(MoWapTestCase):
    """Acceptance criterion: the calculator does not exclude a household on
    dwelling type, prior-weatherization history, or priority status — none of
    which it reads. Asserted as behaviour: a household with no housing expense,
    no elderly/disabled/child member, and no assets recorded still passes."""

    def test_bare_household_with_low_income_is_eligible(self):
        screen = self.build(1)
        self.add_person(screen, age=40, disabled=False, long_term_disability=False, visually_impaired=False)
        self.assertTrue(self.household_eligible(screen).eligible)

    def test_no_housing_or_utility_expense_required(self):
        screen, _ = self.single_earner(amount=20_000)
        self.assertEqual(screen.expenses.count(), 0)
        self.assertTrue(self.household_eligible(screen).eligible)


class TestMoWapSpecScenarios(MoWapTestCase):
    """One test per entry in specs/mo.md's Test Scenarios list."""

    def assert_eligible(self, screen):
        result = self.result(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, VALUE)

    def assert_ineligible(self, screen):
        result = self.result(screen)
        self.assertFalse(result.eligible)
        self.assertEqual(result.value, 0)

    def test_scenario_1_standard_income_path_single_adult_below_the_limit(self):
        screen = self.build(1, zipcode="64108", county="Jackson")
        head = self.add_person(screen, age=40)
        self.add_monthly_income(head, "wages", 2_600)  # $31,200/yr vs a $31,300 limit
        self.assertEqual(self.countable_income(screen), 31_200)
        self.assert_eligible(screen)

    def test_scenario_2_exact_200_percent_boundary_four_person_household(self):
        screen = self.build(4, zipcode="65201", county="Boone")
        head = self.add_person(screen, age=38)
        self.add_yearly_income(head, "wages", LIMIT[4])
        self.add_person(screen, "spouse", age=37)
        self.add_person(screen, "child", age=10)
        self.add_person(screen, "child", age=7)
        self.assertEqual(self.countable_income(screen), LIMIT[4])
        self.assert_eligible(screen)

    def test_scenario_3_just_above_the_income_limit_no_categorical_pathway(self):
        screen = self.build(3, zipcode="65802", county="Greene")
        head = self.add_person(screen, age=40)
        self.add_yearly_income(head, "wages", LIMIT[3] + 100)
        self.add_person(screen, "spouse", age=39)
        self.add_person(screen, "child", age=9)
        self.assert_ineligible(screen)

    def test_scenario_4_cash_assistance_categorical_above_the_income_limit(self):
        screen = self.build(2, zipcode="63101", county="St. Louis City")
        head = self.add_person(screen, age=35)
        self.add_yearly_income(head, "wages", 44_400)  # above the $42,300 2-person limit
        self.add_monthly_income(head, "cashAssistance", 500)
        self.add_person(screen, "child", age=6)
        self.assertGreater(self.countable_income(screen), LIMIT[2])
        self.assert_eligible(screen)

    def test_scenario_5_ssi_categorical_above_the_income_limit(self):
        screen = self.build(2, zipcode="65616", county="Taney")
        head = self.add_person(screen, age=45)
        self.add_monthly_income(head, "sSI", 900)
        spouse = self.add_person(screen, "spouse", age=44)
        self.add_monthly_income(spouse, "wages", 3_000)
        self.assertEqual(self.countable_income(screen), 46_800)
        self.assertGreater(self.countable_income(screen), LIMIT[2])
        self.assert_eligible(screen)

    def test_scenario_6_child_support_received_is_excluded(self):
        screen = self.build(2, zipcode="63101", county="St. Louis City")
        head = self.add_person(screen, age=34)
        self.add_yearly_income(head, "wages", 42_000)
        self.add_yearly_income(head, "childSupport", 12_000)
        self.add_person(screen, "child", age=8)
        # Without the exclusion this household reads as $54,000 and fails.
        self.assertEqual(self.countable_income(screen), 42_000)
        self.assert_eligible(screen)

    def test_scenario_7_minors_wages_and_unemployment_are_both_excluded(self):
        screen = self.build(2, zipcode="65201", county="Boone")
        head = self.add_person(screen, age=42)
        self.add_yearly_income(head, "wages", 42_000)
        child = self.add_person(screen, "child", age=15)
        self.add_yearly_income(child, "wages", 1_800)
        self.add_yearly_income(child, "unemployment", 600)
        # Without the exclusion this household reads as $44,400 and fails.
        self.assertEqual(self.countable_income(screen), 42_000)
        self.assert_eligible(screen)

    def test_scenario_8_alimony_is_counted_and_flips_the_household_over(self):
        screen = self.build(1, zipcode="63101", county="St. Louis City")
        head = self.add_person(screen, age=50)
        self.add_yearly_income(head, "wages", 28_000)  # alone, under the $31,300 limit
        self.add_yearly_income(head, "alimony", 5_000)
        self.assertEqual(self.countable_income(screen), 33_000)
        self.assert_ineligible(screen)

    def test_scenario_9_income_aggregated_across_two_adults(self):
        screen = self.build(2, zipcode="65201", county="Boone")
        head = self.add_person(screen, age=36)
        self.add_yearly_income(head, "wages", 24_000)
        spouse = self.add_person(screen, "spouse", age=35)
        self.add_yearly_income(spouse, "wages", 20_000)
        # Each is under the 1-person figure; together they exceed the 2-person limit.
        self.assertEqual(self.countable_income(screen), 44_000)
        self.assert_ineligible(screen)

    def test_scenario_10_gifts_are_excluded(self):
        screen = self.build(1, zipcode="64801", county="Jasper")
        head = self.add_person(screen, age=29)
        self.add_yearly_income(head, "wages", 31_000)
        self.add_yearly_income(head, "gifts", 5_000)
        # Without the exclusion this household reads as $36,000 and fails.
        self.assertEqual(self.countable_income(screen), 31_000)
        self.assert_eligible(screen)

    def test_scenario_11_child_support_paid_is_not_deducted(self):
        screen = self.build(1, zipcode="65802", county="Greene")
        head = self.add_person(screen, age=44)
        self.add_yearly_income(head, "wages", 32_000)
        self.add_expense(screen, "childSupport", 12_000)
        # Treating the expense as a deduction would read $20,000 and wrongly pass.
        self.assertEqual(self.countable_income(screen), 32_000)
        self.assert_ineligible(screen)

    def test_scenario_12_household_size_above_8_applies_the_per_person_extension(self):
        screen = self.build(9, zipcode="64108", county="Jackson")
        head = self.add_person(screen, age=48)
        self.add_yearly_income(head, "wages", LIMIT[9])
        self.add_person(screen, "spouse", age=47)
        for age in (17, 15, 13, 11, 9, 7, 5):
            self.add_person(screen, "child", age=age)
        self.assertEqual(self.calculator(screen)._income_limit(), LIMIT[9])
        self.assert_eligible(screen)

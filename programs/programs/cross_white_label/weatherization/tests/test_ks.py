"""
Unit tests for the KsWap calculator.

Coverage maps to ``specs/ks.md`` — its four calculator-implemented criteria
(1 income, 2 countable income, 3 categorical routes, 6 the household unit),
its Benefit Value section, and one test per entry in its sixteen-scenario Test
Scenarios list.

Built on real ``Screen`` / ``HouseholdMember`` / ``IncomeStream`` / ``Expense`` /
``CurrentBenefit`` rows rather than mocks. Almost every rule here is a question
about income-type filtering (``calc_gross_income`` with ``exclude``, the ``all``
aggregation, monthly-to-yearly conversion) or about an accessor (``calc_age``,
``has_base_benefit``), so a mock standing in for those would assert the mock's
own semantics rather than the calculator's.

Ages are fixed integers rather than birth dates: the spec's scenarios state
birth years and months, but deriving an age from ``timezone.now()`` would break
the suite on a calendar boundary, and no rule here turns on the month.

The income limits every scenario is measured against come from the program
row's 2026 FPL pin, whose 200% figures reproduce KHRC's printed table exactly
at every size from 1 to 16 — ``TestKsWapIncomeLimit`` pins that table directly.

Not tested here, because the calculator does not implement them (see the class
docstring):
- Criterion 4 (at least one citizen or Qualified Alien) — the program's
  ``legal_status_required`` config.
- Criterion 5 (the dwelling is in Kansas) — white-label routing.
- The HUD and USDA routes beyond Section 8, and cash assistance received
  earlier in the preceding twelve months — all unscreenable, all recorded as
  disclosure-only data gaps.
- Priority order, occupancy, dwelling type, and the 15-year re-weatherization
  bar — none affect eligibility or value.

Every eligible household is worth a flat $7,475.
"""

from django.test import TestCase

from programs.framework.base import Eligibility, ProgramCalculator
from programs.framework.registry import build
from programs.models import Program
from programs.programs.cross_white_label.weatherization.ks import KsWap
from programs.programs.testing_fixtures.pe_integration import (
    add_income,
    add_member,
    make_program,
    make_screen,
)
from screener.models import CurrentBenefit, Expense
from screener.tests.helpers import seed_program

YEAR = "2026"
VALUE = 7_475

#: 200% of the 2026 federal poverty guideline — the table KHRC prints on its
#: own application. Every scenario below is positioned against one of these.
LIMIT = {1: 31_920, 2: 43_280, 3: 54_640, 4: 66_000, 8: 111_440, 10: 134_160, 16: 202_320}


class KsWapTestCase(TestCase):
    """Household builder shared by every test below."""

    # Distinct ids per household keep the members of one screen from colliding
    # with another's when a test builds more than one.
    next_screen_id = 1

    def build(self, household_size, zipcode="66603", county="Shawnee County"):
        screen = make_screen(
            self.next_screen_id,
            white_label_code="ks",
            state_code="KS",
            household_size=household_size,
            zipcode=zipcode,
            county=county,
        )
        # Reused rather than recreated: a test that builds more than one
        # household (every subTest loop below) would otherwise collide on the
        # program row's unique external_name.
        existing = Program.objects.filter(white_label=screen.white_label, name_abbreviated="ks_wap").first()
        self.program = existing or make_program("ks", "ks_wap", YEAR)
        self.member_id = self.next_screen_id * 100
        KsWapTestCase.next_screen_id += 1
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
        return KsWap(screen, self.program, {}, screen.missing_fields())

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


class TestKsWapClassAttributes(KsWapTestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(KsWap, ProgramCalculator))

    def test_registered_under_ks_wap(self):
        self.assertIs(build("programs.programs", ProgramCalculator).get("ks_wap"), KsWap)

    def test_amount_is_7475_lump_sum(self):
        # Kansas's published average program-operations cost per dwelling unit,
        # $7,474.93 in the 2025 state plan, rounded to the dollar.
        self.assertEqual(KsWap.amount, VALUE)

    def test_fpl_percent_is_200(self):
        self.assertEqual(KsWap.fpl_percent, 2)

    def test_excluded_income_types(self):
        self.assertEqual(
            set(KsWap.excluded_income_types),
            {"childSupport", "gifts", "selfEmployment", "rental", "boarder", "investment"},
        )

    def test_student_excluded_income_types_cover_earned_and_unemployment(self):
        # `selfEmployment` is the third earned stream and is already excluded
        # for every member, so it does not repeat here.
        self.assertEqual(set(KsWap.student_excluded_income_types), {"wages", "unemployment"})

    def test_minor_age_is_18(self):
        self.assertEqual(KsWap.minor_age, 18)

    def test_categorical_base_programs_cover_all_four_routes(self):
        self.assertEqual(set(KsWap.categorical_base_programs), {"ssi", "tanf", "liheap", "section_8"})

    def test_categorical_income_types_back_the_ssi_and_tanf_routes(self):
        self.assertEqual(set(KsWap.categorical_income_types), {"sSI", "cashAssistance"})

    def test_snap_is_not_a_pathway(self):
        """Unlike tx_wap, cowap and wa_wap, no SNAP name appears anywhere in
        this calculator's configuration — Kansas's categorical list names SSI,
        TANF and LIEAP, and the DOE expansions reach HUD and USDA."""
        configured = (
            set(KsWap.excluded_income_types)
            | set(KsWap.categorical_income_types)
            | set(KsWap.categorical_base_programs)
        )
        self.assertNotIn("snap", {name.lower() for name in configured})

    def test_income_fields_in_dependencies(self):
        self.assertIn("household_size", KsWap.dependencies)
        self.assertIn("income_amount", KsWap.dependencies)
        self.assertIn("income_frequency", KsWap.dependencies)


class TestKsWapIncomeLimit(KsWapTestCase):
    """Criterion 1's table — 200% of the 2026 federal poverty guideline, which
    is the table KHRC prints on its standardized application (revised
    2026-02-23) at every size it publishes."""

    #: KHRC's printed table verbatim, both of its interleaved columns.
    KHRC_TABLE = {
        1: 31_920,
        2: 43_280,
        3: 54_640,
        4: 66_000,
        5: 77_360,
        6: 88_720,
        7: 100_080,
        8: 111_440,
        9: 122_800,
        10: 134_160,
        11: 145_520,
        12: 156_880,
        13: 168_240,
        14: 179_600,
        15: 190_960,
        16: 202_320,
    }

    def limit_for(self, household_size):
        screen = self.build(household_size)
        return self.calculator(screen)._income_limit()

    def test_every_published_row(self):
        """Sizes 9 and up are the reason the calculator reads `get_limit` rather
        than indexing `as_dict()`: the dict holds explicit rows only to 8, and
        the helper's per-additional-person extension reproduces KHRC's printed
        figures for 9 through 16 exactly."""
        for household_size, expected in self.KHRC_TABLE.items():
            with self.subTest(household_size=household_size):
                self.assertEqual(self.limit_for(household_size), expected)

    def test_size_above_the_published_table_still_extends(self):
        self.assertEqual(self.limit_for(17), self.KHRC_TABLE[16] + 2 * 5_680)

    def test_null_household_size_yields_no_limit(self):
        # Unreachable in production: household_size is a declared dependency,
        # so can_calc() drops the program first. Pinned so the guard stays
        # honest rather than raising or comparing against a fabricated row.
        screen = self.build(1)
        screen.household_size = None
        self.assertIsNone(self.calculator(screen)._income_limit())


class TestKsWapIncomeBoundary(KsWapTestCase):
    """Criterion 1's comparator is inclusive of the exact limit."""

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

    def test_null_household_size_passes_the_income_criterion_unmeasured(self):
        # The limit is indexed to the size; with no size there is no row to
        # compare against, so the criterion is met rather than guessed at — and
        # no pass message claims a limit the household did not have to clear.
        screen, _ = self.single_earner(amount=500_000)
        screen.household_size = None
        e = self.household_eligible(screen)
        self.assertTrue(e.eligible)
        self.assertEqual(e.pass_messages, [])


class TestKsWapIncomeAggregation(KsWapTestCase):
    """Criterion 6 — income is summed over the family unit as entered."""

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


class TestKsWapCountableIncomeExclusions(KsWapTestCase):
    """Criterion 2 — DOE WPN 25-3's "Definition of Income" attachment, which
    Kansas adopts wholesale rather than defining an income rule of its own."""

    BASE = 20_000
    ADDED = 5_000

    def countable_with(self, income_type, member_kwargs=None):
        screen = self.build(1)
        member = self.add_person(screen, **(member_kwargs or {}))
        self.add_yearly_income(member, "wages", self.BASE)
        self.add_yearly_income(member, income_type, self.ADDED)
        return self.countable_income(screen)

    def test_excluded_types_do_not_count(self):
        for income_type in KsWap.excluded_income_types:
            with self.subTest(income_type=income_type):
                self.assertEqual(self.countable_with(income_type), self.BASE)

    def test_counted_types_do_count(self):
        # Everything WPN 25-3 leaves countable at gross. `alimony` is the one
        # the notice names explicitly (B.3, no netting question).
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


class TestKsWapStudentIncomeExclusion(KsWapTestCase):
    """Criterion 2 / WPN 25-3 Section D.1 — earned income and unemployment
    compensation come out for a member under 18, or for a full-time student of
    any age. Their unearned income stays in."""

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

    def test_eighteen_year_old_who_is_not_a_student_counts(self):
        # The age half of Section D.1 is "under the age of 18", exclusive.
        screen = self.household_with_second_member({"age": 18}, [("wages", 9_000)])
        self.assertEqual(self.countable_income(screen), self.ADULT_WAGES + 9_000)

    def test_full_time_student_is_excluded_at_any_age(self):
        """Data Gap 6. Section D.1's "(or full-time high school students)"
        clause is honoured for any full-time student, because MFB records no
        level of schooling to distinguish high school from college. Excluding
        too widely only lowers countable income, so it can only widen results
        — never turn an eligible household ineligible."""
        for age in (18, 19, 22, 45):
            with self.subTest(age=age):
                screen = self.household_with_second_member(
                    {"age": age, "student": True, "student_full_time": True},
                    [("wages", 9_000)],
                )
                self.assertEqual(self.countable_income(screen), self.ADULT_WAGES)

    def test_part_time_student_counts(self):
        screen = self.household_with_second_member(
            {"age": 20, "student": True, "student_full_time": False},
            [("wages", 9_000)],
        )
        self.assertEqual(self.countable_income(screen), self.ADULT_WAGES + 9_000)

    def test_full_time_flag_without_student_does_not_exclude(self):
        """`student_full_time` is only meaningful alongside `student`. Nothing
        enforces that server-side, so a direct API write can set the flag on a
        non-student — whose wages Section D.1 still counts."""
        for student in (False, None):
            with self.subTest(student=student):
                screen = self.household_with_second_member(
                    {"age": 30, "student": student, "student_full_time": True},
                    [("wages", 9_000)],
                )
                self.assertEqual(self.countable_income(screen), self.ADULT_WAGES + 9_000)

    def test_unknown_age_counts_as_an_adult(self):
        # The age disregard is granted on proof of age; an unproven one is not
        # assumed.
        screen = self.household_with_second_member({"age": None}, [("wages", 9_000)])
        self.assertEqual(self.countable_income(screen), self.ADULT_WAGES + 9_000)

    def test_unknown_age_full_time_student_is_still_excluded(self):
        # The student half of the clause does not depend on age at all.
        screen = self.household_with_second_member(
            {"age": None, "student": True, "student_full_time": True},
            [("wages", 9_000)],
        )
        self.assertEqual(self.countable_income(screen), self.ADULT_WAGES)


class TestKsWapCategoricalEligibility(KsWapTestCase):
    """Criterion 3 — the routes that bypass the income test outright."""

    OVER_LIMIT = 80_000

    def over_income_household(self):
        screen, member = self.single_earner(amount=self.OVER_LIMIT)
        return screen, member

    def test_over_income_alone_is_ineligible(self):
        screen, _ = self.over_income_household()
        self.assertFalse(self.household_eligible(screen).eligible)

    def test_ssi_receipt_bypasses_the_income_test(self):
        screen, _ = self.over_income_household()
        self.receive_benefit(screen, "ks_ssi", "ssi")
        self.assertTrue(self.household_eligible(screen).eligible)

    def test_ssi_income_stream_bypasses_the_income_test(self):
        # The stream is a backstop to the current-benefit row: the
        # single-benefit toggle endpoint does not re-derive the row, so a
        # screen can carry the stream without it.
        screen, member = self.over_income_household()
        self.add_monthly_income(member, "sSI", 900)
        self.assertTrue(self.household_eligible(screen).eligible)

    def test_tanf_receipt_bypasses_the_income_test(self):
        # Kansas administers TANF as TAF; one program row, `ks_tanf`, backs both.
        screen, _ = self.over_income_household()
        self.receive_benefit(screen, "ks_tanf", "tanf")
        self.assertTrue(self.household_eligible(screen).eligible)

    def test_cash_assistance_income_stream_bypasses_the_income_test(self):
        # MFB files TANF dollars under `cashAssistance` and never under `tanf`,
        # so for TANF the stream test is required rather than a backstop.
        screen, member = self.over_income_household()
        self.add_monthly_income(member, "cashAssistance", 400)
        self.assertTrue(self.household_eligible(screen).eligible)

    def test_lieap_receipt_bypasses_the_income_test(self):
        screen, _ = self.over_income_household()
        self.receive_benefit(screen, "ks_lieap", "liheap")
        self.assertTrue(self.household_eligible(screen).eligible)

    def test_section_8_receipt_bypasses_the_income_test(self):
        # Wired ahead of the data: Kansas has no voucher row yet, so this
        # pathway activates the day one is added.
        screen, _ = self.over_income_household()
        self.receive_benefit(screen, "ks_hcv", "section_8")
        self.assertTrue(self.household_eligible(screen).eligible)

    def test_routes_are_matched_structurally_not_by_exact_name(self):
        for name_abbreviated, base_program in (
            ("ks_ssi", "ssi"),
            ("ks_tanf", "tanf"),
            ("ks_lieap", "liheap"),
            ("ks_hcv", "section_8"),
        ):
            with self.subTest(base_program=base_program):
                screen, _ = self.over_income_household()
                self.receive_benefit(screen, name_abbreviated, base_program)
                self.assertFalse(screen.has_benefit(base_program))
                self.assertTrue(screen.has_base_benefit(base_program))

    def test_another_members_ssi_stream_qualifies_the_household(self):
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

    def test_snap_receipt_alone_is_not_a_pathway(self):
        # True for tx_wap, cowap and wa_wap; deliberately false here.
        screen, _ = self.over_income_household()
        self.receive_benefit(screen, "ks_snap", "snap")
        self.assertFalse(self.household_eligible(screen).eligible)

    def test_categorical_route_does_not_require_the_income_test_too(self):
        # The disjunction is OR, never AND: an under-income household with no
        # benefit is eligible, and an over-income one with a benefit is too.
        screen, _ = self.single_earner(amount=20_000)
        self.assertTrue(self.household_eligible(screen).eligible)


class TestKsWapValue(KsWapTestCase):
    """Benefit Value — a flat $7,475 for every eligible household, and no
    eligible-but-$0 result."""

    def test_eligible_household_is_worth_7475(self):
        screen, _ = self.single_earner(amount=20_000)
        result = self.result(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, VALUE)

    def test_ineligible_household_is_worth_nothing(self):
        screen, _ = self.single_earner(amount=80_000)
        result = self.result(screen)
        self.assertFalse(result.eligible)
        self.assertEqual(result.value, 0)

    def test_categorically_eligible_household_is_worth_7475(self):
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
        self.assertEqual(KsWap.member_amount, 0)


class TestKsWapNotGatedOn(KsWapTestCase):
    """The calculator does not exclude a household on tenure, occupancy,
    dwelling type, prior-weatherization history or priority status — none of
    which it reads. Asserted as behaviour: a household with no housing expense,
    no elderly/disabled/child member and no assets still passes."""

    def test_bare_household_with_low_income_is_eligible(self):
        screen = self.build(1)
        self.add_person(screen, age=40, disabled=False, long_term_disability=False, visually_impaired=False)
        self.assertTrue(self.household_eligible(screen).eligible)

    def test_no_housing_or_utility_expense_required(self):
        screen, _ = self.single_earner(amount=20_000)
        self.assertEqual(screen.expenses.count(), 0)
        self.assertTrue(self.household_eligible(screen).eligible)


class TestKsWapSpecScenarios(KsWapTestCase):
    """One test per entry in specs/ks.md's sixteen-scenario Test Scenarios
    list. Location appears in each because the screener collects it, but it
    never discriminates — criterion 5 is satisfied by the white label and
    Kansas's coverage is statewide."""

    def assert_eligible(self, screen):
        result = self.result(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, VALUE)

    def assert_ineligible(self, screen):
        result = self.result(screen)
        self.assertFalse(result.eligible)
        self.assertEqual(result.value, 0)

    def four_person_household(self, head_streams):
        screen = self.build(4)
        head = self.add_person(screen, age=38)
        for income_type, amount, frequency in head_streams:
            add_income(head, amount, income_type, frequency)
        spouse = self.add_person(screen, "spouse", age=36)
        self.add_person(screen, "child", age=10)
        self.add_person(screen, "child", age=7)
        return screen, head, spouse

    def test_scenario_1_four_person_household_under_the_income_limit(self):
        screen, _, _ = self.four_person_household([("wages", 60_000, "yearly")])
        self.assertEqual(self.countable_income(screen), 60_000)
        self.assert_eligible(screen)

    def test_scenario_2_four_person_household_exactly_at_the_income_limit(self):
        # Inclusive boundary, multi-member summation and monthly-to-yearly
        # conversion, all at once.
        screen, _, spouse = self.four_person_household([("wages", 4_000, "monthly")])
        self.add_monthly_income(spouse, "wages", 1_500)
        self.assertEqual(self.countable_income(screen), LIMIT[4])
        self.assert_eligible(screen)

    def test_scenario_3_four_person_household_one_dollar_over_the_income_limit(self):
        screen, _, _ = self.four_person_household([("wages", LIMIT[4] + 1, "yearly")])
        self.assert_ineligible(screen)

    def test_scenario_4_one_person_household_at_the_one_person_limit(self):
        screen, _ = self.single_earner(household_size=1, amount=LIMIT[1])
        self.assertEqual(self.countable_income(screen), LIMIT[1])
        self.assert_eligible(screen)

    def test_scenario_5_one_person_household_at_a_four_person_income(self):
        # The same income is eligible at four people (scenario 2), so the limit
        # is indexed to household_size rather than to a constant.
        screen, _ = self.single_earner(household_size=1, amount=LIMIT[4])
        self.assert_ineligible(screen)

    def test_scenario_6_household_above_the_income_limit_receiving_ssi(self):
        screen = self.build(2)
        head = self.add_person(screen, age=64)
        self.add_yearly_income(head, "wages", 90_000)
        self.add_person(screen, "spouse", age=60)
        self.receive_benefit(screen, "ks_ssi", "ssi")
        self.assertGreater(self.countable_income(screen), LIMIT[2])
        self.assert_eligible(screen)

    def test_scenario_7_household_above_the_income_limit_reporting_ssi_only_as_income(self):
        # The stream is checked on every member, not only the head.
        screen = self.build(2)
        head = self.add_person(screen, age=68)
        self.add_yearly_income(head, "wages", 39_000)
        spouse = self.add_person(screen, "spouse", age=66)
        self.add_yearly_income(spouse, "sSI", 11_000)
        self.assertEqual(self.countable_income(screen), 50_000)
        self.assertGreater(self.countable_income(screen), LIMIT[2])
        self.assert_eligible(screen)

    def test_scenario_8_household_above_the_income_limit_receiving_tanf(self):
        screen = self.build(3)
        head = self.add_person(screen, age=34)
        self.add_yearly_income(head, "wages", 70_000)
        self.add_person(screen, "child", age=12)
        self.add_person(screen, "child", age=5)
        self.receive_benefit(screen, "ks_tanf", "tanf")
        self.assertGreater(self.countable_income(screen), LIMIT[3])
        self.assert_eligible(screen)

    def test_scenario_9_household_above_the_income_limit_receiving_only_snap(self):
        screen = self.build(2, zipcode="67202", county="Sedgwick County")
        head = self.add_person(screen, age=56)
        self.add_yearly_income(head, "wages", 55_000)
        self.add_person(screen, "spouse", age=54)
        self.receive_benefit(screen, "ks_snap", "snap")
        self.assertGreater(self.countable_income(screen), LIMIT[2])
        self.assert_ineligible(screen)

    def test_scenario_10_household_with_no_income(self):
        # Absent income is $0, not missing data.
        screen = self.build(1)
        self.add_person(screen, age=58)
        self.assertEqual(self.countable_income(screen), 0)
        self.assert_eligible(screen)

    def test_scenario_11_child_support_received_and_gifts_are_excluded(self):
        screen = self.build(2)
        head = self.add_person(screen, age=41)
        self.add_yearly_income(head, "wages", LIMIT[2])
        spouse = self.add_person(screen, "spouse", age=39)
        self.add_yearly_income(spouse, "childSupport", 6_000)
        self.add_yearly_income(spouse, "gifts", 2_000)
        # Summing ["all"] gives $51,280 and fails.
        self.assertEqual(self.countable_income(screen), LIMIT[2])
        self.assert_eligible(screen)

    def test_scenario_12_working_sixteen_year_olds_wages_and_unemployment_are_excluded(self):
        screen = self.build(3)
        head = self.add_person(screen, age=44)
        self.add_yearly_income(head, "wages", LIMIT[3])
        self.add_person(screen, "spouse", age=42)
        child = self.add_person(screen, "child", age=16)
        self.add_yearly_income(child, "wages", 8_000)
        self.add_yearly_income(child, "unemployment", 2_000)
        # Counting the minor's $10,000 gives $64,640 and fails.
        self.assertEqual(self.countable_income(screen), LIMIT[3])
        self.assert_eligible(screen)

    def test_scenario_13_alimony_is_counted_and_flips_the_household_over(self):
        screen = self.build(2, zipcode="67202", county="Sedgwick County")
        head = self.add_person(screen, age=47)
        self.add_yearly_income(head, "wages", 30_000)
        spouse = self.add_person(screen, "spouse", age=45)
        self.add_yearly_income(spouse, "alimony", 13_281)
        # Excluding alimony leaves $30,000 and wrongly returns eligible.
        self.assertEqual(self.countable_income(screen), LIMIT[2] + 1)
        self.assert_ineligible(screen)

    def test_scenario_14_tanf_reported_as_a_cash_assistance_income_stream(self):
        screen = self.build(3)
        head = self.add_person(screen, age=36)
        self.add_yearly_income(head, "wages", 70_000)
        self.add_yearly_income(head, "cashAssistance", 4_800)
        self.add_person(screen, "child", age=13)
        self.add_person(screen, "child", age=8)
        self.assertGreater(self.countable_income(screen), LIMIT[3])
        self.assert_eligible(screen)

    def test_scenario_15_child_support_paid_is_not_deducted(self):
        screen = self.build(2, zipcode="67202", county="Sedgwick County")
        head = self.add_person(screen, age=43)
        self.add_yearly_income(head, "wages", LIMIT[2] + 1)
        self.add_person(screen, "spouse", age=41)
        self.add_expense(screen, "childSupport", 9_000)
        # Deducting the $9,000 expense gives $34,281 and wrongly returns eligible.
        self.assertEqual(self.countable_income(screen), LIMIT[2] + 1)
        self.assert_ineligible(screen)

    def test_scenario_16_eight_person_household_at_the_eight_person_limit(self):
        screen = self.build(8)
        head = self.add_person(screen, age=45)
        self.add_yearly_income(head, "wages", LIMIT[8])
        self.add_person(screen, "spouse", age=43)
        for age in (17, 15, 13, 11, 9, 7):
            self.add_person(screen, "child", age=age)
        self.assertEqual(self.countable_income(screen), LIMIT[8])
        self.assert_eligible(screen)


class TestKsWapBindingImplementationRequirements(KsWapTestCase):
    """The two regressions specs/ks.md commits to as build requirements.

    Requirement 1 is fully delivered: flipping `ks_lieap`'s has-benefits flag
    made the input enterable, so its regression is reachable end to end.

    Requirement 2 is delivered on the calculator side only. The screener caps
    household size at 8 for every white label, so sizes 9 and up cannot be
    entered and the two tests below them assert arithmetic no Kansas household
    can currently reach. They stay because the arithmetic is this calculator's
    to get right and is cheap to pin — not because the sizes are supported."""

    def test_lieap_route_admits_an_over_income_kansas_household(self):
        """Requirement 1. `ks_lieap.show_in_has_benefits_step` is flipped to
        true in this program's config import, which is what lets a Kansas
        screen carry the CurrentBenefit row this reads."""
        screen, _ = self.single_earner(household_size=1, amount=45_000)
        self.receive_benefit(screen, "ks_lieap", "liheap")
        self.assertGreater(self.countable_income(screen), LIMIT[1])
        self.assert_eligible_at_full_value(screen)

    def test_ten_person_household_at_the_ten_person_limit(self):
        """Requirement 2, the calculator half. The screener caps household size
        at 8 today, so this is unreachable through the UI until that cap is
        raised for Kansas — but the threshold arithmetic is this calculator's
        and is correct now."""
        screen = self.build(10)
        head = self.add_person(screen, age=45)
        self.add_yearly_income(head, "wages", LIMIT[10])
        self.add_person(screen, "spouse", age=44)
        for age in (19, 17, 15, 13, 11, 9, 7, 5):
            self.add_person(screen, "child", age=age)
        self.assertEqual(self.calculator(screen)._income_limit(), LIMIT[10])
        self.assert_eligible_at_full_value(screen)

    def test_sixteen_person_household_at_the_sixteen_person_limit(self):
        """The top of KHRC's printed table, which is the top of the range
        requirement 2 asks Kansas to accept."""
        screen = self.build(16)
        head = self.add_person(screen, age=50)
        self.add_yearly_income(head, "wages", LIMIT[16])
        self.add_person(screen, "spouse", age=48)
        for index in range(14):
            self.add_person(screen, "child", age=20 + index)
        self.assertEqual(self.calculator(screen)._income_limit(), LIMIT[16])
        self.assert_eligible_at_full_value(screen)

    def assert_eligible_at_full_value(self, screen):
        result = self.result(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, VALUE)

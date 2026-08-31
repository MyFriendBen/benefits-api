"""
Unit tests for the MoLiheap calculator.

Coverage maps to ``specs/mo.md`` — its five Covered Eligibility Criteria, its four
deductions and two income exclusions, its Benefit Value section, and one test per
entry in its 24-scenario Test Scenarios list.

These are built on real ``Screen`` / ``HouseholdMember`` / ``IncomeStream`` /
``Expense`` / ``Insurance`` rows rather than mocks. Nearly every rule here is a
question about income-type filtering (``calc_gross_income`` with ``exclude``, the
``all`` aggregation, monthly-vs-yearly conversion) or about an accessor
(``calc_age``, ``is_head``, ``is_spouse``, ``has_disability``,
``has_insurance``), so a mock standing in for those would be asserting the mock's
own semantics rather than the calculator's.

Ages are fixed integers derived against the spec's reference year, 2026 — a
``birth_year_month`` would make every age a function of ``timezone.now()`` and
break the suite on a calendar boundary. Scenario 6's claim is specifically about
``age_from_date`` granting 65 during the birth month, so that one test does set
``birth_year_month`` and pins the reference date to the spec's 2026-08-20.

Not tested here, because the calculator does not implement them (see the class
docstring):
- Criterion 3 (citizenship) — the program's ``legal_status_required`` config.
- Criterion 4 (Missouri residency) — enforced at the screener's ZIP step, which
  rejects a non-Missouri ZIP before any calculator runs.
- The $3,000 resource limit, primary heating fuel, CARS recoupment, and the
  utilities-included renter payment — all unscreenable, all recorded as data gaps.

Every eligible household is worth a flat $153.
"""

from datetime import date
from unittest.mock import patch

from django.test import TestCase

from programs.framework.base import Eligibility, ProgramCalculator
from programs.framework.registry import build
from programs.models import Program
from programs.programs.cross_white_label.liheap.mo import MoLiheap
from programs.programs.testing_fixtures.pe_integration import (
    add_income,
    add_member,
    make_program,
    make_screen,
)
from screener.models import Expense, Insurance, Screen

YEAR = "2026"
VALUE = 153


class MoLiheapTestCase(TestCase):
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
        # program row's unique (white_label, name_abbreviated).
        existing = Program.objects.filter(white_label=screen.white_label, name_abbreviated="mo_liheap").first()
        self.program = existing or make_program("mo", "mo_liheap", YEAR)
        self.member_id = self.next_screen_id * 100
        MoLiheapTestCase.next_screen_id += 1
        return screen

    def add_person(self, screen, relationship, birth_year, **kwargs):
        """A member stated by the birth year the scenario gives, as a fixed age
        against 2026 — see the module docstring on why the age is not derived
        from a birth date."""
        self.member_id += 1
        return add_member(screen, self.member_id, relationship, int(YEAR) - birth_year, **kwargs)

    def add_expense(self, screen, expense_type, monthly_amount):
        return Expense.objects.create(
            screen=screen,
            type=expense_type,
            amount=monthly_amount,
            frequency="monthly",
        )

    def calculator(self, screen):
        return MoLiheap(screen, self.program, {}, screen.missing_fields())

    def household_eligible(self, screen):
        e = Eligibility()
        self.calculator(screen).household_eligible(e)
        return e


class TestMoLiheapClassAttributes(MoLiheapTestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(MoLiheap, ProgramCalculator))

    def test_registered_under_mo_liheap(self):
        self.assertIs(build("programs.programs", ProgramCalculator).get("mo_liheap"), MoLiheap)

    def test_amount_is_153_lump_sum(self):
        self.assertEqual(MoLiheap.amount, VALUE)

    def test_income_limit_table_matches_published_60_percent_smi(self):
        self.assertEqual(
            MoLiheap.income_limits,
            {
                1: 2_840,
                2: 3_714,
                3: 4_588,
                4: 5_461,
                5: 6_335,
                6: 7_209,
                7: 7_373,
                8: 7_537,
                9: 7_701,
                10: 7_864,
            },
        )

    def test_income_limit_increment_is_164(self):
        # The MyDSS page's own note says $163, but its table and the FFY2026
        # application both increment by $164 — see specs/mo.md Criterion 1.
        self.assertEqual(MoLiheap.income_limit_increment, 164)

    def test_earned_income_deduction_is_20_percent(self):
        self.assertEqual(MoLiheap.earned_income_deduction, 0.20)

    def test_earned_income_types_include_boarder(self):
        self.assertEqual(set(MoLiheap.earned_income_types), {"wages", "selfEmployment", "boarder"})

    def test_excluded_income_types_are_interest_and_dividend(self):
        self.assertEqual(set(MoLiheap.excluded_income_types), {"investment", "deferredComp"})

    def test_medical_deduction_is_100_at_65(self):
        self.assertEqual(MoLiheap.medical_deduction, 100)
        self.assertEqual(MoLiheap.medical_deduction_min_age, 65)

    def test_medicare_premium_is_cms_2026_part_b_standard(self):
        self.assertEqual(MoLiheap.medicare_premium, 202.90)

    def test_min_applicant_age_is_15(self):
        self.assertEqual(MoLiheap.min_applicant_age, 15)

    def test_energy_expense_types(self):
        self.assertEqual(
            set(MoLiheap.expenses),
            {"rent", "mortgage", "heating", "cooling", "otherUtilities"},
        )

    def test_income_fields_in_dependencies(self):
        self.assertIn("income_amount", MoLiheap.dependencies)
        self.assertIn("income_frequency", MoLiheap.dependencies)
        self.assertIn("household_size", MoLiheap.dependencies)


class TestMoLiheapIncomeLimit(MoLiheapTestCase):
    """Criterion 1's limit table, including the rows and the increment the live
    screener's ``.lte(8)`` household-size cap makes unreachable."""

    def limit_for(self, household_size):
        screen = self.build(household_size)
        return self.calculator(screen)._income_limit()

    def test_every_published_row(self):
        for household_size, expected in MoLiheap.income_limits.items():
            with self.subTest(household_size=household_size):
                self.assertEqual(self.limit_for(household_size), expected)

    def test_size_above_table_adds_the_increment(self):
        self.assertEqual(self.limit_for(11), 7_864 + 164)
        self.assertEqual(self.limit_for(13), 7_864 + 3 * 164)

    def test_size_7_is_its_own_row_not_a_clamp_at_size_6(self):
        self.assertNotEqual(self.limit_for(7), self.limit_for(6))

    def test_null_household_size_falls_back_to_the_size_1_row(self):
        # Unreachable in production: household_size is a declared dependency, so
        # can_calc() drops the program first. Pinned so the guard stays honest.
        screen = self.build(1)
        screen.household_size = None
        self.assertEqual(self.calculator(screen)._income_limit(), 2_840)


class TestMoLiheapEnergyCostResponsibility(MoLiheapTestCase):
    """Criterion 2 — a housing or utility expense stands in for responsibility."""

    def screen_with_expense(self, expense_type=None):
        screen = self.build(1)
        self.add_person(screen, "headOfHousehold", 1986)
        if expense_type is not None:
            self.add_expense(screen, expense_type, 100)
        return screen

    def test_each_qualifying_expense_type_passes(self):
        for expense_type in MoLiheap.expenses:
            with self.subTest(expense_type=expense_type):
                self.assertTrue(self.household_eligible(self.screen_with_expense(expense_type)).eligible)

    def test_no_expense_at_all_fails(self):
        self.assertFalse(self.household_eligible(self.screen_with_expense()).eligible)

    def test_a_non_energy_expense_does_not_qualify(self):
        self.assertFalse(self.household_eligible(self.screen_with_expense("childCare")).eligible)


class TestMoLiheapApplicantAge(MoLiheapTestCase):
    """Criterion 5 — the household needs a member aged 15 or older."""

    def screen_with_oldest(self, birth_year):
        screen = self.build(1)
        self.add_person(screen, "headOfHousehold", birth_year)
        self.add_expense(screen, "heating", 100)
        return screen

    def test_exactly_15_passes(self):
        self.assertTrue(self.household_eligible(self.screen_with_oldest(2011)).eligible)

    def test_14_fails(self):
        self.assertFalse(self.household_eligible(self.screen_with_oldest(2012)).eligible)

    def test_a_qualifying_member_need_not_be_the_head(self):
        screen = self.build(2)
        self.add_person(screen, "headOfHousehold", 2012)  # 14
        self.add_person(screen, "sisterOrBrother", 2010)  # 16
        self.add_expense(screen, "heating", 100)
        self.assertTrue(self.household_eligible(screen).eligible)

    def test_unknown_age_does_not_satisfy_the_criterion(self):
        screen = self.build(1)
        self.add_person(screen, "headOfHousehold", 1986)
        screen.household_members.update(age=None)
        self.add_expense(screen, "heating", 100)
        self.assertFalse(self.household_eligible(screen).eligible)

    def test_fail_message_included(self):
        self.assertTrue(len(self.household_eligible(self.screen_with_oldest(2012)).fail_messages) > 0)


class TestMoLiheapMedicalDeduction(MoLiheapTestCase):
    """Deduction 2 — $100, applicant or spouse only, once per household."""

    def applies(self, screen):
        return self.calculator(screen)._medical_deduction_applies()

    def test_head_at_65_qualifies(self):
        screen = self.build(1)
        self.add_person(screen, "headOfHousehold", 1961)  # 65
        self.assertTrue(self.applies(screen))

    def test_head_at_64_does_not_qualify(self):
        screen = self.build(1)
        self.add_person(screen, "headOfHousehold", 1962)  # 64
        self.assertFalse(self.applies(screen))

    def test_spouse_at_65_qualifies(self):
        screen = self.build(2)
        self.add_person(screen, "headOfHousehold", 1986)
        self.add_person(screen, "spouse", 1960)  # 66
        self.assertTrue(self.applies(screen))

    def test_domestic_partner_counts_as_spouse(self):
        screen = self.build(2)
        self.add_person(screen, "headOfHousehold", 1986)
        self.add_person(screen, "domesticPartner", 1960)  # 66
        self.assertTrue(self.applies(screen))

    def test_a_qualifying_parent_does_not_earn_the_deduction(self):
        screen = self.build(2)
        self.add_person(screen, "headOfHousehold", 1986)
        self.add_person(screen, "parent", 1956)  # 70
        self.assertFalse(self.applies(screen))

    def test_each_disability_flag_qualifies_the_head(self):
        for flag in ("disabled", "visually_impaired", "long_term_disability"):
            with self.subTest(flag=flag):
                screen = self.build(1)
                self.add_person(screen, "headOfHousehold", 1976, **{flag: True})
                self.assertTrue(self.applies(screen))

    def test_a_disabled_non_spouse_does_not_earn_the_deduction(self):
        screen = self.build(2)
        self.add_person(screen, "headOfHousehold", 1986)
        self.add_person(screen, "child", 2010, disabled=True)
        self.assertFalse(self.applies(screen))

    def test_neither_elderly_nor_disabled(self):
        screen = self.build(1)
        self.add_person(screen, "headOfHousehold", 1986)
        self.assertFalse(self.applies(screen))

    def test_head_turning_65_during_the_birth_month_qualifies(self):
        # Scenario 6's claim: MFB treats a member as 65 throughout their birth
        # month, so a head born August 1961 has the deduction on 2026-08-20.
        # Missouri requires the birthday to have passed, which is the inclusive
        # direction — see specs/mo.md Deduction 2.
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 1986)
        member.age = None
        member.birth_year_month = date(1961, 8, 1)
        member.save()

        with patch.object(Screen, "get_reference_date", return_value=date(2026, 8, 20)):
            self.assertTrue(self.applies(screen))

    def test_head_whose_birth_month_has_not_arrived_does_not_qualify(self):
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 1986)
        member.age = None
        member.birth_year_month = date(1961, 9, 1)
        member.save()

        with patch.object(Screen, "get_reference_date", return_value=date(2026, 8, 20)):
            self.assertFalse(self.applies(screen))


class TestMoLiheapMedicareDeduction(MoLiheapTestCase):
    """Deduction 4 — $202.90 per Medicare-covered member."""

    def count(self, screen):
        return self.calculator(screen)._medicare_member_count()

    def test_counts_each_medicare_member(self):
        screen = self.build(3)
        for birth_year in (1959, 1958, 1986):
            member = self.add_person(screen, "headOfHousehold" if birth_year == 1959 else "spouse", birth_year)
            Insurance.objects.create(household_member=member, none=False, medicare=birth_year != 1986)
        self.assertEqual(self.count(screen), 2)

    def test_a_member_with_no_insurance_row_is_not_counted(self):
        screen = self.build(1)
        self.add_person(screen, "headOfHousehold", 1959)
        self.assertEqual(self.count(screen), 0)

    def test_other_insurance_types_are_not_counted(self):
        screen = self.build(1)
        member = self.add_person(screen, "headOfHousehold", 1959)
        Insurance.objects.create(household_member=member, none=False, medicaid=True, private=True)
        self.assertEqual(self.count(screen), 0)


class TestMoLiheapCountableIncome(MoLiheapTestCase):
    """Criterion 1's exclusions and deductions, read off the countable figure
    directly rather than through an eligibility boundary."""

    def countable(self, screen):
        return self.calculator(screen)._countable_income()

    def test_gross_unearned_income_is_counted_whole(self):
        screen = self.build(1)
        head = self.add_person(screen, "headOfHousehold", 1986)
        add_income(head, 1_000, "pension")
        self.assertEqual(self.countable(screen), 1_000)

    def test_each_earned_income_type_takes_the_20_percent_deduction(self):
        for income_type in MoLiheap.earned_income_types:
            with self.subTest(income_type=income_type):
                screen = self.build(1)
                head = self.add_person(screen, "headOfHousehold", 1986)
                add_income(head, 1_000, income_type)
                self.assertEqual(self.countable(screen), 800)

    def test_each_interest_and_dividend_type_is_excluded(self):
        for income_type in MoLiheap.excluded_income_types:
            with self.subTest(income_type=income_type):
                screen = self.build(1)
                head = self.add_person(screen, "headOfHousehold", 1986)
                add_income(head, 1_000, "pension")
                add_income(head, 300, income_type)
                self.assertEqual(self.countable(screen), 1_000)

    def test_gifts_cash_assistance_and_veteran_income_are_counted(self):
        # An earlier draft excluded all three; the manual documents each as
        # countable — see specs/mo.md data gap 7.
        for income_type in ("gifts", "cashAssistance", "cashAssistanceOther", "veteran"):
            with self.subTest(income_type=income_type):
                screen = self.build(1)
                head = self.add_person(screen, "headOfHousehold", 1986)
                add_income(head, 500, income_type)
                self.assertEqual(self.countable(screen), 500)

    def test_a_minors_earned_income_is_excluded_and_takes_no_deduction(self):
        screen = self.build(2)
        head = self.add_person(screen, "headOfHousehold", 1986)
        child = self.add_person(screen, "child", 2009)  # 17
        add_income(head, 1_000, "pension")
        add_income(child, 500, "wages")
        self.assertEqual(self.countable(screen), 1_000)

    def test_a_minors_ssa_income_is_counted(self):
        for income_type in ("sSI", "sSDisability"):
            with self.subTest(income_type=income_type):
                screen = self.build(2)
                head = self.add_person(screen, "headOfHousehold", 1986)
                child = self.add_person(screen, "child", 2009)  # 17
                add_income(head, 1_000, "pension")
                add_income(child, 100, income_type)
                self.assertEqual(self.countable(screen), 1_100)

    def test_a_member_of_unknown_age_is_treated_as_an_adult(self):
        screen = self.build(2)
        head = self.add_person(screen, "headOfHousehold", 1986)
        child = self.add_person(screen, "child", 2009)
        add_income(head, 1_000, "pension")
        add_income(child, 500, "wages")
        screen.household_members.filter(id=child.id).update(age=None)
        # $500 earned, counted with the 20% deduction rather than excluded.
        self.assertEqual(self.countable(screen), 1_400)

    def test_child_support_paid_is_deducted(self):
        screen = self.build(1)
        head = self.add_person(screen, "headOfHousehold", 1986)
        add_income(head, 1_000, "pension")
        self.add_expense(screen, "childSupport", 165)
        self.assertEqual(self.countable(screen), 835)

    def test_child_support_received_as_income_is_counted_not_deducted(self):
        screen = self.build(1)
        head = self.add_person(screen, "headOfHousehold", 1986)
        add_income(head, 1_000, "childSupport")
        self.assertEqual(self.countable(screen), 1_000)

    def test_the_medical_deduction_is_taken_once_for_two_qualifying_members(self):
        screen = self.build(2)
        head = self.add_person(screen, "headOfHousehold", 1961)  # 65
        self.add_person(screen, "spouse", 1959)  # 67
        add_income(head, 1_000, "pension")
        self.assertEqual(self.countable(screen), 900)

    def test_deductions_cannot_drive_the_figure_below_zero(self):
        screen = self.build(1)
        head = self.add_person(screen, "headOfHousehold", 1961)  # 65
        add_income(head, 50, "pension")
        self.assertEqual(self.countable(screen), 0)

    def test_yearly_income_is_converted_to_monthly(self):
        screen = self.build(1)
        head = self.add_person(screen, "headOfHousehold", 1986)
        add_income(head, 34_080, "pension", frequency="yearly")
        self.assertEqual(self.countable(screen), 2_840)

    def test_all_four_deductions_stack(self):
        screen = self.build(2)
        head = self.add_person(screen, "headOfHousehold", 1959)  # 67
        spouse = self.add_person(screen, "spouse", 1958)  # 68
        add_income(head, 1_000, "wages")
        add_income(head, 2_000, "pension")
        Insurance.objects.create(household_member=head, none=False, medicare=True)
        Insurance.objects.create(household_member=spouse, none=False, medicare=True)
        self.add_expense(screen, "childSupport", 50)
        # 3,000 gross - 200 earned - 100 medical - 50 child support - 405.80 Medicare
        self.assertEqual(self.countable(screen), 2_244.20)


class TestMoLiheapValue(MoLiheapTestCase):
    def test_household_value_is_153(self):
        screen = self.build(1)
        self.add_person(screen, "headOfHousehold", 1986)
        self.assertEqual(self.calculator(screen).household_value(), VALUE)

    def test_ineligible_household_is_worth_nothing(self):
        screen = self.build(1)
        head = self.add_person(screen, "headOfHousehold", 1986)
        add_income(head, 10_000, "pension")
        self.add_expense(screen, "heating", 100)
        eligibility = self.calculator(screen).calc()
        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.value, 0)

    def test_no_member_value_is_added(self):
        screen = self.build(3)
        self.add_person(screen, "headOfHousehold", 1986)
        self.add_person(screen, "spouse", 1988)
        self.add_person(screen, "child", 2015)
        self.add_expense(screen, "heating", 100)
        eligibility = self.calculator(screen).calc()
        self.assertTrue(eligibility.eligible)
        # Flat per household — three members must not multiply it.
        self.assertEqual(eligibility.value, VALUE)


class TestMoLiheapScenarios(MoLiheapTestCase):
    """One test per Test Scenario in specs/mo.md, run end to end through calc().

    Scenario ZIP/county pairs are recorded as the spec states them even though
    Criterion 4 is enforced at intake rather than here.
    """

    def assert_eligible(self, screen):
        eligibility = self.calculator(screen).calc()
        self.assertTrue(eligibility.eligible, eligibility.fail_messages)
        self.assertEqual(eligibility.value, VALUE)

    def assert_ineligible(self, screen):
        eligibility = self.calculator(screen).calc()
        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.value, 0)

    def test_scenario_1_single_adult_low_income_renter(self):
        screen = self.build(1, zipcode="63101", county="St. Louis City")
        head = self.add_person(screen, "headOfHousehold", 1986)
        add_income(head, 1_000, "wages")
        self.add_expense(screen, "rent", 600)
        self.add_expense(screen, "heating", 150)
        # 1,000 x 0.80 = 800 <= 2,840
        self.assert_eligible(screen)

    def test_scenario_2_household_of_1_exactly_at_the_limit(self):
        screen = self.build(1, zipcode="65201", county="Boone County")
        head = self.add_person(screen, "headOfHousehold", 1986)
        add_income(head, 2_840, "pension")
        self.add_expense(screen, "heating", 150)
        self.assert_eligible(screen)

    def test_scenario_3_household_of_1_one_dollar_over_the_limit(self):
        screen = self.build(1, zipcode="65201", county="Boone County")
        head = self.add_person(screen, "headOfHousehold", 1986)
        add_income(head, 2_841, "pension")
        self.add_expense(screen, "heating", 150)
        # Also pins the 20% deduction to earned income only: applying it here
        # would give 2,272.80 and wrongly flip this to eligible.
        self.assert_ineligible(screen)

    def test_scenario_4_earned_income_at_the_limit_after_the_deduction(self):
        screen = self.build(1, zipcode="64108", county="Jackson County")
        head = self.add_person(screen, "headOfHousehold", 1986)
        add_income(head, 3_550, "wages")
        self.add_expense(screen, "rent", 700)
        self.add_expense(screen, "heating", 50)
        # 3,550 x 0.80 = 2,840.00 = the size-1 limit
        self.assert_eligible(screen)

    def test_scenario_5_eligible_income_but_no_housing_or_utility_expense(self):
        screen = self.build(1, zipcode="63101", county="St. Louis City")
        head = self.add_person(screen, "headOfHousehold", 1986)
        add_income(head, 500, "wages")
        self.assert_ineligible(screen)

    def test_scenario_6_head_exactly_65_eligible_only_after_the_100_deduction(self):
        screen = self.build(2, zipcode="65201", county="Boone County")
        head = self.add_person(screen, "headOfHousehold", 1961)  # 65
        self.add_person(screen, "spouse", 1963)  # 63
        add_income(head, 3_814, "sSRetirement")
        self.add_expense(screen, "heating", 200)
        # 3,814 - 100 = 3,714 = the size-2 limit
        self.assert_eligible(screen)

    def test_scenario_7_two_medicare_members_eligible_only_after_both_deductions(self):
        screen = self.build(2, zipcode="64108", county="Jackson County")
        head = self.add_person(screen, "headOfHousehold", 1959)  # 67
        spouse = self.add_person(screen, "spouse", 1958)  # 68
        add_income(head, 4_219.80, "sSRetirement")
        Insurance.objects.create(household_member=head, none=False, medicare=True)
        Insurance.objects.create(household_member=spouse, none=False, medicare=True)
        self.add_expense(screen, "heating", 180)
        # 4,219.80 - 100 - 405.80 (2 x 202.90) = 3,714.00 = the size-2 limit
        self.assert_eligible(screen)

    def test_scenario_8_child_support_paid_eligible_only_after_the_deduction(self):
        screen = self.build(1, zipcode="63101", county="St. Louis City")
        head = self.add_person(screen, "headOfHousehold", 1986)
        add_income(head, 3_005, "pension")
        self.add_expense(screen, "rent", 650)
        self.add_expense(screen, "heating", 50)
        self.add_expense(screen, "childSupport", 165)
        # 3,005 - 165 = 2,840 = the size-1 limit
        self.assert_eligible(screen)

    def test_scenario_9_household_of_7_at_the_size_7_limit(self):
        screen = self.build(7, zipcode="65201", county="Boone County")
        head = self.add_person(screen, "headOfHousehold", 1986)
        for birth_year in (2012, 2014, 2016, 2018, 2020, 2022):
            self.add_person(screen, "child", birth_year)
        add_income(head, 7_373, "pension")
        self.add_expense(screen, "rent", 1_200)
        self.add_expense(screen, "heating", 50)
        self.assert_eligible(screen)

    def test_scenario_10_head_under_65_with_a_disability(self):
        screen = self.build(1, zipcode="63101", county="St. Louis City")
        head = self.add_person(screen, "headOfHousehold", 1976, long_term_disability=True)  # 50
        add_income(head, 2_940, "pension")
        self.add_expense(screen, "rent", 700)
        self.add_expense(screen, "heating", 50)
        # 2,940 - 100 = 2,840 = the size-1 limit
        self.assert_eligible(screen)

    def test_scenario_11_two_members_65_or_older_one_deduction_only(self):
        screen = self.build(2, zipcode="65201", county="Boone County")
        head = self.add_person(screen, "headOfHousehold", 1961)  # 65
        self.add_person(screen, "spouse", 1959)  # 67
        add_income(head, 3_914, "pension")
        self.add_expense(screen, "heating", 200)
        # 3,914 - 100 = 3,814 > 3,714; a second deduction would wrongly admit it
        self.assert_ineligible(screen)

    def test_scenario_12_qualifying_age_in_a_non_spouse_member(self):
        screen = self.build(2, zipcode="64108", county="Jackson County")
        head = self.add_person(screen, "headOfHousehold", 1986)
        self.add_person(screen, "parent", 1956)  # 70
        add_income(head, 3_800, "pension")
        self.add_expense(screen, "rent", 800)
        self.add_expense(screen, "heating", 50)
        self.assert_ineligible(screen)

    def test_scenario_13_income_reported_yearly_at_the_monthly_limit(self):
        screen = self.build(1, zipcode="65201", county="Boone County")
        head = self.add_person(screen, "headOfHousehold", 1986)
        add_income(head, 34_080, "pension", frequency="yearly")
        self.add_expense(screen, "heating", 150)
        # 34,080 / 12 = 2,840.00 = the size-1 limit
        self.assert_eligible(screen)

    def test_scenario_14_household_of_8_at_the_size_8_limit(self):
        screen = self.build(8, zipcode="65201", county="Boone County")
        head = self.add_person(screen, "headOfHousehold", 1986)
        for birth_year in (2008, 2010, 2012, 2014, 2016, 2018, 2022):
            self.add_person(screen, "child", birth_year)
        add_income(head, 7_537, "pension")
        self.add_expense(screen, "rent", 1_300)
        self.add_expense(screen, "heating", 50)
        self.assert_eligible(screen)

    def test_scenario_15_household_of_4_at_the_size_4_limit(self):
        screen = self.build(4, zipcode="63101", county="St. Louis City")
        head = self.add_person(screen, "headOfHousehold", 1986)
        self.add_person(screen, "spouse", 1988)
        self.add_person(screen, "child", 2015)
        self.add_person(screen, "child", 2018)
        add_income(head, 5_461, "pension")
        self.add_expense(screen, "rent", 1_100)
        self.add_expense(screen, "heating", 50)
        self.assert_eligible(screen)

    def test_scenario_16_household_with_a_working_17_year_old(self):
        screen = self.build(2, zipcode="64108", county="Jackson County")
        head = self.add_person(screen, "headOfHousehold", 1986)
        child = self.add_person(screen, "child", 2009)  # 17
        add_income(head, 3_714, "pension")
        add_income(child, 500, "wages")
        self.add_expense(screen, "rent", 900)
        self.add_expense(screen, "heating", 50)
        # The 17-year-old's earned income is excluded outright
        self.assert_eligible(screen)

    def test_scenario_17_household_with_investment_income(self):
        screen = self.build(1, zipcode="63101", county="St. Louis City")
        head = self.add_person(screen, "headOfHousehold", 1986)
        add_income(head, 2_840, "pension")
        add_income(head, 300, "investment")
        self.add_expense(screen, "rent", 700)
        self.add_expense(screen, "heating", 50)
        self.assert_eligible(screen)

    def test_scenario_18_head_aged_64_no_medical_deduction(self):
        screen = self.build(2, zipcode="65201", county="Boone County")
        head = self.add_person(screen, "headOfHousehold", 1962)  # 64
        self.add_person(screen, "spouse", 1964)  # 62
        add_income(head, 3_814, "sSRetirement")
        self.add_expense(screen, "heating", 200)
        # Using 60 (Missouri's early-application age) would wrongly admit this
        self.assert_ineligible(screen)

    def test_scenario_19_household_of_8_one_dollar_over_the_size_8_limit(self):
        screen = self.build(8, zipcode="65201", county="Boone County")
        head = self.add_person(screen, "headOfHousehold", 1986)
        for birth_year in (2008, 2010, 2012, 2014, 2016, 2018, 2022):
            self.add_person(screen, "child", birth_year)
        add_income(head, 7_538, "pension")
        self.add_expense(screen, "rent", 1_300)
        self.add_expense(screen, "heating", 50)
        self.assert_ineligible(screen)

    def test_scenario_20_household_with_a_working_18_year_old(self):
        screen = self.build(2, zipcode="64108", county="Jackson County")
        head = self.add_person(screen, "headOfHousehold", 1986)
        child = self.add_person(screen, "child", 2008)  # 18
        add_income(head, 3_714, "pension")
        add_income(child, 500, "wages")
        self.add_expense(screen, "rent", 900)
        self.add_expense(screen, "heating", 50)
        # 3,714 + 500 x 0.80 = 4,114 > 3,714
        self.assert_ineligible(screen)

    def test_scenario_21_qualifying_age_in_the_spouse_not_the_head(self):
        screen = self.build(2, zipcode="63101", county="St. Louis City")
        head = self.add_person(screen, "headOfHousehold", 1986)
        self.add_person(screen, "spouse", 1960)  # 66
        add_income(head, 3_814, "pension")
        self.add_expense(screen, "heating", 200)
        # 3,814 - 100 = 3,714 = the size-2 limit
        self.assert_eligible(screen)

    def test_scenario_22_earned_income_one_dollar_past_the_deduction_boundary(self):
        screen = self.build(1, zipcode="63101", county="St. Louis City")
        head = self.add_person(screen, "headOfHousehold", 1986)
        add_income(head, 3_551, "wages")
        self.add_expense(screen, "rent", 700)
        self.add_expense(screen, "heating", 50)
        # 3,551 x 0.80 = 2,840.80 > 2,840 — the only scenario that catches a
        # deduction rate larger than 20%
        self.assert_ineligible(screen)

    def test_scenario_23_minor_with_ssa_income(self):
        screen = self.build(2, zipcode="64108", county="Jackson County")
        head = self.add_person(screen, "headOfHousehold", 1986)
        child = self.add_person(screen, "child", 2009)  # 17
        add_income(head, 3_714, "sSRetirement")
        add_income(child, 100, "sSI")
        self.add_expense(screen, "rent", 900)
        self.add_expense(screen, "heating", 50)
        # 3,714 + 100 = 3,814 > 3,714 — the under-18 exclusion is earned only
        self.assert_ineligible(screen)

    def test_scenario_24_no_household_member_aged_15_or_older(self):
        screen = self.build(2, zipcode="63101", county="St. Louis City")
        head = self.add_person(screen, "headOfHousehold", 2012)  # 14
        self.add_person(screen, "sisterOrBrother", 2016)  # 10
        add_income(head, 400, "wages")
        self.add_expense(screen, "rent", 500)
        self.add_expense(screen, "heating", 50)
        # Income and expenses both qualify; this fails only on applicant age
        self.assert_ineligible(screen)

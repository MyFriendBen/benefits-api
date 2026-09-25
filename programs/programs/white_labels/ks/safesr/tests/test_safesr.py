"""
Unit tests for KsSafesr — one test per spec.md Test Scenario (1-20), plus the
branches the scenarios cannot reach.

Kansas Property Tax Relief for Low Income Seniors (SAFESR, Form K-40PT):
- Claimant 65 for the entire claim year (birth_year <= claim_year - 66)
- SAFESR household income <= $25,380 (2025), with all four Social Security
  streams at 100% and sSDisability / childSupport / gifts / veteran excluded
- Owns and occupies (a rent expense -> ineligible; else homeowner)
- Refund = 75% of the propertyTax expense, falling back to $2,342/year
  whenever the summed expense is zero, rounded to whole dollars

Every scenario uses claim year 2025.
"""

from datetime import date
from unittest.mock import patch

from django.test import TestCase

from programs.framework.base import ProgramCalculator
from programs.models import FederalPoveryLimit
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from programs.programs.white_labels.ks.safesr.calculator import KsSafesr
from programs.util import DependencyError


def member(birth_year=1955, relationship="headOfHousehold", **income):
    """A member as a scenario states them: a birth year, and annual income by type."""
    return birth_year, relationship, income


class SafesrTestCase(CustomCalculatorTestCase):
    calculator_class = KsSafesr
    white_label_code = "ks"
    state_code = "KS"
    fpl_year = "2025"

    def household(self, *members, rent=0, mortgage=0, property_tax=None):
        """
        The first member is the head, and carries the housing expenses.

        property_tax=None means no propertyTax row at all; 0 means a row entered at
        $0. The two are distinguished because has_expense matches on type and
        ignores the amount, while the value fork reads the summed amount.
        """
        members = members or (member(),)
        screen = self.make_screen(household_size=len(members))

        for birth_year, relationship, income in members:
            birth_year_month = None if birth_year is None else date(birth_year, 1, 1)
            household_member = self.add_member(screen, relationship, age=None, birth_year_month=birth_year_month)
            for income_type, amount in income.items():
                self.add_income(household_member, amount, income_type, frequency="yearly")

        head = screen.household_members.get(relationship="headOfHousehold")
        for expense_type, amount in (("rent", rent), ("mortgage", mortgage)):
            if amount:
                self.add_expense(head, amount, expense_type, frequency="yearly")
        if property_tax is not None:
            self.add_expense(head, property_tax, "propertyTax", frequency="yearly")

        return screen

    def set_claim_year(self, year):
        """Point program.year at `year`'s FederalPoveryLimit row, or at nothing for None."""
        if year is None:
            self.program.year = None
        else:
            self.program.year, _ = FederalPoveryLimit.objects.get_or_create(
                year=str(year), defaults={"period": str(year)}
            )


class TestClassAttributes(TestCase):
    def test_is_subclass(self):
        self.assertTrue(issubclass(KsSafesr, ProgramCalculator))

    def test_program_code(self):
        self.assertEqual(KsSafesr.program_code, "ks_safesr")

    def test_constants(self):
        self.assertEqual(KsSafesr.income_limit_by_year[2025], 25_380)
        self.assertEqual(KsSafesr.senior_age, 65)
        self.assertEqual(KsSafesr.adult_age, 18)
        self.assertEqual(KsSafesr.refund_percent, 0.75)
        self.assertEqual(KsSafesr.fallback_property_tax, 2_342)

    def test_excluded_types(self):
        # The veteran bucket is a committed proxy, not a Kansas exclusion, but it
        # is committed all the same — scenario 20 turns on it.
        self.assertEqual(KsSafesr.excluded_types, ("sSDisability", "childSupport", "gifts", "veteran"))

    def test_dependencies(self):
        # expense_type/expense_amount are the tokens Expense.missing_fields actually
        # emits; a bare "expenses" is never emitted and so never gates anything.
        # relationship and household_size are deliberately absent: the minor guard
        # is keyed to birth year and no rule reads household size.
        self.assertEqual(
            KsSafesr.dependencies,
            ("age", "income_type", "income_amount", "income_frequency", "expense_type", "expense_amount"),
        )

    def test_declared_dependencies_are_tokens_the_screener_emits(self):
        # Guards the whole tuple against the inert-token trap, not just the two
        # expense entries.
        emitted = {
            "zipcode",
            "county",
            "household_size",
            "household_assets",
            "energy_calculator",
            "relationship",
            "age",
            "student",
            "pregnant",
            "visually_impaired",
            "disabled",
            "long_term_disability",
            "insurance",
            "income_type",
            "income_amount",
            "income_frequency",
            "expense_type",
            "expense_amount",
        }
        self.assertEqual(set(KsSafesr.dependencies) - emitted, set())

    def test_2025_ceiling_is_120_percent_of_the_two_person_fpl(self):
        # An annual cross-check on the published figure, not the source of it —
        # KDOR's published ceiling has not always equalled the formula.
        from programs.models import _FPL_DEFAULTS

        self.assertEqual(round(1.2 * _FPL_DEFAULTS["2025"][2]), KsSafesr.income_limit_by_year[2025])


class TestSpecScenarios(SafesrTestCase):
    def test_s1_clearly_eligible_senior_homeowner(self):
        e = self.calculate(self.household(member(1955, sSRetirement=14_400), property_tax=1_800))
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 1_350)  # 75% x 1800

    def test_s2_income_exactly_at_the_ceiling(self):
        e = self.calculate(self.household(member(1959, sSRetirement=25_380), property_tax=1_000))
        self.assertTrue(e.eligible)  # pins the <= comparator from below
        self.assertEqual(e.value, 750)

    def test_s3_income_just_below_the_ceiling(self):
        e = self.calculate(self.household(member(1958, sSRetirement=25_280), property_tax=1_200))
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 900)

    def test_s4_income_just_above_the_ceiling(self):
        # Kills the K-40H copy-paste bug: at 50% Social Security this is $12,740
        # and wrongly passes.
        e = self.calculate(self.household(member(1955, sSRetirement=25_480), property_tax=1_800))
        self.assertFalse(e.eligible)

    def test_s5_earliest_qualifying_birth_year(self):
        e = self.calculate(self.household(member(1959, sSRetirement=10_800), property_tax=800))
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 600)

    def test_s6_turned_65_during_the_year(self):
        # The off-by-one the age rule exists to catch: a current-age snapshot
        # passes this household, birth_year <= 1959 rejects it.
        e = self.calculate(self.household(member(1960, sSRetirement=10_800), property_tax=1_200))
        self.assertFalse(e.eligible)

    def test_s7_age_well_above_the_minimum(self):
        e = self.calculate(self.household(member(1946, sSRetirement=10_800), property_tax=900))
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 675)

    def test_s8_renter_otherwise_fully_qualified(self):
        e = self.calculate(self.household(member(1954, sSRetirement=14_400), rent=800 * 12))
        self.assertFalse(e.eligible)

    def test_s9_senior_homeowner_receiving_snap(self):
        # SNAP is line 13(a) excluded income and is not an IncomeStream at all,
        # so it neither disqualifies nor counts toward the ceiling.
        e = self.calculate(self.household(member(1956, sSRetirement=10_800), property_tax=700))
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 525)

    def test_s10_mixed_household_senior_head_younger_spouse_and_adult_child(self):
        # The age test applies to the claimant only; the income test to everyone.
        screen = self.household(
            member(1954, sSRetirement=8_400),
            member(1968, "spouse", wages=6_000),
            member(1996, "child", wages=4_800),
            property_tax=1_600,
        )
        e = self.calculate(screen)
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 1_200)

    def test_s11_two_seniors_in_one_household(self):
        # One claimant per household per year (K.S.A. 79-4507): the refund is
        # household-level, so two qualifying seniors do not pay twice.
        screen = self.household(
            member(1958, sSRetirement=8_400),
            member(1958, "spouse", sSRetirement=6_600),
            property_tax=1_000,
        )
        e = self.calculate(screen)
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 750)
        self.assertEqual(e.household_value, 750)
        self.assertEqual([m.value for m in e.eligible_members], [0, 0])

    def test_s12_adult_childs_income_pushes_the_household_over(self):
        # The only scenario turning on a non-claimant adult's income being
        # counted, and the only one that catches a relationship-keyed skip.
        screen = self.household(
            member(1953, sSRetirement=8_400),
            member(1990, "child", wages=18_000),
            property_tax=1_200,
        )
        self.assertFalse(self.calculate(screen).eligible)  # 26,400 > 25,380

    def test_s13_senior_with_zero_income(self):
        e = self.calculate(self.household(member(1951), property_tax=600))
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 450)

    def test_s14_no_housing_expense_entered(self):
        # A blank housing section is a homeowner, and the value falls back.
        e = self.calculate(self.household(member(1955, sSRetirement=14_400)))
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 1_756)  # 75% x 2342 = 1756.50, rounded

    def test_s15_mortgage_entered_no_property_tax(self):
        e = self.calculate(self.household(member(1953, sSRetirement=13_200), mortgage=650 * 12))
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 1_756)

    def test_s16_property_tax_row_entered_at_zero(self):
        # Gating the value on has_expense(["propertyTax"]) computes 75% x $0 and
        # hands an eligible household a $0 refund; scenarios 14 and 15 both pass
        # that calculator, this one does not.
        e = self.calculate(self.household(member(1955, sSRetirement=14_400), property_tax=0))
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 1_756)

    def test_s17_ssdi_and_gifts_are_excluded(self):
        # Gross is $37,200; SAFESR household income is $23,400. Each exclusion
        # crosses the ceiling on its own.
        screen = self.household(
            member(1952, sSRetirement=23_400, gifts=3_000),
            member(1985, "child", sSDisability=10_800),
            property_tax=1_200,
        )
        e = self.calculate(screen)
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 900)

    def test_s18_grandchild_who_turns_18_mid_year_plus_child_support(self):
        # Three ways of building this wrong cross the ceiling: keying the skip to
        # relationship (grandChild is not in K-40H's tuple), writing the cutoff as
        # birth_year > claim_year - 18, and omitting childSupport.
        screen = self.household(
            member(1953, sSRetirement=22_800, childSupport=5_000),
            member(2007, "grandChild", wages=4_800),
            property_tax=1_200,
        )
        e = self.calculate(screen)
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 900)

    def test_s19_grandchild_who_was_18_all_year(self):
        # The other half of the adulthood boundary: a cutoff one year too broad
        # returns eligible here.
        screen = self.household(
            member(1952, sSRetirement=22_800),
            member(2006, "grandChild", wages=4_800),
            property_tax=1_200,
        )
        self.assertFalse(self.calculate(screen).eligible)  # 27,600 > 25,380

    def test_s20_veterans_benefits_excluded(self):
        # Gross is $27,600; SAFESR household income is $19,200 once the bucket
        # drops. Counting it — which K-40H does — returns not eligible.
        e = self.calculate(self.household(member(1950, sSRetirement=19_200, veteran=8_400), property_tax=1_400))
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 1_050)


class TestIncomeDefinition(SafesrTestCase):
    """The 100%-Social-Security rule, one stream at a time."""

    def test_all_four_social_security_streams_count_at_full_value(self):
        # $6,400 x 4 = $25,600, over the ceiling. At K-40H's 50% on the first
        # three this is $16,000 and passes.
        screen = self.household(
            member(1950, sSRetirement=6_400, sSSurvivor=6_400, sSI=6_400, sSDependent=6_400),
            property_tax=1_200,
        )
        self.assertFalse(self.calculate(screen).eligible)

    def test_household_income_sums_every_countable_stream(self):
        screen = self.household(
            member(
                1950,
                wages=1_000,
                selfEmployment=1_000,
                pension=1_000,
                deferredComp=1_000,
                investment=1_000,
                rental=1_000,
                boarder=1_000,
                unemployment=1_000,
                workersComp=1_000,
                cashAssistance=1_000,
                cashAssistanceOther=1_000,
                alimony=1_000,
            ),
            property_tax=1_200,
        )
        self.assertEqual(self.make_calculator(screen)._household_income(), 12_000)

    def test_excluded_streams_alone_leave_zero_income(self):
        screen = self.household(
            member(1950, sSDisability=30_000, childSupport=30_000, gifts=30_000, veteran=30_000),
            property_tax=1_200,
        )
        self.assertEqual(self.make_calculator(screen)._household_income(), 0)

    def test_member_with_no_birth_year_is_counted_as_an_adult(self):
        # birth_year is None when birth_year_month is unset. For the income gate
        # the conservative reading is to count them.
        screen = self.household(
            member(1950, sSRetirement=22_800),
            member(None, "relatedOther", wages=4_800),
            property_tax=1_200,
        )
        self.assertEqual(self.make_calculator(screen)._household_income(), 27_600)


class TestAgeGate(SafesrTestCase):
    def test_member_with_no_birth_year_fails_the_age_gate(self):
        e = self.calculate(self.household(member(None, sSRetirement=10_800), property_tax=1_200))
        self.assertFalse(e.eligible)

    def test_age_gate_and_ceiling_both_follow_the_configured_year(self):
        self.set_claim_year(2025)
        self.assertEqual(self.make_calculator(self.household())._claim_year(), 2025)

    def test_claim_year_falls_back_to_the_newest_ceiling_when_program_year_is_none(self):
        # import_program_config only warns when no FederalPoveryLimit row matches,
        # so a mis-seeded config leaves program.year as None.
        self.set_claim_year(None)
        self.assertEqual(self.make_calculator(self.household())._claim_year(), max(KsSafesr.income_limit_by_year))

    def test_claim_year_falls_back_when_no_ceiling_is_published_for_the_configured_year(self):
        # The fallback is shared so the age gate and the ceiling can never
        # describe different years.
        self.set_claim_year(2099)
        self.assertEqual(self.make_calculator(self.household())._claim_year(), max(KsSafesr.income_limit_by_year))


class TestTaxYearIsTheConfiguredYear(SafesrTestCase):
    """
    SAFESR is a tax program: the rules follow the tax year, which lags the
    current year by one. Nothing may read the current year.
    """

    def test_age_gate_and_ceiling_both_shift_with_the_configured_tax_year(self):
        # Born 1960 is not 65 for all of 2025 but is for all of 2026, and $25,800
        # clears a 2026 ceiling of $26,000 while failing the 2025 one. Both flip
        # together, which a hardcoded year in either rule would not.
        screen = self.household(member(1960, sSRetirement=25_800), property_tax=1_000)
        self.assertFalse(self.calculate(screen).eligible)

        with patch.dict(KsSafesr.income_limit_by_year, {2026: 26_000}, clear=False):
            self.set_claim_year(2026)
            self.assertEqual(self.make_calculator(screen)._claim_year(), 2026)
            e = self.calculate(screen)
            self.assertTrue(e.eligible)
            self.assertEqual(e.value, 750)

    def test_minor_guard_shifts_with_the_configured_tax_year(self):
        # Born 2007 was not 18 for all of 2025, but was for all of 2026.
        screen = self.household(
            member(1950, sSRetirement=22_800),
            member(2007, "grandChild", wages=4_800),
        )
        self.assertEqual(self.make_calculator(screen)._household_income(), 22_800)

        with patch.dict(KsSafesr.income_limit_by_year, {2026: 26_000}, clear=False):
            self.set_claim_year(2026)
            self.assertEqual(self.make_calculator(screen)._household_income(), 27_600)


class TestDependencyGating(SafesrTestCase):
    def test_a_null_expense_amount_drops_the_program_rather_than_crashing(self):
        # calc_expenses raises TypeError on a null amount, and the eligibility loop
        # catches only DependencyError, so without this token the whole household's
        # response 500s.
        screen = self.household(property_tax=1_800)
        self.assertFalse(self.make_calculator(screen, missing=("expense_amount",)).can_calc())
        with self.assertRaises(DependencyError):
            self.calculate(screen, missing=("expense_amount",))

    def test_a_null_expense_type_drops_the_program(self):
        # An untyped row could be the rent row, so the ownership proxy cannot be
        # trusted; drop the program rather than guess the household owns.
        screen = self.household(property_tax=1_800)
        self.assertFalse(self.make_calculator(screen, missing=("expense_type",)).can_calc())

    def test_an_unrelated_missing_field_does_not_drop_the_program(self):
        screen = self.household(property_tax=1_800)
        calc = self.make_calculator(screen, missing=("household_assets", "insurance", "energy_calculator"))
        self.assertTrue(calc.can_calc())


class TestValue(SafesrTestCase):
    def test_refund_is_never_zero_for_an_eligible_household(self):
        # calc_expenses can only return whole dollars, so the smallest non-zero
        # bill rounds up rather than to $0 — a $0 value would be filtered out of
        # the results page entirely.
        e = self.calculate(self.household(member(1950, sSRetirement=10_800), property_tax=1))
        self.assertEqual(e.value, 1)

    def test_value_rounds_to_whole_dollars(self):
        e = self.calculate(self.household(member(1950, sSRetirement=10_800), property_tax=1_001))
        self.assertEqual(e.value, 751)  # 750.75

    def test_ineligible_household_has_no_value(self):
        e = self.calculate(self.household(member(1955, sSRetirement=30_000), property_tax=1_800))
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)

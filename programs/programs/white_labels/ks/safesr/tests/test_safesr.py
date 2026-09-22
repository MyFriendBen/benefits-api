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

from django.test import TestCase
from unittest.mock import Mock

from programs.framework.base import ProgramCalculator
from programs.programs.white_labels.ks.safesr.calculator import KsSafesr


def make_member(birth_year=1955, income=None):
    """income is a dict of {income type: annual amount}."""
    income = income or {}
    member = Mock()
    member.birth_year = birth_year

    def calc_income(frequency, types, exclude=[]):
        if types == ["all"]:
            return sum(v for t, v in income.items() if t not in exclude)
        return sum(income.get(t, 0) for t in types)

    member.calc_gross_income = Mock(side_effect=calc_income)
    return member


def make_calculator(members=None, rent=0, mortgage=0, property_tax=None, claim_year=2025):
    """
    property_tax=None means no propertyTax row at all; 0 means a row entered at
    $0. The two are distinguished because has_expense matches on type and
    ignores the amount, while the value fork reads the summed amount.
    """
    if members is None:
        members = [make_member()]

    mock_program = Mock()
    if claim_year is None:
        mock_program.year = None
    else:
        mock_program.year.period = str(claim_year)

    expenses = {}
    if rent:
        expenses["rent"] = rent
    if mortgage:
        expenses["mortgage"] = mortgage
    if property_tax is not None:
        expenses["propertyTax"] = property_tax

    mock_screen = Mock()
    mock_screen.household_size = len(members)
    mock_screen.household_members.all = Mock(return_value=members)
    mock_screen.has_expense = Mock(side_effect=lambda types: any(t in expenses for t in types))
    mock_screen.calc_expenses = Mock(side_effect=lambda freq, types: sum(expenses.get(t, 0) for t in types))

    mock_missing_deps = Mock()
    mock_missing_deps.has.return_value = False

    return KsSafesr(mock_screen, mock_program, {}, mock_missing_deps)


def run(calc):
    e = calc.eligible()
    calc.value(e)
    return e.eligible, e.value


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
        # relationship and household_size are deliberately absent: the minor guard
        # is keyed to birth year and no rule reads household size.
        self.assertEqual(
            KsSafesr.dependencies,
            ("age", "income_type", "income_amount", "income_frequency", "expenses"),
        )

    def test_2025_ceiling_is_120_percent_of_the_two_person_fpl(self):
        # An annual cross-check on the published figure, not the source of it —
        # KDOR's published ceiling has not always equalled the formula.
        from programs.models import _FPL_DEFAULTS

        self.assertEqual(round(1.2 * _FPL_DEFAULTS["2025"][2]), KsSafesr.income_limit_by_year[2025])


class TestSpecScenarios(TestCase):
    def test_s1_clearly_eligible_senior_homeowner(self):
        m = make_member(birth_year=1955, income={"sSRetirement": 14_400})
        eligible, value = run(make_calculator([m], property_tax=1_800))
        self.assertTrue(eligible)
        self.assertEqual(value, 1_350)  # 75% x 1800

    def test_s2_income_exactly_at_the_ceiling(self):
        m = make_member(birth_year=1959, income={"sSRetirement": 25_380})
        eligible, value = run(make_calculator([m], property_tax=1_000))
        self.assertTrue(eligible)  # pins the <= comparator from below
        self.assertEqual(value, 750)

    def test_s3_income_just_below_the_ceiling(self):
        m = make_member(birth_year=1958, income={"sSRetirement": 25_280})
        eligible, value = run(make_calculator([m], property_tax=1_200))
        self.assertTrue(eligible)
        self.assertEqual(value, 900)

    def test_s4_income_just_above_the_ceiling(self):
        # Kills the K-40H copy-paste bug: at 50% Social Security this is $12,740
        # and wrongly passes.
        m = make_member(birth_year=1955, income={"sSRetirement": 25_480})
        eligible, _ = run(make_calculator([m], property_tax=1_800))
        self.assertFalse(eligible)

    def test_s5_earliest_qualifying_birth_year(self):
        m = make_member(birth_year=1959, income={"sSRetirement": 10_800})
        eligible, value = run(make_calculator([m], property_tax=800))
        self.assertTrue(eligible)
        self.assertEqual(value, 600)

    def test_s6_turned_65_during_the_year(self):
        # The off-by-one the age rule exists to catch: a current-age snapshot
        # passes this household, birth_year <= 1959 rejects it.
        m = make_member(birth_year=1960, income={"sSRetirement": 10_800})
        eligible, _ = run(make_calculator([m], property_tax=1_200))
        self.assertFalse(eligible)

    def test_s7_age_well_above_the_minimum(self):
        m = make_member(birth_year=1946, income={"sSRetirement": 10_800})
        eligible, value = run(make_calculator([m], property_tax=900))
        self.assertTrue(eligible)
        self.assertEqual(value, 675)

    def test_s8_renter_otherwise_fully_qualified(self):
        m = make_member(birth_year=1954, income={"sSRetirement": 14_400})
        eligible, _ = run(make_calculator([m], rent=800 * 12))
        self.assertFalse(eligible)

    def test_s9_senior_homeowner_receiving_snap(self):
        # SNAP is line 13(a) excluded income and is not an IncomeStream at all,
        # so it neither disqualifies nor counts toward the ceiling.
        m = make_member(birth_year=1956, income={"sSRetirement": 10_800})
        eligible, value = run(make_calculator([m], property_tax=700))
        self.assertTrue(eligible)
        self.assertEqual(value, 525)

    def test_s10_mixed_household_senior_head_younger_spouse_and_adult_child(self):
        # The age test applies to the claimant only; the income test to everyone.
        head = make_member(birth_year=1954, income={"sSRetirement": 8_400})
        spouse = make_member(birth_year=1968, income={"wages": 6_000})
        adult_child = make_member(birth_year=1996, income={"wages": 4_800})
        eligible, value = run(make_calculator([head, spouse, adult_child], property_tax=1_600))
        self.assertTrue(eligible)
        self.assertEqual(value, 1_200)

    def test_s11_two_seniors_in_one_household(self):
        # One claimant per household per year (K.S.A. 79-4507): the refund is
        # household-level, so two qualifying seniors do not pay twice.
        head = make_member(birth_year=1958, income={"sSRetirement": 8_400})
        spouse = make_member(birth_year=1958, income={"sSRetirement": 6_600})
        calc = make_calculator([head, spouse], property_tax=1_000)
        e = calc.eligible()
        calc.value(e)
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 750)
        self.assertEqual(e.household_value, 750)
        self.assertEqual([m.value for m in e.eligible_members], [0, 0])

    def test_s12_adult_childs_income_pushes_the_household_over(self):
        # The only scenario turning on a non-claimant adult's income being
        # counted, and the only one that catches a relationship-keyed skip.
        head = make_member(birth_year=1953, income={"sSRetirement": 8_400})
        adult_child = make_member(birth_year=1990, income={"wages": 18_000})
        eligible, _ = run(make_calculator([head, adult_child], property_tax=1_200))
        self.assertFalse(eligible)  # 26,400 > 25,380

    def test_s13_senior_with_zero_income(self):
        m = make_member(birth_year=1951, income={})
        eligible, value = run(make_calculator([m], property_tax=600))
        self.assertTrue(eligible)
        self.assertEqual(value, 450)

    def test_s14_no_housing_expense_entered(self):
        # A blank housing section is a homeowner, and the value falls back.
        m = make_member(birth_year=1955, income={"sSRetirement": 14_400})
        eligible, value = run(make_calculator([m]))
        self.assertTrue(eligible)
        self.assertEqual(value, 1_756)  # 75% x 2342 = 1756.50, rounded

    def test_s15_mortgage_entered_no_property_tax(self):
        m = make_member(birth_year=1953, income={"sSRetirement": 13_200})
        eligible, value = run(make_calculator([m], mortgage=650 * 12))
        self.assertTrue(eligible)
        self.assertEqual(value, 1_756)

    def test_s16_property_tax_row_entered_at_zero(self):
        # Gating the value on has_expense(["propertyTax"]) computes 75% x $0 and
        # hands an eligible household a $0 refund; scenarios 14 and 15 both pass
        # that calculator, this one does not.
        m = make_member(birth_year=1955, income={"sSRetirement": 14_400})
        eligible, value = run(make_calculator([m], property_tax=0))
        self.assertTrue(eligible)
        self.assertEqual(value, 1_756)

    def test_s17_ssdi_and_gifts_are_excluded(self):
        # Gross is $37,200; SAFESR household income is $23,400. Each exclusion
        # crosses the ceiling on its own.
        head = make_member(birth_year=1952, income={"sSRetirement": 23_400, "gifts": 3_000})
        adult_child = make_member(birth_year=1985, income={"sSDisability": 10_800})
        eligible, value = run(make_calculator([head, adult_child], property_tax=1_200))
        self.assertTrue(eligible)
        self.assertEqual(value, 900)

    def test_s18_grandchild_who_turns_18_mid_year_plus_child_support(self):
        # Three ways of building this wrong cross the ceiling: keying the skip to
        # relationship (grandChild is not in K-40H's tuple), writing the cutoff as
        # birth_year > claim_year - 18, and omitting childSupport.
        head = make_member(birth_year=1953, income={"sSRetirement": 22_800, "childSupport": 5_000})
        grandchild = make_member(birth_year=2007, income={"wages": 4_800})
        eligible, value = run(make_calculator([head, grandchild], property_tax=1_200))
        self.assertTrue(eligible)
        self.assertEqual(value, 900)

    def test_s19_grandchild_who_was_18_all_year(self):
        # The other half of the adulthood boundary: a cutoff one year too broad
        # returns eligible here.
        head = make_member(birth_year=1952, income={"sSRetirement": 22_800})
        grandchild = make_member(birth_year=2006, income={"wages": 4_800})
        eligible, _ = run(make_calculator([head, grandchild], property_tax=1_200))
        self.assertFalse(eligible)  # 27,600 > 25,380

    def test_s20_veterans_benefits_excluded(self):
        # Gross is $27,600; SAFESR household income is $19,200 once the bucket
        # drops. Counting it — which K-40H does — returns not eligible.
        m = make_member(birth_year=1950, income={"sSRetirement": 19_200, "veteran": 8_400})
        eligible, value = run(make_calculator([m], property_tax=1_400))
        self.assertTrue(eligible)
        self.assertEqual(value, 1_050)


class TestIncomeDefinition(TestCase):
    """The 100%-Social-Security rule, one stream at a time."""

    def test_all_four_social_security_streams_count_at_full_value(self):
        # $6,400 x 4 = $25,600, over the ceiling. At K-40H's 50% on the first
        # three this is $16,000 and passes.
        m = make_member(
            birth_year=1950,
            income={"sSRetirement": 6_400, "sSSurvivor": 6_400, "sSI": 6_400, "sSDependent": 6_400},
        )
        eligible, _ = run(make_calculator([m], property_tax=1_200))
        self.assertFalse(eligible)

    def test_household_income_sums_every_countable_stream(self):
        m = make_member(
            birth_year=1950,
            income={
                "wages": 1_000,
                "selfEmployment": 1_000,
                "pension": 1_000,
                "deferredComp": 1_000,
                "investment": 1_000,
                "rental": 1_000,
                "boarder": 1_000,
                "unemployment": 1_000,
                "workersComp": 1_000,
                "cashAssistance": 1_000,
                "cashAssistanceOther": 1_000,
                "alimony": 1_000,
            },
        )
        calc = make_calculator([m], property_tax=1_200)
        self.assertEqual(calc._household_income(), 12_000)

    def test_excluded_streams_alone_leave_zero_income(self):
        m = make_member(
            birth_year=1950,
            income={"sSDisability": 30_000, "childSupport": 30_000, "gifts": 30_000, "veteran": 30_000},
        )
        calc = make_calculator([m], property_tax=1_200)
        self.assertEqual(calc._household_income(), 0)

    def test_member_with_no_birth_year_is_counted_as_an_adult(self):
        # birth_year is None when birth_year_month is unset. For the income gate
        # the conservative reading is to count them.
        head = make_member(birth_year=1950, income={"sSRetirement": 22_800})
        unknown = make_member(birth_year=None, income={"wages": 4_800})
        calc = make_calculator([head, unknown], property_tax=1_200)
        self.assertEqual(calc._household_income(), 27_600)


class TestAgeGate(TestCase):
    def test_member_with_no_birth_year_fails_the_age_gate(self):
        m = make_member(birth_year=None, income={"sSRetirement": 10_800})
        eligible, _ = run(make_calculator([m], property_tax=1_200))
        self.assertFalse(eligible)

    def test_age_gate_and_ceiling_both_follow_the_configured_year(self):
        calc = make_calculator(claim_year=2025)
        self.assertEqual(calc._claim_year(), 2025)

    def test_claim_year_falls_back_to_the_newest_ceiling_when_program_year_is_none(self):
        # import_program_config only warns when no FederalPoveryLimit row matches,
        # so a mis-seeded config leaves program.year as None.
        calc = make_calculator(claim_year=None)
        self.assertEqual(calc._claim_year(), max(KsSafesr.income_limit_by_year))

    def test_claim_year_falls_back_when_no_ceiling_is_published_for_the_configured_year(self):
        # The fallback is shared so the age gate and the ceiling can never
        # describe different years.
        calc = make_calculator(claim_year=2099)
        self.assertEqual(calc._claim_year(), max(KsSafesr.income_limit_by_year))


class TestValue(TestCase):
    def test_refund_is_never_zero_for_an_eligible_household(self):
        # calc_expenses can only return whole dollars, so the smallest non-zero
        # bill rounds up rather than to $0 — a $0 value would be filtered out of
        # the results page entirely.
        m = make_member(birth_year=1950, income={"sSRetirement": 10_800})
        _, value = run(make_calculator([m], property_tax=1))
        self.assertEqual(value, 1)

    def test_value_rounds_to_whole_dollars(self):
        m = make_member(birth_year=1950, income={"sSRetirement": 10_800})
        _, value = run(make_calculator([m], property_tax=1_001))
        self.assertEqual(value, 751)  # 750.75

    def test_ineligible_household_has_no_value(self):
        m = make_member(birth_year=1955, income={"sSRetirement": 30_000})
        eligible, value = run(make_calculator([m], property_tax=1_800))
        self.assertFalse(eligible)
        self.assertEqual(value, 0)

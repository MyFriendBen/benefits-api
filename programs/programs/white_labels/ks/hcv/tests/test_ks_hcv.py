"""
Unit tests for the KS Housing Choice Voucher calculator.

Every scenario in `spec.md` has a test in `TestKsHcvSpecScenarios`, named for its
scenario number, asserting both eligibility and the exact benefit value. The
scenarios' HUD figures — the FY2026 Very Low Income limits and the FMRs/SAFMRs
quoted in the spec — are passed in rather than fetched, so the tests pin the
calculator's arithmetic without touching the HUD API.

Ages are built the way the calculator reads them: from a `birth_year_month` date
run through the real `HouseholdMember.age_from_date` against the spec's pinned
reference date, 2026-08-27. The mock's raw `age` field is left `None` on purpose,
so any calculator that reads it instead of `calc_age()` fails these tests rather
than passing by coincidence.
"""

from datetime import date
from django.test import TestCase
from unittest.mock import Mock, patch

from integrations.clients.hud_income_limits import HudIncomeClientError
from programs.framework.base import ProgramCalculator
from programs.programs.white_labels.ks.hcv.calculator import KsHcv
from screener.models import HouseholdMember

EARNED_TYPES = frozenset(("wages", "selfEmployment"))

#: The spec pins every stated age to this date; `Screen.get_reference_date()`
#: would otherwise drift with the ambient clock.
REFERENCE_DATE = date(2026, 8, 27)

# FY2026 HUD figures the spec's scenarios quote, so a test reads like its scenario.
WICHITA_VLI = {1: 33_800, 2: 38_600, 3: 43_450, 4: 48_250, 5: 52_150, 6: 56_000, 7: 59_850, 8: 63_700}
TOPEKA_VLI = {1: 34_600, 2: 39_550, 3: 44_500, 4: 49_400, 5: 53_400, 6: 57_350, 7: 61_300, 8: 65_250}
KANSAS_CITY_VLI = {1: 39_700, 2: 45_400, 3: 51_050, 4: 56_700, 5: 61_250, 6: 65_800, 7: 70_350, 8: 74_850}

#: ZIP 67202 — Wichita is a mandatory-SAFMR metro, so these are ZIP-level SAFMRs.
WICHITA_SAFMR = {0: 840, 1: 910, 2: 1_180, 3: 1_550, 4: 1_920}
#: ZIP 66103 — likewise mandatory-SAFMR. The area-wide FMR is higher at 1BR
#: ($1,197), which is what Scenario 15 exists to rule out.
KANSAS_CITY_SAFMR = {0: 1_080, 1: 1_180, 2: 1_340, 3: 1_750, 4: 2_080}
#: Topeka carries no `+` in the FY2026 schedule, so the area FMR applies.
TOPEKA_FMR = {0: 792, 1: 820, 2: 1_057, 3: 1_392, 4: 1_411}


def make_member(
    born=None,
    relationship="headOfHousehold",
    income=None,
    disabled=False,
    visually_impaired=False,
    long_term_disability=False,
    student_full_time=False,
    pregnant=False,
    raw_age=None,
):
    """
    A mock HouseholdMember.

    `born` is a `(year, month)` pair; the member's age is derived from it through
    the real `HouseholdMember.age_from_date` against `REFERENCE_DATE`, exactly as
    `calc_age()` does. `raw_age` sets the deprecated `age` field, which defaults to
    `None` so a calculator reading it is caught.

    `income` maps an income type to an ANNUAL dollar amount, e.g. `{"wages": 21_600}`,
    and `calc_gross_income` reproduces the real model's earned/unearned/exclude
    semantics over it.
    """
    income = income or {}

    member = Mock()
    member.age = raw_age
    member.birth_year_month = date(born[0], born[1], 1) if born else None
    member.relationship = relationship
    member.pregnant = pregnant
    member.disabled = disabled
    member.visually_impaired = visually_impaired
    member.long_term_disability = long_term_disability
    member.student = student_full_time
    member.student_full_time = student_full_time
    member.has_disability = Mock(return_value=bool(disabled or visually_impaired or long_term_disability))

    if born is None:
        member.calc_age = Mock(return_value=raw_age)
    else:
        member.calc_age = Mock(return_value=HouseholdMember.age_from_date(member.birth_year_month, REFERENCE_DATE))

    def calc_gross_income(frequency, types, exclude=()):
        total = 0.0
        for income_type, annual in income.items():
            if income_type in exclude:
                continue
            matched = (
                "all" in types
                or income_type in types
                or ("earned" in types and income_type in EARNED_TYPES)
                or ("unearned" in types and income_type not in EARNED_TYPES)
            )
            if matched:
                total += annual if frequency == "yearly" else annual / 12
        return total

    member.calc_gross_income = Mock(side_effect=calc_gross_income)
    return member


#: Distinguishes "not specified, derive it" from an explicit null household_size.
DERIVE = object()


def make_calculator(members=None, household_size=DERIVE, county="Sedgwick", zipcode="67202", rent=0, mortgage=0):
    if members is None:
        members = [make_member(born=(1990, 3))]
    if household_size is DERIVE:
        household_size = len(members)

    screen = Mock()
    screen.household_size = household_size
    screen.county = county
    screen.zipcode = zipcode
    screen.household_members.all = Mock(return_value=members)
    screen.has_benefit = Mock(return_value=False)
    screen.has_base_benefit = Mock(return_value=False)
    screen.get_reference_date = Mock(return_value=REFERENCE_DATE)

    # Both expense types are present, so a calculator that asks for `mortgage`
    # gets a non-zero answer and Scenario 21 catches it.
    expenses = {"rent": float(rent), "mortgage": float(mortgage)}
    screen.calc_expenses = Mock(
        side_effect=lambda frequency, types: sum(v for t, v in expenses.items() if "all" in types or t in types)
    )

    head = next((m for m in members if m.relationship == "headOfHousehold"), members[0] if members else None)
    screen.get_head = Mock(return_value=head)

    program = Mock()
    program.year.period = "2026"

    missing_deps = Mock()
    missing_deps.has.return_value = False

    return KsHcv(screen, program, {}, missing_deps)


def hud_mocks(income_limit=10_000_000, payment_standard=0):
    """The two HUD lookups the calculator makes, and a patcher over both. Returns
    the mocks so a test can assert on the call as well as stub it."""
    income_mock = Mock(return_value=income_limit)
    payment_mock = Mock(return_value=payment_standard)
    patcher = patch.multiple(
        "programs.programs.white_labels.ks.hcv.calculator.hud_client",
        get_screen_il_ami=income_mock,
        get_screen_payment_standard=payment_mock,
    )
    return patcher, income_mock, payment_mock


def patch_hud(income_limit=10_000_000, payment_standard=0):
    return hud_mocks(income_limit, payment_standard)[0]


class TestKsHcvClassAttributes(TestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(KsHcv, ProgramCalculator))

    def test_program_code(self):
        self.assertEqual(KsHcv.program_code, "ks_hcv")

    def test_registered_in_calculator_registry(self):
        from programs.programs import calculators

        self.assertIs(calculators["ks_hcv"], KsHcv)

    def test_income_gate_is_very_low_income(self):
        """Criterion 1 runs at 50% AMI. Scenario 20 is the only scenario that
        detects a wrong tier, so this pins it directly as well."""
        self.assertEqual(KsHcv.ami_percent, "50%")

    def test_deductions_are_the_published_cy2026_values(self):
        self.assertEqual(KsHcv.dependent_deduction_annual, 500)
        self.assertEqual(KsHcv.elderly_disabled_deduction_annual, 550)

    def test_minimum_rent_is_modelled_at_zero(self):
        """Wichita sets the local minimum rent at $0 outright — sourced, not assumed."""
        self.assertEqual(KsHcv.min_rent_monthly, 0)

    def test_bedroom_map_puts_a_single_person_in_a_studio(self):
        """KS follows TX at size 1 (0BR), not IL/WA (1BR); sizes 2-8 match all three."""
        self.assertEqual(dict(KsHcv.BEDROOM_MAP), {1: 0, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3, 7: 4, 8: 4})

    def test_workers_comp_is_the_type_level_exclusion(self):
        self.assertEqual(KsHcv.EXCLUDED_INCOME_TYPES, ("workersComp",))

    def test_domestic_partner_is_treated_as_a_co_head(self):
        self.assertEqual(KsHcv.HEAD_RELATIONSHIPS, ("headOfHousehold", "spouse", "domesticPartner"))

    def test_no_asset_limit_is_declared(self):
        """Data gap 6: MFB applies no asset or property gate, so there is no limit
        to declare and `household_assets` is not a dependency."""
        self.assertFalse(hasattr(KsHcv, "asset_limit"))
        self.assertNotIn("household_assets", KsHcv.dependencies)

    def test_dependencies(self):
        self.assertEqual(
            KsHcv.dependencies,
            (
                "income_amount",
                "income_frequency",
                "household_size",
                "county",
                "zipcode",
                "age",
                "relationship",
            ),
        )


class TestKsHcvMandatorySafmrAreas(TestCase):
    """The payment standard is only ZIP-level in a metro HUD designates mandatory-
    SAFMR, and the match is exact string equality on HUD's `area_name`."""

    def test_kansas_metros_are_registered(self):
        from integrations.clients.hud_income_limits import hud_client

        self.assertIn("Wichita, KS HUD Metro FMR Area", hud_client.MANDATORY_SAFMR_AREA_NAMES)
        self.assertIn("Kansas City, MO-KS HUD Metro FMR Area", hud_client.MANDATORY_SAFMR_AREA_NAMES)

    def test_topeka_is_not_registered(self):
        from integrations.clients.hud_income_limits import hud_client

        self.assertNotIn("Topeka, KS MSA", hud_client.MANDATORY_SAFMR_AREA_NAMES)


class TestKsHcvAgeDerivation(TestCase):
    """KS reads ages through `calc_age()` — departing from WA, TX and IL, which all
    read the raw `age` field the serializer backfills at create time."""

    def test_age_comes_from_birth_year_month_not_the_raw_field(self):
        # Born March 2016 — 10 as of the reference date — but the stale raw field
        # says 40. A calculator reading `age` finds an adult and counts no dependent.
        child = make_member(born=(2016, 3), relationship="child", raw_age=40)
        calc = make_calculator(members=[make_member(born=(1988, 3)), child])
        self.assertTrue(calc._is_minor(child))
        self.assertEqual(calc._count_dependents(), 1)

    def test_month_granularity_matches_age_from_date(self):
        """A birthday later in the calendar year than the reference month has not
        yet been reached — September 2016 is 9, not 10, on 2026-08-27."""
        self.assertEqual(HouseholdMember.age_from_date(date(2016, 9, 1), REFERENCE_DATE), 9)
        self.assertEqual(HouseholdMember.age_from_date(date(2016, 3, 1), REFERENCE_DATE), 10)

    def test_missing_birth_date_falls_back_to_the_raw_field(self):
        member = make_member(born=None, relationship="child", raw_age=12)
        calc = make_calculator(members=[make_member(born=(1988, 3)), member])
        self.assertTrue(calc._is_minor(member))

    def test_unknown_age_is_treated_as_an_adult(self):
        """No birth date and no raw age: never apply an income exclusion on a guess."""
        member = make_member(born=None, relationship="child", raw_age=None, income={"wages": 12_000})
        calc = make_calculator(members=[make_member(born=(1988, 3)), member])
        self.assertFalse(calc._is_minor(member))
        self.assertEqual(calc._annual_income(), 12_000)


class TestKsHcvBedroomSize(TestCase):
    """The KS statewide subsidy standard."""

    def _bedrooms(self, household_size, members=None):
        return make_calculator(members=members, household_size=household_size)._estimate_bedrooms()

    def test_one_person_is_a_studio(self):
        self.assertEqual(self._bedrooms(1), 0)

    def test_two_people_is_1br(self):
        self.assertEqual(self._bedrooms(2), 1)

    def test_three_people_is_2br(self):
        self.assertEqual(self._bedrooms(3), 2)

    def test_four_people_is_2br(self):
        self.assertEqual(self._bedrooms(4), 2)

    def test_five_people_is_3br(self):
        self.assertEqual(self._bedrooms(5), 3)

    def test_six_people_is_3br(self):
        self.assertEqual(self._bedrooms(6), 3)

    def test_seven_people_is_4br(self):
        self.assertEqual(self._bedrooms(7), 4)

    def test_eight_people_is_4br(self):
        self.assertEqual(self._bedrooms(8), 4)

    def test_a_size_outside_the_table_falls_to_the_largest_published_size(self):
        self.assertEqual(self._bedrooms(12), 4)


class TestKsHcvPregnancyAdjustment(TestCase):
    """24 CFR 982.402(b)(5) — scoped to the bedroom lookup, not the income limit."""

    def test_pregnant_sole_member_is_a_two_person_family_for_the_bedroom_lookup(self):
        calc = make_calculator(members=[make_member(born=(1999, 1), pregnant=True)], household_size=1)
        self.assertEqual(calc._effective_household_size(), 2)
        self.assertEqual(calc._estimate_bedrooms(), 1)

    def test_non_pregnant_sole_member_stays_a_studio(self):
        calc = make_calculator(members=[make_member(born=(1999, 1))], household_size=1)
        self.assertEqual(calc._effective_household_size(), 1)
        self.assertEqual(calc._estimate_bedrooms(), 0)

    def test_pregnancy_in_a_larger_household_triggers_no_adjustment(self):
        members = [make_member(born=(1990, 3), pregnant=True), make_member(born=(1990, 6), relationship="spouse")]
        calc = make_calculator(members=members, household_size=2)
        self.assertEqual(calc._effective_household_size(), 2)
        self.assertEqual(calc._estimate_bedrooms(), 1)

    def test_the_income_limit_still_uses_the_unadjusted_household_size(self):
        calc = make_calculator(members=[make_member(born=(1999, 1), pregnant=True)], household_size=1)
        patcher, income_mock, _ = hud_mocks(income_limit=WICHITA_VLI[1], payment_standard=910)
        with patcher:
            calc.calc()
        self.assertEqual(income_mock.call_args.args[0].household_size, 1)

    def test_a_household_with_no_head_is_not_adjusted(self):
        calc = make_calculator(members=[make_member(born=(1999, 1), relationship="child")], household_size=1)
        calc.screen.get_head = Mock(return_value=None)
        self.assertEqual(calc._effective_household_size(), 1)


class TestKsHcvAnnualIncome(TestCase):
    """24 CFR 5.609 annual income — the quantity both the gate and the value run on."""

    def _income(self, members):
        return make_calculator(members=members)._annual_income()

    def test_minor_earned_income_is_excluded(self):
        members = [
            make_member(born=(1988, 3), income={"wages": 21_600}),
            make_member(born=(2013, 3), relationship="child", income={"wages": 2_400}),
        ]
        self.assertEqual(self._income(members), 21_600)

    def test_minor_unearned_income_still_counts(self):
        """§ 5.609(a)(1) counts unearned income of a dependent under 18."""
        members = [
            make_member(born=(1988, 3)),
            make_member(born=(2013, 3), relationship="child", income={"childSupport": 1_200}),
        ]
        self.assertEqual(self._income(members), 1_200)

    def test_a_minor_head_of_household_contributes_in_full(self):
        """§ 5.609(a)(1) carves out the head and spouse whatever their age."""
        members = [make_member(born=(2009, 3), income={"wages": 9_000})]
        self.assertEqual(self._income(members), 9_000)

    def test_a_minor_spouse_contributes_in_full(self):
        members = [
            make_member(born=(1988, 3)),
            make_member(born=(2009, 3), relationship="spouse", income={"wages": 9_000}),
        ]
        self.assertEqual(self._income(members), 9_000)

    def test_a_minor_domestic_partner_contributes_in_full(self):
        """MFB extends the § 5.609(a)(1) carve-out to a co-head, which the text
        does not name; § 5.403 authorises the substitution elsewhere."""
        members = [
            make_member(born=(1988, 3)),
            make_member(born=(2009, 3), relationship="domesticPartner", income={"wages": 9_000}),
        ]
        self.assertEqual(self._income(members), 9_000)

    def test_dependent_full_time_student_earned_income_is_capped(self):
        members = [
            make_member(born=(1985, 3), income={"wages": 12_000}),
            make_member(born=(2006, 4), relationship="child", student_full_time=True, income={"wages": 6_000}),
        ]
        self.assertEqual(self._income(members), 12_500)

    def test_dependent_student_earning_under_the_cap_counts_in_full(self):
        members = [
            make_member(born=(1985, 3)),
            make_member(born=(2006, 4), relationship="child", student_full_time=True, income={"wages": 300}),
        ]
        self.assertEqual(self._income(members), 300)

    def test_dependent_student_unearned_income_is_not_capped(self):
        members = [
            make_member(born=(1985, 3)),
            make_member(born=(2006, 4), relationship="child", student_full_time=True, income={"childSupport": 6_000}),
        ]
        self.assertEqual(self._income(members), 6_000)

    def test_a_head_who_is_a_full_time_student_is_not_capped(self):
        members = [make_member(born=(2006, 4), student_full_time=True, income={"wages": 6_000})]
        self.assertEqual(self._income(members), 6_000)

    def test_workers_compensation_is_excluded_for_any_member(self):
        members = [
            make_member(born=(1988, 3), income={"wages": 10_800, "workersComp": 2_400}),
            make_member(born=(1990, 6), relationship="spouse", income={"workersComp": 5_000}),
        ]
        self.assertEqual(self._income(members), 10_800)

    def test_foster_member_income_is_excluded_entirely(self):
        """§ 5.609(b)(8) — applied to every `fosterChild`-relationship member (D2),
        across both earned and unearned streams."""
        members = [
            make_member(born=(1991, 3), income={"wages": 21_600}),
            make_member(
                born=(2020, 1), relationship="fosterChild", income={"cashAssistanceOther": 1_800, "wages": 900}
            ),
        ]
        self.assertEqual(self._income(members), 21_600)


class TestKsHcvDependents(TestCase):
    def _count(self, members):
        return make_calculator(members=members)._count_dependents()

    def test_minor_children_count(self):
        members = [
            make_member(born=(1988, 3)),
            make_member(born=(2016, 1), relationship="child"),
            make_member(born=(2020, 1), relationship="child"),
        ]
        self.assertEqual(self._count(members), 2)

    def test_head_spouse_and_domestic_partner_never_count(self):
        members = [
            make_member(born=(2009, 3)),
            make_member(born=(2009, 3), relationship="spouse"),
            make_member(born=(2009, 3), relationship="domesticPartner"),
        ]
        self.assertEqual(self._count(members), 0)

    def test_adult_full_time_student_counts(self):
        members = [
            make_member(born=(1985, 3)),
            make_member(born=(2006, 4), relationship="child", student_full_time=True),
        ]
        self.assertEqual(self._count(members), 1)

    def test_adult_with_a_disability_counts(self):
        """The `_count_dependents` disability limb, which no spec scenario reaches."""
        members = [make_member(born=(1985, 3)), make_member(born=(1995, 4), relationship="sibling", disabled=True)]
        self.assertEqual(self._count(members), 1)

    def test_adult_who_is_neither_student_nor_disabled_does_not_count(self):
        members = [make_member(born=(1958, 3)), make_member(born=(1990, 9), relationship="child")]
        self.assertEqual(self._count(members), 0)

    def test_foster_member_counts_departing_from_the_federal_text(self):
        """D2: `family_size` and the dependent count are not reduced for an
        unconfirmed `fosterChild`, even though their income is excluded."""
        members = [make_member(born=(1988, 3)), make_member(born=(2020, 1), relationship="fosterChild")]
        self.assertEqual(self._count(members), 1)


class TestKsHcvElderlyOrDisabledFamily(TestCase):
    def _flag(self, members):
        return make_calculator(members=members)._is_elderly_or_disabled_family()

    def test_sole_member_62_qualifies(self):
        self.assertTrue(self._flag([make_member(born=(1964, 3))]))

    def test_head_61_does_not(self):
        self.assertFalse(self._flag([make_member(born=(1965, 3))]))

    def test_spouse_62_qualifies(self):
        members = [make_member(born=(1990, 3)), make_member(born=(1964, 3), relationship="spouse")]
        self.assertTrue(self._flag(members))

    def test_domestic_partner_62_qualifies(self):
        members = [make_member(born=(1990, 3)), make_member(born=(1964, 3), relationship="domesticPartner")]
        self.assertTrue(self._flag(members))

    def test_head_with_a_plain_disability_qualifies(self):
        self.assertTrue(self._flag([make_member(born=(1990, 3), disabled=True)]))

    def test_head_who_is_visually_impaired_qualifies(self):
        """`has_disability()` ORs three fields; reading `disabled` alone misses this."""
        self.assertTrue(self._flag([make_member(born=(1990, 3), visually_impaired=True)]))

    def test_head_with_a_long_term_disability_qualifies(self):
        self.assertTrue(self._flag([make_member(born=(1990, 3), long_term_disability=True)]))

    def test_elderly_non_head_member_does_not_qualify_the_family(self):
        members = [make_member(born=(1990, 3)), make_member(born=(1958, 1), relationship="parent")]
        self.assertFalse(self._flag(members))

    def test_child_with_a_disability_does_not_qualify_the_family(self):
        members = [make_member(born=(1990, 3)), make_member(born=(2016, 1), relationship="child", disabled=True)]
        self.assertFalse(self._flag(members))

    def test_unknown_head_age_without_disability_does_not_qualify(self):
        self.assertFalse(self._flag([make_member(born=None, raw_age=None)]))


class TestKsHcvTotalTenantPayment(TestCase):
    """24 CFR 5.628(a), rounded half-up per the Form HUD-50058 instructions."""

    def _ttp(self, annual_income, annual_adjusted=None):
        from decimal import Decimal

        calc = make_calculator()
        adjusted = Decimal(str(annual_income if annual_adjusted is None else annual_adjusted))
        return calc._total_tenant_payment(annual_income, adjusted)

    def test_thirty_percent_prong_governs(self):
        self.assertEqual(self._ttp(21_600), 540)

    def test_ten_percent_prong_governs_when_deductions_dominate(self):
        """Reachable only where deductions exceed two-thirds of income; no spec
        scenario gets there, so it is pinned directly."""
        self.assertEqual(self._ttp(6_000, annual_adjusted=0), 50)

    def test_rounds_half_up_not_half_even(self):
        """Scenario 12's exact tie: half-up gives $743, banker's rounding $742."""
        self.assertEqual(self._ttp(31_200, annual_adjusted=29_700), 743)

    def test_a_half_dollar_a_float_would_lose_still_rounds_up(self):
        """The `/40` form keeps $500.50 exact where `0.30 * (20020 / 12)` does not."""
        self.assertEqual(self._ttp(20_020, annual_adjusted=20_020), 501)

    def test_rounds_below_a_half_dollar_down(self):
        self.assertEqual(self._ttp(10_850, annual_adjusted=10_850), 271)

    def test_zero_income_gives_a_zero_payment_under_the_modelled_minimum_rent(self):
        self.assertEqual(self._ttp(0), 0)

    def test_deductions_never_drive_adjusted_income_negative(self):
        calc = make_calculator(
            members=[
                make_member(born=(1958, 3), income={"sSRetirement": 200}),
                make_member(born=(2016, 1), relationship="child"),
            ]
        )
        self.assertEqual(calc._adjusted_income(200), 0)


class TestKsHcvGrossRentProxy(TestCase):
    def test_reported_rent_is_used_when_present(self):
        calc = make_calculator(rent=900)
        self.assertEqual(calc._gross_rent_proxy(1_180), 900)

    def test_falls_back_to_the_payment_standard_with_no_rent(self):
        calc = make_calculator(rent=0)
        self.assertEqual(calc._gross_rent_proxy(1_180), 1_180)

    def test_mortgage_is_not_a_rent_proxy(self):
        """WA and TX read `["rent", "mortgage"]`; KS follows IL and reads rent only."""
        calc = make_calculator(rent=0, mortgage=700)
        self.assertEqual(calc._gross_rent_proxy(1_180), 1_180)


class TestKsHcvIncomeGate(TestCase):
    def test_income_at_the_limit_is_eligible(self):
        calc = make_calculator(members=[make_member(born=(1988, 3), income={"wages": 33_800})], household_size=1)
        with patch_hud(income_limit=WICHITA_VLI[1], payment_standard=840):
            self.assertTrue(calc.calc().eligible)

    def test_one_dollar_over_the_limit_is_not_eligible(self):
        calc = make_calculator(members=[make_member(born=(1988, 3), income={"wages": 33_801})], household_size=1)
        with patch_hud(income_limit=WICHITA_VLI[1], payment_standard=840):
            self.assertFalse(calc.calc().eligible)

    def test_the_limit_is_looked_up_at_fifty_percent_for_the_screen_and_year(self):
        calc = make_calculator(members=[make_member(born=(1988, 3), income={"wages": 12_000})], household_size=1)
        patcher, income_mock, _ = hud_mocks(income_limit=WICHITA_VLI[1], payment_standard=840)
        with patcher:
            calc.calc()
        self.assertEqual(income_mock.call_args.args[1], "50%")
        self.assertEqual(income_mock.call_args.args[2], "2026")

    def test_null_household_size_passes_the_gate_inclusively(self):
        calc = make_calculator(members=[make_member(born=(1988, 3), income={"wages": 999_999})], household_size=None)
        with patch_hud(income_limit=WICHITA_VLI[1], payment_standard=840):
            self.assertTrue(calc.calc().eligible)

    def test_no_asset_gate_is_applied(self):
        """Data gap 6 — `household_assets` is not HUD's net family assets."""
        calc = make_calculator(members=[make_member(born=(1988, 3), income={"wages": 12_000})], household_size=1)
        calc.screen.household_assets = 500_000
        with patch_hud(income_limit=WICHITA_VLI[1], payment_standard=840):
            self.assertTrue(calc.calc().eligible)

    def test_the_gate_runs_on_excluded_income_not_raw_gross(self):
        """A minor's wages would push this household over the 2-person limit if
        § 5.609(b)(3) were not applied first."""
        members = [
            make_member(born=(1988, 3), income={"wages": 38_000}),
            make_member(born=(2013, 3), relationship="child", income={"wages": 6_000}),
        ]
        calc = make_calculator(members=members, household_size=2)
        with patch_hud(income_limit=WICHITA_VLI[2], payment_standard=910):
            self.assertTrue(calc.calc().eligible)


class TestKsHcvSpecScenarios(TestCase):
    """One test per Test Scenario in spec.md, asserting eligibility and value."""

    def _assert_eligible(self, members, income_limit, payment_standard, expected_value, **kwargs):
        calc = make_calculator(members=members, **kwargs)
        with patch_hud(income_limit=income_limit, payment_standard=payment_standard):
            e = calc.calc()
        self.assertTrue(e.eligible, "expected eligible")
        self.assertEqual(e.value, expected_value)

    def _assert_ineligible(self, members, income_limit, **kwargs):
        calc = make_calculator(members=members, **kwargs)
        with patch_hud(income_limit=income_limit):
            e = calc.calc()
        self.assertFalse(e.eligible)

    def _single_parent_two_children(self):
        """Scenario 1's household, reused by Scenarios 19 and 21."""
        return [
            make_member(born=(1991, 3), income={"wages": 21_600}),  # $1,800/mo
            make_member(born=(2016, 9), relationship="child"),
            make_member(born=(2020, 1), relationship="child"),
        ]

    def _family_of_five_at(self, annual_income):
        """Scenario 13's household, reused by Scenario 20 one dollar higher."""
        return [
            make_member(born=(1985, 3), income={"wages": annual_income}),
            make_member(born=(1987, 9), relationship="spouse"),
            make_member(born=(2012, 4), relationship="child"),
            make_member(born=(2016, 11), relationship="child"),
            make_member(born=(2020, 7), relationship="child"),
        ]

    def test_scenario_1_wichita_single_mother_two_children(self):
        self._assert_eligible(
            self._single_parent_two_children(),
            income_limit=WICHITA_VLI[3],
            payment_standard=WICHITA_SAFMR[2],
            expected_value=7_980,
        )

    def test_scenario_2_single_adult_in_a_studio(self):
        self._assert_eligible(
            [make_member(born=(1991, 9), income={"wages": 21_600})],
            income_limit=WICHITA_VLI[1],
            payment_standard=WICHITA_SAFMR[0],
            expected_value=3_600,
        )

    def test_scenario_3_dual_earner_family_of_four(self):
        members = [
            make_member(born=(1986, 3), income={"wages": 18_000}),  # $1,500/mo
            make_member(born=(1988, 9), relationship="spouse", income={"wages": 8_400}),  # $700/mo
            make_member(born=(2016, 1), relationship="child"),
            make_member(born=(2019, 11), relationship="child"),
        ]
        self._assert_eligible(
            members,
            income_limit=WICHITA_VLI[4],
            payment_standard=WICHITA_SAFMR[2],
            expected_value=6_540,
        )

    def test_scenario_4_couple_at_the_top_of_the_vli_band_floors_at_one_dollar(self):
        """Eligible with a nominal $1, not ineligible and not $0 — at $0 the
        frontend's `programValue(program) > 0` filter would hide the program."""
        members = [
            make_member(born=(1988, 3), income={"wages": 38_000}),
            make_member(born=(1990, 9), relationship="spouse"),
        ]
        self._assert_eligible(
            members,
            income_limit=WICHITA_VLI[2],
            payment_standard=WICHITA_SAFMR[1],
            expected_value=1,
        )

    def test_scenario_5_elderly_single_adult_on_social_security(self):
        self._assert_eligible(
            [make_member(born=(1950, 3), income={"sSRetirement": 11_400})],  # $950/mo
            income_limit=WICHITA_VLI[1],
            payment_standard=WICHITA_SAFMR[0],
            expected_value=6_828,
        )

    def test_scenario_6_disabled_single_adult_on_ssi(self):
        """Disability recorded only as `long_term_disability`, so a calculator
        reading the `disabled` field alone loses the $550 and returns $7,920."""
        self._assert_eligible(
            [make_member(born=(1989, 6), income={"sSI": 7_200}, long_term_disability=True)],
            income_limit=WICHITA_VLI[1],
            payment_standard=WICHITA_SAFMR[0],
            expected_value=8_088,
        )

    def test_scenario_7_multi_generational_household(self):
        members = [
            make_member(born=(1958, 3), income={"sSRetirement": 11_400}),  # head, 68
            make_member(born=(1990, 9), relationship="child", income={"wages": 16_800}),  # adult child, 35
            make_member(born=(2018, 1), relationship="grandChild"),  # 8
        ]
        self._assert_eligible(
            members,
            income_limit=WICHITA_VLI[3],
            payment_standard=WICHITA_SAFMR[2],
            expected_value=6_012,
        )

    def test_scenario_8_seven_person_topeka_household(self):
        """The elderly parent and adult sibling are neither head nor spouse, so no
        elderly/disabled deduction applies despite one member being 68."""
        members = [
            make_member(born=(1990, 3), income={"wages": 16_800}),
            make_member(born=(1992, 9), relationship="spouse", income={"wages": 14_400}),
            make_member(born=(1958, 1), relationship="parent", income={"sSRetirement": 11_400}),
            make_member(born=(1988, 11), relationship="sibling", income={"pension": 7_200}),
            make_member(born=(2014, 4), relationship="child"),
            make_member(born=(2017, 7), relationship="child"),
            make_member(born=(2021, 2), relationship="child"),
        ]
        self._assert_eligible(
            members,
            income_limit=TOPEKA_VLI[7],
            payment_standard=TOPEKA_FMR[4],
            expected_value=2_436,
            county="Shawnee",
            zipcode="66604",
        )

    def test_scenario_9_zero_income_household(self):
        """Kills a $50 minimum-rent floor: with no income TTP must be $0, giving
        the full payment standard as HAP."""
        self._assert_eligible(
            [make_member(born=(1991, 9))],
            income_limit=TOPEKA_VLI[1],
            payment_standard=TOPEKA_FMR[0],
            expected_value=9_504,
            county="Shawnee",
            zipcode="66604",
        )

    def test_scenario_10_foster_income_excluded_without_dependent_count_loss(self):
        members = [
            make_member(born=(1991, 3), income={"wages": 21_600}),
            make_member(born=(2016, 9), relationship="child"),
            make_member(born=(2020, 1), relationship="fosterChild", income={"cashAssistanceOther": 1_800}),
        ]
        self._assert_eligible(
            members,
            income_limit=TOPEKA_VLI[3],
            payment_standard=TOPEKA_FMR[2],
            expected_value=6_504,
            county="Shawnee",
            zipcode="66604",
        )

    def test_scenario_11_couple_with_a_workers_compensation_payment(self):
        members = [
            make_member(born=(1988, 3), income={"wages": 10_800, "workersComp": 2_400}),
            make_member(born=(1990, 6), relationship="spouse", income={"wages": 7_200}),
        ]
        self._assert_eligible(
            members,
            income_limit=WICHITA_VLI[2],
            payment_standard=WICHITA_SAFMR[1],
            expected_value=5_520,
        )

    def test_scenario_12_minor_earned_income_and_the_rounding_tie(self):
        """The suite's only TTP tie that discriminates the rounding rule: $742.50
        is $743 half-up and $742 under Python's banker's `round()`. Do not re-tune
        this household's income."""
        members = [
            make_member(born=(1988, 3), income={"wages": 21_600}),
            make_member(born=(1990, 6), relationship="spouse", income={"wages": 9_600}),
            make_member(born=(2013, 3), relationship="child", income={"wages": 2_400}),  # 13, $200/mo
            make_member(born=(2016, 11), relationship="child"),
            make_member(born=(2020, 7), relationship="child"),
        ]
        self._assert_eligible(
            members,
            income_limit=WICHITA_VLI[5],
            payment_standard=WICHITA_SAFMR[3],
            expected_value=9_684,
        )

    def test_scenario_13_family_of_five_exactly_at_the_vli_limit(self):
        self._assert_eligible(
            self._family_of_five_at(52_150),
            income_limit=WICHITA_VLI[5],
            payment_standard=WICHITA_SAFMR[3],
            expected_value=3_408,
        )

    def test_scenario_14_single_adult_far_above_the_vli_limit(self):
        self._assert_ineligible(
            [make_member(born=(1988, 3), income={"wages": 66_000})],
            income_limit=WICHITA_VLI[1],
        )

    def test_scenario_15_kansas_city_safmr_coverage(self):
        """Kills a SAFMR branch hard-coded to Wichita: at Kansas City's area-wide
        1BR FMR of $1,197 the value would be $8,244, not $8,040."""
        members = [
            make_member(born=(1990, 3), income={"wages": 12_000}),
            make_member(born=(1992, 6), relationship="spouse", income={"wages": 8_400}),
        ]
        self._assert_eligible(
            members,
            income_limit=KANSAS_CITY_VLI[2],
            payment_standard=KANSAS_CITY_SAFMR[1],
            expected_value=8_040,
            county="Wyandotte",
            zipcode="66103",
        )

    def test_scenario_16_pregnant_single_person(self):
        """The pregnancy rule moves the bedroom lookup 0BR → 1BR and leaves the
        income-limit household size at 1."""
        calc = make_calculator(members=[make_member(born=(1999, 1), income={"wages": 14_400}, pregnant=True)])
        patcher, income_mock, payment_mock = hud_mocks(income_limit=WICHITA_VLI[1], payment_standard=WICHITA_SAFMR[1])
        with patcher:
            e = calc.calc()
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 6_600)
        self.assertEqual(payment_mock.call_args.args[1], 1)
        self.assertEqual(income_mock.call_args.args[0].household_size, 1)

    def test_scenario_17_family_size_is_not_reduced_for_a_foster_member(self):
        """Income sits between the 2- and 3-person limits, so a wrongly reduced
        `family_size` screens the household out entirely."""
        members = [
            make_member(born=(1988, 3), income={"wages": 40_000}),
            make_member(born=(2016, 1), relationship="child"),
            make_member(born=(2020, 1), relationship="fosterChild"),
        ]
        self._assert_eligible(
            members,
            income_limit=WICHITA_VLI[3],
            payment_standard=WICHITA_SAFMR[2],
            expected_value=2_460,
        )

    def test_scenario_17_reducing_family_size_would_screen_the_household_out(self):
        """The discriminating half of Scenario 17, asserted directly: at the
        2-person limit of $38,600 the same household is ineligible."""
        members = [
            make_member(born=(1988, 3), income={"wages": 40_000}),
            make_member(born=(2016, 1), relationship="child"),
            make_member(born=(2020, 1), relationship="fosterChild"),
        ]
        self._assert_ineligible(members, income_limit=WICHITA_VLI[2])

    def test_scenario_18_dependent_full_time_student_over_18(self):
        members = [
            make_member(born=(1985, 3), income={"wages": 12_000}),
            make_member(born=(2006, 4), relationship="child", student_full_time=True, income={"wages": 6_000}),
        ]
        self._assert_eligible(
            members,
            income_limit=WICHITA_VLI[2],
            payment_standard=WICHITA_SAFMR[1],
            expected_value=7_320,
        )

    def test_scenario_19_reported_rent_caps_the_hap(self):
        """Scenario 1's household with $900/mo rent: the gross-rent arm governs."""
        self._assert_eligible(
            self._single_parent_two_children(),
            income_limit=WICHITA_VLI[3],
            payment_standard=WICHITA_SAFMR[2],
            expected_value=4_620,
            rent=900,
        )

    def test_scenario_20_family_of_five_one_dollar_over_the_vli_limit(self):
        """The only scenario that detects the income tier: at 80% AMI the 5-person
        limit is $83,400 and this household would be eligible."""
        self._assert_ineligible(self._family_of_five_at(52_151), income_limit=WICHITA_VLI[5])

    def test_scenario_21_a_mortgage_does_not_cap_the_hap(self):
        """Scenario 1's household with a $700/mo mortgage and no rent. A calculator
        reading `["rent", "mortgage"]`, as WA and TX do, returns $2,220."""
        self._assert_eligible(
            self._single_parent_two_children(),
            income_limit=WICHITA_VLI[3],
            payment_standard=WICHITA_SAFMR[2],
            expected_value=7_980,
            mortgage=700,
        )

    def test_scenario_22_elderly_couple_deduction_taken_once(self):
        """Both head and spouse are 62+; summing the deduction over them gives
        $5,304 instead of $5,148."""
        members = [
            make_member(born=(1958, 3), income={"sSRetirement": 11_400}),
            make_member(born=(1961, 6), relationship="spouse", income={"sSRetirement": 8_400}),
        ]
        self._assert_eligible(
            members,
            income_limit=WICHITA_VLI[2],
            payment_standard=WICHITA_SAFMR[1],
            expected_value=5_148,
        )


class TestKsHcvNeverRaises(TestCase):
    """A HUD lookup that raises must never propagate out and break the eligibility
    run. `calc()` finishes and falls back to the safe guess: an income gate we cannot
    evaluate is not eligible, a value we cannot compute is $0 — unfloored, because
    that is a value MFB could not compute rather than one that came out at zero."""

    def _calc(self):
        return make_calculator(members=[make_member(born=(1990, 3), income={"wages": 12_000})], household_size=1)

    def test_income_lookup_hud_error(self):
        calc = self._calc()
        with patch.multiple(
            "programs.programs.white_labels.ks.hcv.calculator.hud_client",
            get_screen_il_ami=Mock(side_effect=HudIncomeClientError("HUD unavailable")),
            get_screen_payment_standard=Mock(return_value=840),
        ):
            e = calc.calc()
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)

    def test_income_lookup_unexpected_exception(self):
        calc = self._calc()
        with patch.multiple(
            "programs.programs.white_labels.ks.hcv.calculator.hud_client",
            get_screen_il_ami=Mock(side_effect=ValueError("unexpected boom")),
            get_screen_payment_standard=Mock(return_value=840),
        ):
            e = calc.calc()
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)

    def test_payment_standard_hud_error_degrades_to_zero_unfloored(self):
        calc = self._calc()
        with patch.multiple(
            "programs.programs.white_labels.ks.hcv.calculator.hud_client",
            get_screen_il_ami=Mock(return_value=WICHITA_VLI[1]),
            get_screen_payment_standard=Mock(side_effect=HudIncomeClientError("no FMR")),
        ):
            e = calc.calc()
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 0)

    def test_payment_standard_unexpected_exception_degrades_to_zero(self):
        calc = self._calc()
        with patch.multiple(
            "programs.programs.white_labels.ks.hcv.calculator.hud_client",
            get_screen_il_ami=Mock(return_value=WICHITA_VLI[1]),
            get_screen_payment_standard=Mock(side_effect=KeyError("unexpected")),
        ):
            e = calc.calc()
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 0)

    def test_unconfigured_program_year_is_not_eligible(self):
        """Reachable with no network call at all — the program `year` must be set."""
        calc = self._calc()
        calc.program.year = None
        e = calc.calc()
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)

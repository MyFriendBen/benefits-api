"""
Unit tests for the MO Housing Choice Voucher calculator.

Every scenario in `spec.md`'s Test Scenarios section has a test in
`TestMoHcvSpecScenarios`, named for its scenario number, asserting both
eligibility and the exact benefit value. The scenarios' HUD figures — the FY2026
Very Low Income limits and the FMRs/SAFMRs quoted in the spec — are passed in
rather than fetched, so the tests pin the calculator's arithmetic without
touching the HUD API.

Ages are built the way the calculator reads them: from a `birth_year_month` date
run through the real `HouseholdMember.age_from_date` against the spec's pinned
reference date, 2026-09-28. The mock's raw `age` field is left `None` on purpose,
so any calculator that reads it instead of `calc_age()` fails these tests rather
than passing by coincidence.

Scenario 11 (eligible immigration status) is not a calculator-level test: the
program spec is explicit that no `MoHcv` branch reads legal status — it is
evaluated entirely through the `legal_status_required` config field and the
results-page citizenship filter. `TestMoHcvSpecScenario11` documents that and
asserts the one thing the calculator *can* promise: its household is otherwise
identical to Scenario 1's and computes the same eligibility and value.
"""

from datetime import date
from decimal import Decimal
from django.test import TestCase
from unittest.mock import Mock, patch

from programs.programs.testing_fixtures.custom_calculator import hud_ami

from programs.framework.base import ProgramCalculator
from programs.programs.white_labels.mo.hcv.calculator import MoHcv
from screener.models import HouseholdMember

EARNED_TYPES = frozenset(("wages", "selfEmployment"))

#: The spec pins every stated age to this date; `Screen.get_reference_date()`
#: would otherwise drift with the ambient clock.
REFERENCE_DATE = date(2026, 9, 28)

# FY2026 HUD Very Low (50%) Income Limits the spec's scenarios quote.
KANSAS_CITY_VLI = {1: 39_700, 2: 45_400, 3: 51_050, 4: 56_700, 5: 61_250, 6: 65_800, 7: 70_350, 8: 74_850}
ST_LOUIS_VLI = {1: 39_750, 2: 45_400, 3: 51_100, 4: 56_750, 5: 61_300, 6: 65_850, 7: 70_400, 8: 74_950}
SPRINGFIELD_VLI = {1: 32_000, 2: 36_600, 3: 41_150, 4: 45_700, 5: 49_400, 6: 53_050, 7: 56_700, 8: 60_350}
COLUMBIA_VLI = {1: 40_750, 2: 46_550, 3: 52_350, 4: 58_150, 5: 62_850, 6: 67_500, 7: 72_150, 8: 76_800}
TEXAS_COUNTY_VLI = {1: 27_150, 2: 31_000, 3: 34_900, 4: 38_750, 5: 41_850, 6: 44_950, 7: 48_050, 8: 51_150}

# FY2026 payment standards (ZIP-level SAFMR for the two mandatory-SAFMR metros,
# area-wide FMR elsewhere), by bedroom count, from the program spec's Benefit
# Value table.
KANSAS_CITY_SAFMR = {0: 940, 1: 1_020, 2: 1_160, 3: 1_510, 4: 1_800}
ST_LOUIS_SAFMR = {0: 910, 1: 950, 2: 1_160, 3: 1_490, 4: 1_730}
SPRINGFIELD_FMR = {0: 877, 1: 883, 2: 1_095, 3: 1_498, 4: 1_701}
COLUMBIA_FMR = {0: 800, 1: 1_011, 2: 1_160, 3: 1_573, 4: 1_861}
TEXAS_COUNTY_FMR = {0: 612, 1: 694, 2: 888, 3: 1_192, 4: 1_490}


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


def make_calculator(
    members=None,
    household_size=DERIVE,
    county="Jackson County",
    zipcode="64130",
    rent=0,
    mortgage=0,
    medical=0,
    childcare=0,
    has_section_8=False,
):
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
    screen.has_base_benefit = Mock(return_value=has_section_8)
    screen.get_reference_date = Mock(return_value=REFERENCE_DATE)

    expenses = {
        "rent": float(rent),
        "mortgage": float(mortgage),
        "medical": float(medical),
        "childCare": float(childcare),
    }
    screen.calc_expenses = Mock(
        side_effect=lambda frequency, types: sum(v for t, v in expenses.items() if "all" in types or t in types)
    )

    head = next((m for m in members if m.relationship == "headOfHousehold"), members[0] if members else None)
    screen.get_head = Mock(return_value=head)

    program = Mock()
    program.year.period = "2026"

    missing_deps = Mock()
    missing_deps.has.return_value = False

    return MoHcv(screen, program, {}, missing_deps)


class TestMoHcvClassAttributes(TestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(MoHcv, ProgramCalculator))

    def test_program_code(self):
        self.assertEqual(MoHcv.program_code, "mo_hcv")

    def test_registered_in_calculator_registry(self):
        from programs.programs import calculators

        self.assertIs(calculators["mo_hcv"], MoHcv)

    def test_income_gate_is_very_low_income(self):
        self.assertEqual(MoHcv.ami_percent, "50%")

    def test_deductions_are_hakc_chapter_6a_pre_hotma_values(self):
        self.assertEqual(MoHcv.dependent_deduction_annual, 480)
        self.assertEqual(MoHcv.elderly_disabled_deduction_annual, 400)

    def test_minimum_rent_is_hakcs_fifty_dollars(self):
        self.assertEqual(MoHcv.min_rent_monthly, 50)

    def test_medical_deduction_floor_is_three_percent_not_post_hotma_ten_percent(self):
        self.assertEqual(MoHcv.medical_deduction_floor_percent, Decimal("0.03"))

    def test_workers_comp_is_the_type_level_exclusion(self):
        self.assertEqual(MoHcv.EXCLUDED_INCOME_TYPES, ("workersComp",))

    def test_domestic_partner_is_treated_as_a_co_head(self):
        self.assertEqual(MoHcv.HEAD_RELATIONSHIPS, ("headOfHousehold", "spouse", "domesticPartner"))

    def test_foster_child_is_the_relationship_excluded_from_income_and_dependents(self):
        self.assertEqual(MoHcv.FOSTER_RELATIONSHIPS, ("fosterChild",))

    def test_no_asset_limit_is_declared(self):
        """No asset or property gate is applied — `household_assets` is not HUD's
        net family assets."""
        self.assertFalse(hasattr(MoHcv, "asset_limit"))
        self.assertNotIn("household_assets", MoHcv.dependencies)

    def test_generation_map_covers_all_fifteen_relationship_values(self):
        self.assertEqual(
            dict(MoHcv.GENERATION_MAP),
            {
                "grandParent": 2,
                "parent": 1,
                "fosterParent": 1,
                "stepParent": 1,
                "headOfHousehold": 0,
                "spouse": 0,
                "domesticPartner": 0,
                "sisterOrBrother": 0,
                "stepSisterOrBrother": 0,
                "boyfriendOrGirlfriend": 0,
                "roommate": 0,
                "relatedOther": 0,
                "child": -1,
                "stepChild": -1,
                "fosterChild": -1,
                "grandChild": -2,
            },
        )

    def test_max_bedrooms_is_four(self):
        self.assertEqual(MoHcv.MAX_BEDROOMS, 4)

    def test_dependencies(self):
        self.assertEqual(
            MoHcv.dependencies,
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


class TestMoHcvMandatorySafmrAreas(TestCase):
    def test_both_missouri_metros_are_registered(self):
        from integrations.clients.hud_income_limits import hud_client

        self.assertIn("Kansas City, MO-KS HUD Metro FMR Area", hud_client.MANDATORY_SAFMR_AREA_NAMES)
        self.assertIn("St. Louis, MO-IL HUD Metro FMR Area", hud_client.MANDATORY_SAFMR_AREA_NAMES)

    def test_springfield_and_columbia_are_not_registered(self):
        from integrations.clients.hud_income_limits import hud_client

        self.assertNotIn("Springfield, MO HUD Metro FMR Area", hud_client.MANDATORY_SAFMR_AREA_NAMES)
        self.assertNotIn("Columbia, MO HUD Metro FMR Area", hud_client.MANDATORY_SAFMR_AREA_NAMES)


class TestMoHcvAgeDerivation(TestCase):
    """MO reads ages through `calc_age()`, never the raw `age` field, matching
    `KsHcv` and departing from `IlHcv`/`TxHcv`/`WaHcv`."""

    def test_age_comes_from_birth_year_month_not_the_raw_field(self):
        # Born March 2016 — 10 as of the reference date — but the stale raw field
        # says 40. A calculator reading `age` finds an adult and counts no dependent.
        child = make_member(born=(2016, 3), relationship="child", raw_age=40)
        calc = make_calculator(members=[make_member(born=(1988, 3)), child])
        self.assertTrue(calc._is_minor(child))
        self.assertEqual(calc._count_dependents(), 1)

    def test_missing_birth_date_falls_back_to_the_raw_field(self):
        member = make_member(born=None, relationship="child", raw_age=12)
        calc = make_calculator(members=[make_member(born=(1988, 3)), member])
        self.assertTrue(calc._is_minor(member))

    def test_unknown_age_is_treated_as_an_adult(self):
        member = make_member(born=None, relationship="child", raw_age=None, income={"wages": 12_000})
        calc = make_calculator(members=[make_member(born=(1988, 3)), member])
        self.assertFalse(calc._is_minor(member))
        self.assertEqual(calc._annual_income(), 12_000)


class TestMoHcvGenerationCountsAndBedrooms(TestCase):
    def test_single_person_is_one_bedroom(self):
        calc = make_calculator(members=[make_member(born=(1990, 3))])
        self.assertEqual(calc._estimate_bedrooms(), 1)

    def test_head_and_spouse_share_one_generation_one_bedroom(self):
        members = [make_member(born=(1990, 3)), make_member(born=(1991, 6), relationship="spouse")]
        calc = make_calculator(members=members)
        self.assertEqual(calc._estimate_bedrooms(), 1)

    def test_head_and_one_child_are_two_generations_two_bedrooms(self):
        members = [make_member(born=(1988, 3)), make_member(born=(2010, 1), relationship="child")]
        calc = make_calculator(members=members)
        self.assertEqual(calc._estimate_bedrooms(), 2)

    def test_grandparent_maps_to_generation_plus_two(self):
        members = [make_member(born=(1988, 3)), make_member(born=(1956, 5), relationship="grandParent")]
        calc = make_calculator(members=members)
        counts = calc._generation_counts()
        self.assertEqual(counts.get(2), 1)

    def test_parent_maps_to_generation_plus_one(self):
        members = [make_member(born=(1988, 3)), make_member(born=(1966, 9), relationship="parent")]
        calc = make_calculator(members=members)
        counts = calc._generation_counts()
        self.assertEqual(counts.get(1), 1)

    def test_grandchild_maps_to_generation_minus_two(self):
        members = [make_member(born=(1960, 3)), make_member(born=(2018, 1), relationship="grandChild")]
        calc = make_calculator(members=members)
        counts = calc._generation_counts()
        self.assertEqual(counts.get(-2), 1)

    def test_roommate_falls_to_generation_zero(self):
        members = [make_member(born=(1990, 3)), make_member(born=(1992, 5), relationship="roommate")]
        calc = make_calculator(members=members)
        counts = calc._generation_counts()
        self.assertEqual(counts, {0: 2})
        self.assertEqual(calc._estimate_bedrooms(), 1)

    def test_related_other_and_boyfriend_or_girlfriend_fall_to_generation_zero(self):
        members = [
            make_member(born=(1990, 3)),
            make_member(born=(1992, 5), relationship="relatedOther"),
            make_member(born=(1991, 7), relationship="boyfriendOrGirlfriend"),
        ]
        calc = make_calculator(members=members)
        self.assertEqual(calc._generation_counts(), {0: 3})

    def test_null_or_unrecognised_relationship_falls_to_generation_zero(self):
        """Not reached by any screen the frontend can submit — the serializer
        requires `relationshipToHH` — but `HouseholdMember.relationship` is
        nullable, so the API can still produce one. The program spec records this
        as a branch no Test Scenario reaches; it is pinned directly here instead."""
        members = [make_member(born=(1990, 3)), make_member(born=(1992, 5), relationship=None)]
        calc = make_calculator(members=members)
        self.assertEqual(calc._generation_counts(), {0: 2})

        members = [make_member(born=(1990, 3)), make_member(born=(1992, 5), relationship="somethingUnmapped")]
        calc = make_calculator(members=members)
        self.assertEqual(calc._generation_counts(), {0: 2})

    def test_bedroom_count_is_capped_at_four(self):
        # Five generations occupied at one member each sums to 5 bedrooms uncapped.
        members = [
            make_member(born=(1960, 3), relationship="grandParent"),
            make_member(born=(1980, 3), relationship="parent"),
            make_member(born=(2000, 3), relationship="headOfHousehold"),
            make_member(born=(2018, 3), relationship="child"),
            make_member(born=(2022, 3), relationship="grandChild"),
        ]
        calc = make_calculator(members=members)
        self.assertEqual(calc._estimate_bedrooms(), 4)

    def test_pregnant_sole_applicant_is_two_bedrooms(self):
        calc = make_calculator(members=[make_member(born=(1999, 1), pregnant=True)], household_size=1)
        self.assertEqual(calc._estimate_bedrooms(), 2)

    def test_non_pregnant_sole_applicant_stays_one_bedroom(self):
        calc = make_calculator(members=[make_member(born=(1999, 1))], household_size=1)
        self.assertEqual(calc._estimate_bedrooms(), 1)

    def test_pregnancy_in_a_larger_household_triggers_no_adjustment(self):
        members = [make_member(born=(1990, 3), pregnant=True), make_member(born=(1990, 6), relationship="spouse")]
        calc = make_calculator(members=members, household_size=2)
        self.assertEqual(calc._estimate_bedrooms(), 1)

    def test_a_household_with_no_head_is_not_adjusted_for_pregnancy(self):
        calc = make_calculator(members=[make_member(born=(1999, 1), relationship="child")], household_size=1)
        calc.screen.get_head = Mock(return_value=None)
        self.assertEqual(calc._estimate_bedrooms(), 1)

    def test_the_income_limit_still_uses_the_real_household_size_for_a_pregnant_applicant(self):
        calc = make_calculator(members=[make_member(born=(1999, 1), pregnant=True)], household_size=1)
        with hud_ami(MoHcv, KANSAS_CITY_VLI[1], payment_standard=1_160):
            calc.calc()
        # The real household_size (1), not the notional 2, is what gets compared.
        self.assertEqual(calc.screen.household_size, 1)


class TestMoHcvAnnualIncome(TestCase):
    def _income(self, members):
        return make_calculator(members=members)._annual_income()

    def test_minor_earned_income_is_excluded(self):
        members = [
            make_member(born=(1988, 3), income={"wages": 21_600}),
            make_member(born=(2013, 3), relationship="child", income={"wages": 2_400}),
        ]
        self.assertEqual(self._income(members), 21_600)

    def test_minor_unearned_income_still_counts(self):
        members = [
            make_member(born=(1988, 3)),
            make_member(born=(2013, 3), relationship="child", income={"childSupport": 1_200}),
        ]
        self.assertEqual(self._income(members), 1_200)

    def test_a_minor_head_of_household_contributes_in_full(self):
        members = [make_member(born=(2009, 3), income={"wages": 9_000})]
        self.assertEqual(self._income(members), 9_000)

    def test_a_minor_spouse_contributes_in_full(self):
        members = [
            make_member(born=(1988, 3)),
            make_member(born=(2009, 3), relationship="spouse", income={"wages": 9_000}),
        ]
        self.assertEqual(self._income(members), 9_000)

    def test_a_minor_domestic_partner_contributes_in_full(self):
        members = [
            make_member(born=(1988, 3)),
            make_member(born=(2009, 3), relationship="domesticPartner", income={"wages": 9_000}),
        ]
        self.assertEqual(self._income(members), 9_000)

    def test_dependent_full_time_student_earned_income_is_capped_at_480(self):
        members = [
            make_member(born=(1985, 3), income={"wages": 12_000}),
            make_member(born=(2006, 4), relationship="child", student_full_time=True, income={"wages": 6_000}),
        ]
        self.assertEqual(self._income(members), 12_480)

    def test_minor_and_full_time_student_is_excluded_in_full_not_capped(self):
        """§ 5.609(b)(3) must run before (b)(14): a member who is both under 18 and
        a full-time student is excluded in full, not capped at $480."""
        members = [
            make_member(born=(1988, 3), income={"wages": 40_000}),
            make_member(born=(2010, 1), relationship="child", student_full_time=True, income={"wages": 10_000}),
        ]
        self.assertEqual(self._income(members), 40_000)

    def test_workers_compensation_is_excluded_for_any_member(self):
        members = [
            make_member(born=(1988, 3), income={"wages": 10_800, "workersComp": 2_400}),
            make_member(born=(1990, 6), relationship="spouse", income={"workersComp": 5_000}),
        ]
        self.assertEqual(self._income(members), 10_800)

    def test_foster_member_income_is_excluded_entirely(self):
        members = [
            make_member(born=(1986, 2), income={"wages": 30_000}),
            make_member(born=(2007, 1), relationship="fosterChild", income={"wages": 5_000}),
        ]
        self.assertEqual(self._income(members), 30_000)

    def test_adult_non_student_non_disabled_is_not_excluded(self):
        members = [
            make_member(born=(1990, 3), income={"wages": 36_000}),
            make_member(born=(2008, 9), relationship="child", income={"wages": 8_000}),
        ]
        self.assertEqual(self._income(members), 44_000)


class TestMoHcvDependents(TestCase):
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
        members = [
            make_member(born=(1985, 3)),
            make_member(born=(1995, 4), relationship="sisterOrBrother", disabled=True),
        ]
        self.assertEqual(self._count(members), 1)

    def test_adult_who_is_neither_student_nor_disabled_does_not_count(self):
        members = [make_member(born=(1958, 3)), make_member(born=(1990, 9), relationship="child")]
        self.assertEqual(self._count(members), 0)

    def test_foster_child_never_counts_even_when_young(self):
        """MO excludes `fosterChild` from the dependent definition (§ 5.603),
        departing from `IlHcv`, `KsHcv` and `WaHcv`, which retain them."""
        members = [make_member(born=(1986, 2)), make_member(born=(2016, 4), relationship="fosterChild")]
        self.assertEqual(self._count(members), 0)

    def test_foster_child_does_not_count_even_if_disabled_or_a_student(self):
        members = [
            make_member(born=(1986, 2)),
            make_member(born=(2006, 4), relationship="fosterChild", student_full_time=True),
        ]
        self.assertEqual(self._count(members), 0)


class TestMoHcvElderlyOrDisabledFamily(TestCase):
    def _flag(self, members):
        return make_calculator(members=members)._is_elderly_or_disabled_family()

    def test_sole_member_62_qualifies(self):
        self.assertTrue(self._flag([make_member(born=(1964, 9))]))

    def test_head_61_does_not(self):
        self.assertFalse(self._flag([make_member(born=(1965, 3))]))

    def test_spouse_62_qualifies(self):
        members = [make_member(born=(1990, 3)), make_member(born=(1964, 9), relationship="spouse")]
        self.assertTrue(self._flag(members))

    def test_domestic_partner_62_qualifies(self):
        members = [make_member(born=(1990, 3)), make_member(born=(1964, 9), relationship="domesticPartner")]
        self.assertTrue(self._flag(members))

    def test_head_with_a_plain_disability_qualifies(self):
        self.assertTrue(self._flag([make_member(born=(1990, 3), disabled=True)]))

    def test_head_who_is_visually_impaired_qualifies(self):
        self.assertTrue(self._flag([make_member(born=(1990, 3), visually_impaired=True)]))

    def test_head_with_a_long_term_disability_qualifies(self):
        self.assertTrue(self._flag([make_member(born=(1990, 3), long_term_disability=True)]))

    def test_elderly_non_head_relationship_member_does_not_qualify_the_family(self):
        """Scenario 22's rule from outside: a 70-year-old `grandParent` is not head,
        co-head or spouse, so no deduction is taken."""
        members = [make_member(born=(1990, 3)), make_member(born=(1956, 5), relationship="grandParent")]
        self.assertFalse(self._flag(members))

    def test_disabled_domestic_partner_qualifies_through_disability(self):
        members = [
            make_member(born=(1986, 3)),
            make_member(born=(1981, 4), relationship="domesticPartner", disabled=True),
        ]
        self.assertTrue(self._flag(members))

    def test_unknown_head_age_without_disability_does_not_qualify(self):
        self.assertFalse(self._flag([make_member(born=None, raw_age=None)]))


class TestMoHcvMedicalDeduction(TestCase):
    def test_no_deduction_when_not_elderly_or_disabled(self):
        calc = make_calculator(members=[make_member(born=(1990, 3))], medical=200 * 12)
        self.assertEqual(calc._adjusted_income(20_000), Decimal(20_000))

    def test_deduction_is_medical_minus_three_percent_floor(self):
        calc = make_calculator(members=[make_member(born=(1956, 3), income={"wages": 20_000})], medical=200 * 12)
        # medical $2,400, floor 3% * $20,000 = $600, deduction = $1,800.
        self.assertEqual(calc._medical_deduction(Decimal(20_000)), Decimal(1_800))

    def test_deduction_floors_at_zero_when_expenses_are_below_the_floor(self):
        calc = make_calculator(members=[make_member(born=(1956, 3))], medical=100)
        self.assertEqual(calc._medical_deduction(Decimal(20_000)), Decimal(0))


class TestMoHcvChildcareDeduction(TestCase):
    def test_uncapped_when_no_member_has_included_earned_income(self):
        members = [make_member(born=(1990, 3), income={"unemployment": 15_000})]
        calc = make_calculator(members=members, childcare=10_000)
        self.assertEqual(calc._childcare_deduction(), Decimal(10_000))

    def test_capped_at_the_single_earners_included_income(self):
        members = [make_member(born=(1990, 3), income={"wages": 5_000, "unemployment": 15_000})]
        calc = make_calculator(members=members, childcare=7_800)
        self.assertEqual(calc._childcare_deduction(), Decimal(5_000))

    def test_capped_at_the_lowest_paid_of_two_earners_not_the_sum(self):
        members = [
            make_member(born=(1988, 3), income={"wages": 30_000}),
            make_member(born=(1990, 5), relationship="spouse", income={"wages": 12_000}),
        ]
        calc = make_calculator(members=members, childcare=18_000)
        self.assertEqual(calc._childcare_deduction(), Decimal(12_000))

    def test_excluded_minor_earner_is_not_in_the_earner_list(self):
        """§ 5.609(b)(3) zeroes the minor's earnings before the earner list is
        built, so the cap is the head's own wages, not the minor's."""
        members = [
            make_member(born=(1991, 3), income={"wages": 30_000}),
            make_member(born=(2010, 6), relationship="child", income={"wages": 6_000}),
        ]
        calc = make_calculator(members=members, childcare=8_000)
        self.assertEqual(calc._childcare_deduction(), Decimal(8_000))

    def test_foster_child_earner_is_not_in_the_earner_list(self):
        members = [
            make_member(born=(1986, 2), income={"wages": 30_000}),
            make_member(born=(2007, 1), relationship="fosterChild", income={"wages": 20_000}),
        ]
        calc = make_calculator(members=members, childcare=25_000)
        self.assertEqual(calc._childcare_deduction(), Decimal(25_000))

    def test_partly_excluded_student_earner_sets_the_cap_at_480(self):
        """§ 5.609(b)(14) leaves a dependent full-time student $480 of included
        earned income — enough to make them the lowest-paid earner."""
        members = [
            make_member(born=(1986, 3), income={"wages": 28_000}),
            make_member(born=(2007, 5), relationship="child", student_full_time=True, income={"wages": 5_000}),
        ]
        calc = make_calculator(members=members, childcare=3_000)
        self.assertEqual(calc._childcare_deduction(), Decimal(480))

    def test_no_childcare_expense_is_zero(self):
        calc = make_calculator(members=[make_member(born=(1990, 3), income={"wages": 20_000})], childcare=0)
        self.assertEqual(calc._childcare_deduction(), Decimal(0))


class TestMoHcvTotalTenantPayment(TestCase):
    def _ttp(self, annual_income, annual_adjusted=None):
        calc = make_calculator()
        adjusted = Decimal(str(annual_income if annual_adjusted is None else annual_adjusted))
        return calc._total_tenant_payment(annual_income, adjusted)

    def test_thirty_percent_prong_governs(self):
        self.assertEqual(self._ttp(35_040), 876)

    def test_ten_percent_prong_governs_when_deductions_dominate(self):
        self.assertEqual(self._ttp(15_000, annual_adjusted=4_040), 125)

    def test_minimum_rent_prong_governs_when_both_percentages_fall_below_it(self):
        self.assertEqual(self._ttp(3_600, annual_adjusted=0), 50)

    def test_rounds_half_up_not_half_even(self):
        # 30% of $4,645.00/mo = $1,393.50 — half-up gives $1,394, banker's $1,394
        # agrees here, so use an odd-cents case: 30% of monthly $1,712.42 = $513.73.
        self.assertEqual(self._ttp(24_300, annual_adjusted=20_549), 514)

    def test_zero_income_gives_the_minimum_rent(self):
        self.assertEqual(self._ttp(0), 50)

    def test_deductions_never_drive_adjusted_income_negative(self):
        calc = make_calculator(
            members=[
                make_member(born=(1958, 3), income={"sSRetirement": 200}),
                make_member(born=(2016, 1), relationship="child"),
            ]
        )
        self.assertEqual(calc._adjusted_income(200), Decimal(0))


class TestMoHcvGrossRentProxy(TestCase):
    def test_reported_rent_is_used_when_present(self):
        calc = make_calculator(rent=900)
        self.assertEqual(calc._gross_rent_proxy(1_160), 900)

    def test_falls_back_to_the_payment_standard_with_no_rent(self):
        calc = make_calculator(rent=0)
        self.assertEqual(calc._gross_rent_proxy(1_160), 1_160)

    def test_mortgage_is_not_a_rent_proxy(self):
        calc = make_calculator(rent=0, mortgage=700)
        self.assertEqual(calc._gross_rent_proxy(1_020), 1_020)


class TestMoHcvHouseholdEligible(TestCase):
    def test_household_size_trivially_passes(self):
        calc = make_calculator(members=[make_member(born=(1988, 3), income={"wages": 12_000})], household_size=1)
        with hud_ami(MoHcv, KANSAS_CITY_VLI[1], payment_standard=1_020):
            e = calc.calc()
        self.assertTrue(e.eligible)

    def test_already_holding_section_8_is_ineligible(self):
        calc = make_calculator(
            members=[make_member(born=(1988, 3), income={"wages": 12_000})],
            household_size=1,
            has_section_8=True,
        )
        with hud_ami(MoHcv, KANSAS_CITY_VLI[1], payment_standard=1_020):
            e = calc.calc()
        self.assertFalse(e.eligible)

    def test_not_holding_section_8_proceeds_normally(self):
        calc = make_calculator(
            members=[make_member(born=(1988, 3), income={"wages": 12_000})],
            household_size=1,
            has_section_8=False,
        )
        with hud_ami(MoHcv, KANSAS_CITY_VLI[1], payment_standard=1_020):
            e = calc.calc()
        self.assertTrue(e.eligible)

    def test_checks_has_base_benefit_with_section_8(self):
        calc = make_calculator(members=[make_member(born=(1988, 3), income={"wages": 12_000})], household_size=1)
        with hud_ami(MoHcv, KANSAS_CITY_VLI[1], payment_standard=1_020):
            calc.calc()
        calc.screen.has_base_benefit.assert_called_with("section_8")

    def test_income_at_the_limit_is_eligible(self):
        calc = make_calculator(members=[make_member(born=(1988, 3), income={"wages": 39_700})], household_size=1)
        with hud_ami(MoHcv, KANSAS_CITY_VLI[1], payment_standard=1_020):
            self.assertTrue(calc.calc().eligible)

    def test_one_dollar_over_the_limit_is_not_eligible(self):
        calc = make_calculator(members=[make_member(born=(1988, 3), income={"wages": 39_701})], household_size=1)
        with hud_ami(MoHcv, KANSAS_CITY_VLI[1], payment_standard=1_020):
            self.assertFalse(calc.calc().eligible)

    def test_the_limit_is_looked_up_at_fifty_percent_for_the_screen_and_year(self):
        calc = make_calculator(members=[make_member(born=(1988, 3), income={"wages": 12_000})], household_size=1)
        with hud_ami(MoHcv, KANSAS_CITY_VLI[1], payment_standard=1_020) as hud:
            calc.calc()
        self.assertEqual(hud.get_screen_il_ami.call_args.args[1], "50%")
        self.assertEqual(hud.get_screen_il_ami.call_args.args[2], "2026")

    def test_null_household_size_passes_the_gate_inclusively(self):
        calc = make_calculator(members=[make_member(born=(1988, 3), income={"wages": 999_999})], household_size=None)
        with hud_ami(MoHcv, KANSAS_CITY_VLI[1], payment_standard=1_020):
            self.assertTrue(calc.calc().eligible)

    def test_no_asset_gate_is_applied(self):
        calc = make_calculator(members=[make_member(born=(1988, 3), income={"wages": 12_000})], household_size=1)
        calc.screen.household_assets = 500_000
        with hud_ami(MoHcv, KANSAS_CITY_VLI[1], payment_standard=1_020):
            self.assertTrue(calc.calc().eligible)


class TestMoHcvNeverRaises(TestCase):
    def _calc(self):
        return make_calculator(members=[make_member(born=(1990, 3), income={"wages": 12_000})], household_size=1)

    def test_income_lookup_hud_error(self):
        calc = self._calc()
        with hud_ami(MoHcv, unavailable=True, payment_standard=1_020):
            e = calc.calc()
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)

    def test_income_lookup_unexpected_exception(self):
        calc = self._calc()
        with patch.multiple(
            "programs.programs.white_labels.mo.hcv.calculator.hud_client",
            get_screen_il_ami=Mock(side_effect=ValueError("unexpected boom")),
            get_screen_payment_standard=Mock(return_value=1_020),
        ):
            e = calc.calc()
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)

    def test_payment_standard_hud_error_degrades_to_zero_unfloored(self):
        calc = self._calc()
        with hud_ami(MoHcv, KANSAS_CITY_VLI[1], payment_standard_unavailable=True):
            e = calc.calc()
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 0)

    def test_payment_standard_unexpected_exception_degrades_to_zero(self):
        calc = self._calc()
        with patch.multiple(
            "programs.programs.white_labels.mo.hcv.calculator.hud_client",
            get_screen_il_ami=Mock(return_value=KANSAS_CITY_VLI[1]),
            get_screen_payment_standard=Mock(side_effect=KeyError("unexpected")),
        ):
            e = calc.calc()
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 0)

    def test_unconfigured_program_year_is_not_eligible(self):
        calc = self._calc()
        calc.program.year = None
        e = calc.calc()
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)


class TestMoHcvSpecScenarios(TestCase):
    """One test per Test Scenario in spec.md, asserting eligibility and value."""

    def _assert_eligible(self, members, income_limit, payment_standard, expected_value, **kwargs):
        calc = make_calculator(members=members, **kwargs)
        with hud_ami(MoHcv, income_limit, payment_standard=payment_standard):
            e = calc.calc()
        self.assertTrue(e.eligible, "expected eligible")
        self.assertEqual(e.value, expected_value)

    def _assert_ineligible(self, members, income_limit, **kwargs):
        calc = make_calculator(members=members, **kwargs)
        with hud_ami(MoHcv, income_limit):
            e = calc.calc()
        self.assertFalse(e.eligible)

    def _kc_family_of_four(self, head_income):
        """Scenarios 1, 2, 3, 5 and 9's household."""
        return [
            make_member(born=(1990, 3), income={"wages": head_income}),
            make_member(born=(1991, 6), relationship="spouse"),
            make_member(born=(2014, 4), relationship="child"),
            make_member(born=(2018, 9), relationship="child"),
        ]

    def test_scenario_1_kansas_city_family_well_within_the_income_limit(self):
        self._assert_eligible(
            self._kc_family_of_four(36_000),
            income_limit=KANSAS_CITY_VLI[4],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=3_408,
            rent=1_900,
        )

    def test_scenario_2_kansas_city_family_exactly_at_the_income_limit_floors_at_one_dollar(self):
        self._assert_eligible(
            self._kc_family_of_four(56_700),
            income_limit=KANSAS_CITY_VLI[4],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=1,
            rent=1_900,
        )

    def test_scenario_3_kansas_city_family_one_dollar_over_the_income_limit(self):
        self._assert_ineligible(
            self._kc_family_of_four(56_701),
            income_limit=KANSAS_CITY_VLI[4],
            rent=1_900,
        )

    def test_scenario_4_st_louis_income_under_st_louis_limit_but_over_springfields(self):
        members = [
            make_member(born=(1988, 3), income={"wages": 50_000}),
            make_member(born=(1989, 6), relationship="spouse"),
            make_member(born=(2013, 4), relationship="child"),
            make_member(born=(2016, 8), relationship="child"),
            make_member(born=(2019, 5), relationship="child"),
        ]
        self._assert_eligible(
            members,
            income_limit=ST_LOUIS_VLI[5],
            payment_standard=ST_LOUIS_SAFMR[3],
            expected_value=3_312,
            county="St. Louis City",
            zipcode="63118",
            rent=1_900,
        )

    def test_scenario_5_kansas_city_family_already_holding_a_voucher(self):
        self._assert_ineligible(
            self._kc_family_of_four(36_000),
            income_limit=KANSAS_CITY_VLI[4],
            rent=1_900,
            has_section_8=True,
        )

    def test_scenario_6_single_adult_in_springfield(self):
        self._assert_eligible(
            [make_member(born=(1996, 7), income={"wages": 18_000})],
            income_limit=SPRINGFIELD_VLI[1],
            payment_standard=SPRINGFIELD_FMR[1],
            expected_value=5_196,
            county="Greene County",
            zipcode="65806",
            rent=900,
        )

    def test_scenario_7_five_person_columbia_household(self):
        members = [
            make_member(born=(1988, 3), income={"wages": 40_000}),
            make_member(born=(1989, 6), relationship="spouse"),
            make_member(born=(2013, 4), relationship="child"),
            make_member(born=(2016, 8), relationship="child"),
            make_member(born=(2019, 5), relationship="child"),
        ]
        self._assert_eligible(
            members,
            income_limit=COLUMBIA_VLI[5],
            payment_standard=COLUMBIA_FMR[3],
            expected_value=7_308,
            county="Boone County",
            zipcode="65203",
            rent=2_000,
        )

    def test_scenario_8_rural_non_metro_household_in_texas_county(self):
        members = [
            make_member(born=(1985, 3), income={"wages": 38_000}),
            make_member(born=(1986, 6), relationship="spouse"),
            make_member(born=(2007, 1), relationship="child", student_full_time=True, income={"wages": 5_000}),
            make_member(born=(2012, 4), relationship="child"),
            make_member(born=(2014, 8), relationship="child"),
            make_member(born=(2017, 5), relationship="child"),
            make_member(born=(2020, 2), relationship="child"),
        ]
        self._assert_eligible(
            members,
            income_limit=TEXAS_COUNTY_VLI[7],
            payment_standard=TEXAS_COUNTY_FMR[4],
            expected_value=3_576,
            county="Texas County",
            zipcode="65483",
            rent=1_200,
        )

    def test_scenario_9_kansas_city_family_renting_below_the_payment_standard(self):
        self._assert_eligible(
            self._kc_family_of_four(36_000),
            income_limit=KANSAS_CITY_VLI[4],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=1_488,
            rent=1_000,
        )

    def test_scenario_10_kansas_city_single_adult_with_an_elderly_deduction(self):
        self._assert_eligible(
            [make_member(born=(1963, 1), income={"wages": 30_000})],
            income_limit=KANSAS_CITY_VLI[1],
            payment_standard=KANSAS_CITY_SAFMR[1],
            expected_value=3_360,
            rent=1_200,
        )

    def test_scenario_11_eligible_immigration_status_is_config_only(self):
        """Criterion 3 is evaluated at `config` scope via `legal_status_required`
        and the results-page citizenship filter — no `MoHcv` branch reads legal
        status, so this scenario cannot be exercised as a calculator-level unit
        test. What the calculator *can* promise is asserted instead: this is
        Scenario 1's exact household, which the calculator computes as eligible
        at the same value regardless of any citizenship selection, because that
        selection is applied by a different layer entirely."""
        self._assert_eligible(
            self._kc_family_of_four(36_000),
            income_limit=KANSAS_CITY_VLI[4],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=3_408,
            rent=1_900,
        )

    def test_scenario_12_minors_earned_income_excluded_and_generations_bedroom_rule(self):
        members = [
            make_member(born=(1988, 3), income={"wages": 40_000}),
            make_member(born=(2010, 1), relationship="child", income={"wages": 10_000}),
        ]
        self._assert_eligible(
            members,
            income_limit=KANSAS_CITY_VLI[2],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=2_064,
            rent=1_500,
        )

    def test_scenario_13_kansas_city_single_adult_reporting_no_current_rent(self):
        self._assert_eligible(
            [make_member(born=(1996, 7), income={"wages": 20_000})],
            income_limit=KANSAS_CITY_VLI[1],
            payment_standard=KANSAS_CITY_SAFMR[1],
            expected_value=6_240,
            rent=0,
        )

    def test_scenario_14_kansas_city_single_adult_aged_exactly_62(self):
        self._assert_eligible(
            [make_member(born=(1964, 9), income={"wages": 24_000})],
            income_limit=KANSAS_CITY_VLI[1],
            payment_standard=KANSAS_CITY_SAFMR[1],
            expected_value=5_160,
            rent=1_200,
        )

    def test_scenario_15_kansas_city_family_with_an_eighteen_year_old_non_student(self):
        members = [
            make_member(born=(1990, 3), income={"wages": 36_000}),
            make_member(born=(1991, 6), relationship="spouse"),
            make_member(born=(2008, 9), relationship="child", student_full_time=False, income={"wages": 8_000}),
            make_member(born=(2014, 4), relationship="child"),
        ]
        self._assert_eligible(
            members,
            income_limit=KANSAS_CITY_VLI[4],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=864,
            rent=1_900,
        )

    def test_scenario_16_kansas_city_elderly_adult_with_medical_expenses(self):
        self._assert_eligible(
            [make_member(born=(1956, 3), income={"wages": 20_000})],
            income_limit=KANSAS_CITY_VLI[1],
            payment_standard=KANSAS_CITY_SAFMR[1],
            expected_value=6_900,
            rent=1_200,
            medical=200 * 12,
        )

    def test_scenario_17_kansas_city_parent_whose_childcare_costs_exceed_earnings(self):
        members = [
            make_member(born=(1996, 7), income={"wages": 5_000, "unemployment": 15_000}),
            make_member(born=(2021, 6), relationship="child"),
            make_member(born=(2023, 3), relationship="child"),
        ]
        self._assert_eligible(
            members,
            income_limit=KANSAS_CITY_VLI[3],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=9_708,
            rent=1_400,
            childcare=650 * 12,
        )

    def test_scenario_18_kansas_city_household_with_a_foster_child_who_has_earnings(self):
        members = [
            make_member(born=(1986, 2), income={"wages": 30_000}),
            make_member(born=(2007, 1), relationship="fosterChild", student_full_time=False, income={"wages": 5_000}),
            make_member(born=(2018, 4), relationship="child"),
        ]
        self._assert_eligible(
            members,
            income_limit=KANSAS_CITY_VLI[3],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=5_064,
            rent=1_900,
        )

    def test_scenario_19_kansas_city_adult_receiving_workers_compensation(self):
        self._assert_eligible(
            [make_member(born=(1981, 5), income={"wages": 22_000, "workersComp": 12_000})],
            income_limit=KANSAS_CITY_VLI[1],
            payment_standard=KANSAS_CITY_SAFMR[1],
            expected_value=5_640,
            rent=1_200,
        )

    def test_scenario_20_kansas_city_pregnant_sole_applicant(self):
        self._assert_eligible(
            [make_member(born=(1996, 7), income={"wages": 20_000}, pregnant=True)],
            income_limit=KANSAS_CITY_VLI[1],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=7_920,
            rent=0,
        )

    def test_scenario_21_kansas_city_eight_person_household_bedroom_cap(self):
        members = [
            make_member(born=(1986, 3), income={"wages": 40_000}),
            make_member(born=(1987, 6), relationship="spouse"),
            make_member(born=(1997, 2), relationship="sisterOrBrother"),
            make_member(born=(1999, 5), relationship="sisterOrBrother"),
            make_member(born=(2001, 8), relationship="sisterOrBrother"),
            make_member(born=(2012, 1), relationship="child"),
            make_member(born=(2015, 4), relationship="child"),
            make_member(born=(2018, 7), relationship="child"),
        ]
        self._assert_eligible(
            members,
            income_limit=KANSAS_CITY_VLI[8],
            payment_standard=KANSAS_CITY_SAFMR[4],
            expected_value=10_032,
            rent=2_200,
        )

    def test_scenario_22_kansas_city_four_generation_household(self):
        members = [
            make_member(born=(1988, 3), income={"wages": 34_000}),
            make_member(born=(1956, 5), relationship="grandParent"),
            make_member(born=(1966, 9), relationship="parent"),
            make_member(born=(2014, 4), relationship="child"),
            make_member(born=(2017, 6), relationship="child"),
        ]
        self._assert_eligible(
            members,
            income_limit=KANSAS_CITY_VLI[5],
            payment_standard=KANSAS_CITY_SAFMR[4],
            expected_value=11_688,
            rent=2_000,
        )

    def test_scenario_23_kansas_city_homeowner_paying_a_mortgage_and_no_rent(self):
        self._assert_eligible(
            [make_member(born=(1996, 7), income={"wages": 20_000})],
            income_limit=KANSAS_CITY_VLI[1],
            payment_standard=KANSAS_CITY_SAFMR[1],
            expected_value=6_240,
            rent=0,
            mortgage=700,
        )

    def test_scenario_24_kansas_city_household_of_three_in_a_single_generation(self):
        members = [
            make_member(born=(1990, 3), income={"wages": 24_000}),
            make_member(born=(1992, 5), relationship="roommate"),
            make_member(born=(1994, 8), relationship="roommate"),
        ]
        self._assert_eligible(
            members,
            income_limit=KANSAS_CITY_VLI[3],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=6_720,
            rent=1_500,
        )

    def test_scenario_25_kansas_city_head_with_an_elderly_domestic_partner(self):
        members = [
            make_member(born=(1986, 3), income={"wages": 24_000}),
            make_member(born=(1961, 4), relationship="domesticPartner"),
        ]
        self._assert_eligible(
            members,
            income_limit=KANSAS_CITY_VLI[2],
            payment_standard=KANSAS_CITY_SAFMR[1],
            expected_value=5_160,
            rent=1_200,
        )

    def test_scenario_26_kansas_city_seventeen_year_old_sole_head_with_wages(self):
        self._assert_eligible(
            [make_member(born=(2009, 9), income={"wages": 18_000})],
            income_limit=KANSAS_CITY_VLI[1],
            payment_standard=KANSAS_CITY_SAFMR[1],
            expected_value=6_840,
            rent=0,
        )

    def test_scenario_27_kansas_city_seventeen_year_old_sole_head_over_the_limit(self):
        self._assert_ineligible(
            [make_member(born=(2009, 9), income={"wages": 42_000})],
            income_limit=KANSAS_CITY_VLI[1],
        )

    def test_scenario_28_kansas_city_head_with_a_disabled_domestic_partner(self):
        members = [
            make_member(born=(1986, 3), income={"wages": 28_000}),
            make_member(born=(1981, 4), relationship="domesticPartner", disabled=True),
        ]
        self._assert_eligible(
            members,
            income_limit=KANSAS_CITY_VLI[2],
            payment_standard=KANSAS_CITY_SAFMR[1],
            expected_value=3_960,
            rent=1_200,
        )

    def test_scenario_29_kansas_city_foster_child_young_enough_to_be_a_dependent(self):
        members = [
            make_member(born=(1986, 2), income={"wages": 32_000}),
            make_member(born=(2016, 4), relationship="fosterChild"),
        ]
        self._assert_eligible(
            members,
            income_limit=KANSAS_CITY_VLI[2],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=4_320,
            rent=1_900,
        )

    def test_scenario_30_kansas_city_elderly_couple_both_head_relationship_members_qualifying(self):
        members = [
            make_member(born=(1961, 4), income={"wages": 26_000}),
            make_member(born=(1963, 6), relationship="spouse"),
        ]
        self._assert_eligible(
            members,
            income_limit=KANSAS_CITY_VLI[2],
            payment_standard=KANSAS_CITY_SAFMR[1],
            expected_value=4_560,
            rent=1_200,
        )

    def test_scenario_31_kansas_city_minor_full_time_students_earnings(self):
        members = [
            make_member(born=(1988, 3), income={"wages": 40_000}),
            make_member(born=(2010, 1), relationship="child", student_full_time=True, income={"wages": 10_000}),
        ]
        self._assert_eligible(
            members,
            income_limit=KANSAS_CITY_VLI[2],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=2_064,
            rent=1_500,
        )

    def test_scenario_32_childcare_cap_set_by_an_excluded_minors_earnings(self):
        members = [
            make_member(born=(1991, 3), income={"wages": 30_000}),
            make_member(born=(2010, 6), relationship="child", income={"wages": 6_000}),
            make_member(born=(2018, 4), relationship="child"),
        ]
        self._assert_eligible(
            members,
            income_limit=KANSAS_CITY_VLI[3],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=7_608,
            rent=1_900,
            childcare=8_000,
        )

    def test_scenario_33_childcare_deduction_uncapped_and_ten_percent_prong_binds(self):
        members = [
            make_member(born=(1996, 7), income={"unemployment": 15_000}),
            make_member(born=(2010, 6), relationship="child", income={"wages": 6_000}),
            make_member(born=(2021, 6), relationship="child"),
        ]
        self._assert_eligible(
            members,
            income_limit=KANSAS_CITY_VLI[3],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=12_420,
            rent=1_400,
            childcare=10_000,
        )

    def test_scenario_34_elderly_head_with_medical_expenses_and_a_working_minor(self):
        members = [
            make_member(born=(1956, 3), income={"wages": 24_300}),
            make_member(born=(2010, 6), relationship="child", income={"wages": 6_000}),
        ]
        self._assert_eligible(
            members,
            income_limit=KANSAS_CITY_VLI[2],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=7_752,
            rent=1_500,
            medical=300 * 12,
        )

    def test_scenario_35_two_earner_household_childcare_cap_is_the_lower_wage(self):
        members = [
            make_member(born=(1988, 3), income={"wages": 30_000}),
            make_member(born=(1990, 5), relationship="spouse", income={"wages": 12_000}),
            make_member(born=(2020, 4), relationship="child"),
            make_member(born=(2023, 8), relationship="child"),
        ]
        self._assert_eligible(
            members,
            income_limit=KANSAS_CITY_VLI[4],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=5_208,
            rent=1_900,
            childcare=18_000,
        )

    def test_scenario_36_deductions_zero_adjusted_income_minimum_rent_binds(self):
        members = [
            make_member(born=(1991, 3), income={"wages": 3_600}),
            make_member(born=(2010, 6), relationship="child", income={"wages": 14_000}),
            make_member(born=(2021, 6), relationship="child"),
        ]
        self._assert_eligible(
            members,
            income_limit=KANSAS_CITY_VLI[3],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=13_320,
            rent=1_500,
            childcare=3_000,
        )

    def test_scenario_37_childcare_cap_set_by_a_students_480_of_included_earnings(self):
        members = [
            make_member(born=(1986, 3), income={"wages": 28_000}),
            make_member(born=(2007, 5), relationship="child", student_full_time=True, income={"wages": 5_000}),
            make_member(born=(2021, 6), relationship="child"),
        ]
        self._assert_eligible(
            members,
            income_limit=KANSAS_CITY_VLI[3],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=5_808,
            rent=1_800,
            childcare=3_000,
        )

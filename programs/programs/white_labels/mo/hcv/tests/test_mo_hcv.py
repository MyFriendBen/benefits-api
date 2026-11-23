"""
Unit tests for the MO Housing Choice Voucher calculator.

`CustomCalculatorTestCase` (`programs/programs/testing_fixtures/custom_calculator.py`)
is the shared harness for a plain custom calculator: real `Screen`/`HouseholdMember`/
`IncomeStream`/`Expense` rows, not a hand-rolled `Mock` screen. `mo/rca`
(`programs/programs/white_labels/mo/rca/tests/test_mo_rca.py`) is the template this
file follows.

Ages are passed as the whole-year figure spec.md states for each person — e.g. "born
March 1990 (age 36)" becomes `age=36` — rather than a literal birth month, because
`add_member` derives `birth_year_month` from `age` against the pinned reference date
(`reference_date = date(2026, 9, 28)`, via `stores_age = False` and the harness's
`get_reference_date` patch) using the same round-trip arithmetic `calc_age()` reads
back, so the two agree exactly for every scenario here — none needs sub-year
precision. `TestMoHcvAgeDerivation` is the one class that manipulates
`birth_year_month` directly, since it specifically tests what happens when the raw
`age` column disagrees with it or is the only thing set.

Every scenario in spec.md's Test Scenarios section has a test in
`TestMoHcvSpecScenarios`, named for its scenario number, asserting both eligibility and
the exact benefit value — unchanged by this rewrite.

Scenario 11 (eligible immigration status) is not a calculator-level test: the program
spec is explicit that no `MoHcv` branch reads legal status — it is evaluated entirely
through the `legal_status_required` config field and the results-page citizenship
filter. `TestMoHcvSpecScenario11` documents that and asserts the one thing the
calculator *can* promise: its household is otherwise identical to Scenario 1's and
computes the same eligibility and value.

`TestMoHcvNeverRaises` also covers a household with no head of household: a screen the
frontend cannot submit, since `relationshipToHH` is required, but one the API can
still produce. `Screen.get_head()` raises in that case rather than returning `None`
(`screener/models.py`); `_generation_counts()` calls it unguarded, and
`household_value()`'s broad `except Exception` is what keeps that from crashing the
whole eligibility response.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import Mock, patch

from django.test import TestCase

from programs.framework.base import ProgramCalculator
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from programs.programs.white_labels.mo.hcv.calculator import MoHcv
from programs.util import Dependencies
from screener.models import CurrentBenefit

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


class MoHcvTestCase(CustomCalculatorTestCase):
    calculator_class = MoHcv
    program_code = "mo_hcv"
    white_label_code = "mo"
    state_code = "MO"
    fpl_year = "2026"

    # MoHcv reads age only through `calc_age()` (via its own `_age()` helper), never
    # the raw `age` column, so members are saved with a null `age` here — the state
    # every member will be in once the column is dropped.
    stores_age = False

    # The spec pins every scenario to this date; `Screen.get_reference_date()` would
    # otherwise drift with the ambient clock. Scenarios 10, 14, 26 and 27 are exact-
    # month boundary cases that hold only for the twelve months from it (spec.md).
    reference_date = date(2026, 9, 28)

    # MoHcv reads `self.program.year.period` for the HUD year, and the already-holds-
    # a-voucher gate needs a real `Program` row carrying `base_program`.
    needs_program_row = True

    default_zipcode = "64130"
    default_county = "Jackson County"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Matches the real mo_hcv_initial_config.json, which ships
        # `"base_program": "section_8"` — what `give_section_8` and
        # `Screen.has_base_benefit` key on.
        cls.program.base_program = "section_8"
        cls.program.save()

    def give_section_8(self, screen):
        """Record the household as already holding a voucher — the real
        `CurrentBenefit` row `Screen.has_base_benefit("section_8")` reads."""
        CurrentBenefit.objects.create(screen=screen, program=self.program)


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


class TestMoHcvAgeDerivation(MoHcvTestCase):
    """MO reads ages through `calc_age()`, never the raw `age` field, matching
    `KsHcv` and departing from `IlHcv`/`TxHcv`/`WaHcv`."""

    def test_age_comes_from_birth_year_month_not_the_raw_field(self):
        # Born March 2016 — 10 as of the reference date — but the stale raw field
        # is then set to 40. A calculator reading `age` finds an adult and counts
        # no dependent.
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", age=38)
        child = self.add_member(screen, "child", age=None, birth_year_month=date(2016, 3, 1), stored_age=True)
        child.age = 40
        child.save(update_fields=["age"])

        calc = self.make_calculator(screen)
        self.assertTrue(calc._is_minor(child))
        self.assertEqual(calc._count_dependents(), 1)

    def test_missing_birth_date_falls_back_to_the_raw_field(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", age=38)
        member = self.add_member(screen, "child", age=12, birth_year_month=None, stored_age=True)

        calc = self.make_calculator(screen)
        self.assertTrue(calc._is_minor(member))

    def test_unknown_age_is_treated_as_an_adult(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", age=38)
        member = self.add_member(screen, "child", age=None, birth_year_month=None, stored_age=True)
        self.add_income(member, 12_000, income_type="wages", frequency="yearly")

        calc = self.make_calculator(screen)
        self.assertFalse(calc._is_minor(member))
        self.assertEqual(calc._annual_income(), 12_000)


class TestMoHcvGenerationCountsAndBedrooms(MoHcvTestCase):
    def test_single_person_is_one_bedroom(self):
        screen = self.make_screen(household_size=1)
        self.add_member(screen, "headOfHousehold", age=36)

        self.assertEqual(self.make_calculator(screen)._estimate_bedrooms(), 1)

    def test_head_and_spouse_share_one_generation_one_bedroom(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", age=36)
        self.add_member(screen, "spouse", age=35)

        self.assertEqual(self.make_calculator(screen)._estimate_bedrooms(), 1)

    def test_head_and_one_child_are_two_generations_two_bedrooms(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", age=38)
        self.add_member(screen, "child", age=16)

        self.assertEqual(self.make_calculator(screen)._estimate_bedrooms(), 2)

    def test_grandparent_maps_to_generation_plus_two(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", age=38)
        self.add_member(screen, "grandParent", age=70)

        counts = self.make_calculator(screen)._generation_counts()
        self.assertEqual(counts.get(2), 1)

    def test_parent_maps_to_generation_plus_one(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", age=38)
        self.add_member(screen, "parent", age=60)

        counts = self.make_calculator(screen)._generation_counts()
        self.assertEqual(counts.get(1), 1)

    def test_grandchild_maps_to_generation_minus_two(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", age=66)
        self.add_member(screen, "grandChild", age=8)

        counts = self.make_calculator(screen)._generation_counts()
        self.assertEqual(counts.get(-2), 1)

    def test_roommate_falls_to_generation_zero(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", age=36)
        self.add_member(screen, "roommate", age=34)

        calc = self.make_calculator(screen)
        self.assertEqual(calc._generation_counts(), {0: 2})
        self.assertEqual(calc._estimate_bedrooms(), 1)

    def test_related_other_and_boyfriend_or_girlfriend_fall_to_generation_zero(self):
        screen = self.make_screen(household_size=3)
        self.add_member(screen, "headOfHousehold", age=36)
        self.add_member(screen, "relatedOther", age=34)
        self.add_member(screen, "boyfriendOrGirlfriend", age=35)

        self.assertEqual(self.make_calculator(screen)._generation_counts(), {0: 3})

    def test_null_or_unrecognised_relationship_falls_to_generation_zero(self):
        """Not reached by any screen the frontend can submit — the serializer
        requires `relationshipToHH` — but `HouseholdMember.relationship` is
        nullable, so the API can still produce one. The program spec records this
        as a branch no Test Scenario reaches; it is pinned directly here instead."""
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", age=36)
        self.add_member(screen, relationship=None, age=34)
        self.assertEqual(self.make_calculator(screen)._generation_counts(), {0: 2})

        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", age=36)
        self.add_member(screen, relationship="somethingUnmapped", age=34)
        self.assertEqual(self.make_calculator(screen)._generation_counts(), {0: 2})

    def test_bedroom_count_is_capped_at_four(self):
        # Five generations occupied at one member each sums to 5 bedrooms uncapped.
        screen = self.make_screen(household_size=5)
        self.add_member(screen, "grandParent", age=66)
        self.add_member(screen, "parent", age=46)
        self.add_member(screen, "headOfHousehold", age=26)
        self.add_member(screen, "child", age=8)
        self.add_member(screen, "grandChild", age=4)

        self.assertEqual(self.make_calculator(screen)._estimate_bedrooms(), 4)

    def test_pregnant_sole_applicant_is_two_bedrooms(self):
        screen = self.make_screen(household_size=1)
        self.add_member(screen, "headOfHousehold", age=27, pregnant=True)

        self.assertEqual(self.make_calculator(screen)._estimate_bedrooms(), 2)

    def test_non_pregnant_sole_applicant_stays_one_bedroom(self):
        screen = self.make_screen(household_size=1)
        self.add_member(screen, "headOfHousehold", age=27)

        self.assertEqual(self.make_calculator(screen)._estimate_bedrooms(), 1)

    def test_pregnancy_in_a_larger_household_triggers_no_adjustment(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", age=36, pregnant=True)
        self.add_member(screen, "spouse", age=36)

        self.assertEqual(self.make_calculator(screen)._estimate_bedrooms(), 1)

    def test_the_income_limit_still_uses_the_real_household_size_for_a_pregnant_applicant(self):
        screen = self.make_screen(household_size=1)
        self.add_member(screen, "headOfHousehold", age=27, pregnant=True)

        with self.hud_ami(KANSAS_CITY_VLI[1], payment_standard=1_160):
            self.calculate(screen)

        # The real household_size (1), not the notional 2, is what gets compared.
        self.assertEqual(screen.household_size, 1)


class TestMoHcvAnnualIncome(MoHcvTestCase):
    def test_minor_earned_income_is_excluded(self):
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", age=38)
        self.add_income(head, 21_600, income_type="wages", frequency="yearly")
        child = self.add_member(screen, "child", age=13)
        self.add_income(child, 2_400, income_type="wages", frequency="yearly")

        self.assertEqual(self.make_calculator(screen)._annual_income(), 21_600)

    def test_minor_unearned_income_still_counts(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", age=38)
        child = self.add_member(screen, "child", age=13)
        self.add_income(child, 1_200, income_type="childSupport", frequency="yearly")

        self.assertEqual(self.make_calculator(screen)._annual_income(), 1_200)

    def test_a_minor_head_of_household_contributes_in_full(self):
        screen = self.make_screen(household_size=1)
        head = self.add_member(screen, "headOfHousehold", age=17)
        self.add_income(head, 9_000, income_type="wages", frequency="yearly")

        self.assertEqual(self.make_calculator(screen)._annual_income(), 9_000)

    def test_a_minor_spouse_contributes_in_full(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", age=38)
        spouse = self.add_member(screen, "spouse", age=17)
        self.add_income(spouse, 9_000, income_type="wages", frequency="yearly")

        self.assertEqual(self.make_calculator(screen)._annual_income(), 9_000)

    def test_a_minor_domestic_partner_contributes_in_full(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", age=38)
        partner = self.add_member(screen, "domesticPartner", age=17)
        self.add_income(partner, 9_000, income_type="wages", frequency="yearly")

        self.assertEqual(self.make_calculator(screen)._annual_income(), 9_000)

    def test_dependent_full_time_student_earned_income_is_capped_at_480(self):
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", age=41)
        self.add_income(head, 12_000, income_type="wages", frequency="yearly")
        child = self.add_member(screen, "child", age=20, student_full_time=True)
        self.add_income(child, 6_000, income_type="wages", frequency="yearly")

        self.assertEqual(self.make_calculator(screen)._annual_income(), 12_480)

    def test_minor_and_full_time_student_is_excluded_in_full_not_capped(self):
        """§ 5.609(b)(3) must run before (b)(14): a member who is both under 18 and
        a full-time student is excluded in full, not capped at $480."""
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", age=38)
        self.add_income(head, 40_000, income_type="wages", frequency="yearly")
        child = self.add_member(screen, "child", age=16, student_full_time=True)
        self.add_income(child, 10_000, income_type="wages", frequency="yearly")

        self.assertEqual(self.make_calculator(screen)._annual_income(), 40_000)

    def test_workers_compensation_is_excluded_for_any_member(self):
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", age=38)
        self.add_income(head, 10_800, income_type="wages", frequency="yearly")
        self.add_income(head, 2_400, income_type="workersComp", frequency="yearly")
        spouse = self.add_member(screen, "spouse", age=36)
        self.add_income(spouse, 5_000, income_type="workersComp", frequency="yearly")

        self.assertEqual(self.make_calculator(screen)._annual_income(), 10_800)

    def test_foster_member_income_is_excluded_entirely(self):
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", age=40)
        self.add_income(head, 30_000, income_type="wages", frequency="yearly")
        foster = self.add_member(screen, "fosterChild", age=19)
        self.add_income(foster, 5_000, income_type="wages", frequency="yearly")

        self.assertEqual(self.make_calculator(screen)._annual_income(), 30_000)

    def test_adult_non_student_non_disabled_is_not_excluded(self):
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", age=36)
        self.add_income(head, 36_000, income_type="wages", frequency="yearly")
        child = self.add_member(screen, "child", age=18)
        self.add_income(child, 8_000, income_type="wages", frequency="yearly")

        self.assertEqual(self.make_calculator(screen)._annual_income(), 44_000)


class TestMoHcvDependents(MoHcvTestCase):
    def test_minor_children_count(self):
        screen = self.make_screen(household_size=3)
        self.add_member(screen, "headOfHousehold", age=38)
        self.add_member(screen, "child", age=10)
        self.add_member(screen, "child", age=6)

        self.assertEqual(self.make_calculator(screen)._count_dependents(), 2)

    def test_head_spouse_and_domestic_partner_never_count(self):
        screen = self.make_screen(household_size=3)
        self.add_member(screen, "headOfHousehold", age=17)
        self.add_member(screen, "spouse", age=17)
        self.add_member(screen, "domesticPartner", age=17)

        self.assertEqual(self.make_calculator(screen)._count_dependents(), 0)

    def test_adult_full_time_student_counts(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", age=41)
        self.add_member(screen, "child", age=20, student_full_time=True)

        self.assertEqual(self.make_calculator(screen)._count_dependents(), 1)

    def test_adult_with_a_disability_counts(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", age=41)
        self.add_member(screen, "sisterOrBrother", age=31, disabled=True)

        self.assertEqual(self.make_calculator(screen)._count_dependents(), 1)

    def test_adult_who_is_neither_student_nor_disabled_does_not_count(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", age=68)
        self.add_member(screen, "child", age=36)

        self.assertEqual(self.make_calculator(screen)._count_dependents(), 0)

    def test_foster_child_never_counts_even_when_young(self):
        """MO excludes `fosterChild` from the dependent definition (§ 5.603),
        departing from `IlHcv`, `KsHcv` and `WaHcv`, which retain them."""
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", age=40)
        self.add_member(screen, "fosterChild", age=10)

        self.assertEqual(self.make_calculator(screen)._count_dependents(), 0)

    def test_foster_child_does_not_count_even_if_disabled_or_a_student(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", age=40)
        self.add_member(screen, "fosterChild", age=20, student_full_time=True)

        self.assertEqual(self.make_calculator(screen)._count_dependents(), 0)


class TestMoHcvElderlyOrDisabledFamily(MoHcvTestCase):
    def test_sole_member_62_qualifies(self):
        screen = self.make_screen(household_size=1)
        self.add_member(screen, "headOfHousehold", age=62)

        self.assertTrue(self.make_calculator(screen)._is_elderly_or_disabled_family())

    def test_head_61_does_not(self):
        screen = self.make_screen(household_size=1)
        self.add_member(screen, "headOfHousehold", age=61)

        self.assertFalse(self.make_calculator(screen)._is_elderly_or_disabled_family())

    def test_spouse_62_qualifies(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", age=36)
        self.add_member(screen, "spouse", age=62)

        self.assertTrue(self.make_calculator(screen)._is_elderly_or_disabled_family())

    def test_domestic_partner_62_qualifies(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", age=36)
        self.add_member(screen, "domesticPartner", age=62)

        self.assertTrue(self.make_calculator(screen)._is_elderly_or_disabled_family())

    def test_head_with_a_plain_disability_qualifies(self):
        screen = self.make_screen(household_size=1)
        self.add_member(screen, "headOfHousehold", age=36, disabled=True)

        self.assertTrue(self.make_calculator(screen)._is_elderly_or_disabled_family())

    def test_head_who_is_visually_impaired_qualifies(self):
        screen = self.make_screen(household_size=1)
        self.add_member(screen, "headOfHousehold", age=36, visually_impaired=True)

        self.assertTrue(self.make_calculator(screen)._is_elderly_or_disabled_family())

    def test_head_with_a_long_term_disability_qualifies(self):
        screen = self.make_screen(household_size=1)
        self.add_member(screen, "headOfHousehold", age=36, long_term_disability=True)

        self.assertTrue(self.make_calculator(screen)._is_elderly_or_disabled_family())

    def test_elderly_non_head_relationship_member_does_not_qualify_the_family(self):
        """Scenario 22's rule from outside: a 70-year-old `grandParent` is not head,
        co-head or spouse, so no deduction is taken."""
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", age=36)
        self.add_member(screen, "grandParent", age=70)

        self.assertFalse(self.make_calculator(screen)._is_elderly_or_disabled_family())

    def test_disabled_domestic_partner_qualifies_through_disability(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", age=40)
        self.add_member(screen, "domesticPartner", age=45, disabled=True)

        self.assertTrue(self.make_calculator(screen)._is_elderly_or_disabled_family())

    def test_unknown_head_age_without_disability_does_not_qualify(self):
        screen = self.make_screen(household_size=1)
        self.add_member(screen, "headOfHousehold", age=None, birth_year_month=None)

        self.assertFalse(self.make_calculator(screen)._is_elderly_or_disabled_family())


class TestMoHcvMedicalDeduction(MoHcvTestCase):
    def test_no_deduction_when_not_elderly_or_disabled(self):
        screen = self.make_screen(household_size=1)
        head = self.add_member(screen, "headOfHousehold", age=36)
        self.add_expense(head, 200 * 12, expense_type="medical", frequency="yearly")

        self.assertEqual(self.make_calculator(screen)._adjusted_income(20_000), Decimal(20_000))

    def test_deduction_is_medical_minus_three_percent_floor(self):
        screen = self.make_screen(household_size=1)
        head = self.add_member(screen, "headOfHousehold", age=70)
        self.add_income(head, 20_000, income_type="wages", frequency="yearly")
        self.add_expense(head, 200 * 12, expense_type="medical", frequency="yearly")

        # medical $2,400, floor 3% * $20,000 = $600, deduction = $1,800.
        self.assertEqual(self.make_calculator(screen)._medical_deduction(Decimal(20_000)), Decimal(1_800))

    def test_deduction_floors_at_zero_when_expenses_are_below_the_floor(self):
        screen = self.make_screen(household_size=1)
        head = self.add_member(screen, "headOfHousehold", age=70)
        self.add_expense(head, 100, expense_type="medical", frequency="yearly")

        self.assertEqual(self.make_calculator(screen)._medical_deduction(Decimal(20_000)), Decimal(0))


class TestMoHcvChildcareDeduction(MoHcvTestCase):
    def test_uncapped_when_no_member_has_included_earned_income(self):
        screen = self.make_screen(household_size=1)
        head = self.add_member(screen, "headOfHousehold", age=36)
        self.add_income(head, 15_000, income_type="unemployment", frequency="yearly")
        self.add_expense(head, 10_000, expense_type="childCare", frequency="yearly")

        self.assertEqual(self.make_calculator(screen)._childcare_deduction(), Decimal(10_000))

    def test_capped_at_the_single_earners_included_income(self):
        screen = self.make_screen(household_size=1)
        head = self.add_member(screen, "headOfHousehold", age=36)
        self.add_income(head, 5_000, income_type="wages", frequency="yearly")
        self.add_income(head, 15_000, income_type="unemployment", frequency="yearly")
        self.add_expense(head, 7_800, expense_type="childCare", frequency="yearly")

        self.assertEqual(self.make_calculator(screen)._childcare_deduction(), Decimal(5_000))

    def test_capped_at_the_lowest_paid_of_two_earners_not_the_sum(self):
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", age=38)
        self.add_income(head, 30_000, income_type="wages", frequency="yearly")
        spouse = self.add_member(screen, "spouse", age=36)
        self.add_income(spouse, 12_000, income_type="wages", frequency="yearly")
        self.add_expense(head, 18_000, expense_type="childCare", frequency="yearly")

        self.assertEqual(self.make_calculator(screen)._childcare_deduction(), Decimal(12_000))

    def test_excluded_minor_earner_is_not_in_the_earner_list(self):
        """§ 5.609(b)(3) zeroes the minor's earnings before the earner list is
        built, so the cap is the head's own wages, not the minor's."""
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", age=35)
        self.add_income(head, 30_000, income_type="wages", frequency="yearly")
        child = self.add_member(screen, "child", age=16)
        self.add_income(child, 6_000, income_type="wages", frequency="yearly")
        self.add_expense(head, 8_000, expense_type="childCare", frequency="yearly")

        self.assertEqual(self.make_calculator(screen)._childcare_deduction(), Decimal(8_000))

    def test_foster_child_earner_is_not_in_the_earner_list(self):
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", age=40)
        self.add_income(head, 30_000, income_type="wages", frequency="yearly")
        foster = self.add_member(screen, "fosterChild", age=19)
        self.add_income(foster, 20_000, income_type="wages", frequency="yearly")
        self.add_expense(head, 25_000, expense_type="childCare", frequency="yearly")

        self.assertEqual(self.make_calculator(screen)._childcare_deduction(), Decimal(25_000))

    def test_partly_excluded_student_earner_sets_the_cap_at_480(self):
        """§ 5.609(b)(14) leaves a dependent full-time student $480 of included
        earned income — enough to make them the lowest-paid earner."""
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", age=40)
        self.add_income(head, 28_000, income_type="wages", frequency="yearly")
        child = self.add_member(screen, "child", age=19, student_full_time=True)
        self.add_income(child, 5_000, income_type="wages", frequency="yearly")
        self.add_expense(head, 3_000, expense_type="childCare", frequency="yearly")

        self.assertEqual(self.make_calculator(screen)._childcare_deduction(), Decimal(480))

    def test_no_childcare_expense_is_zero(self):
        screen = self.make_screen(household_size=1)
        head = self.add_member(screen, "headOfHousehold", age=36)
        self.add_income(head, 20_000, income_type="wages", frequency="yearly")

        self.assertEqual(self.make_calculator(screen)._childcare_deduction(), Decimal(0))


class TestMoHcvTotalTenantPayment(MoHcvTestCase):
    def _ttp(self, screen, annual_income, annual_adjusted=None):
        calc = self.make_calculator(screen)
        adjusted = Decimal(str(annual_income if annual_adjusted is None else annual_adjusted))
        return calc._total_tenant_payment(annual_income, adjusted)

    def _default_screen(self):
        screen = self.make_screen(household_size=1)
        self.add_member(screen, "headOfHousehold", age=36)
        return screen

    def test_thirty_percent_prong_governs(self):
        self.assertEqual(self._ttp(self._default_screen(), 35_040), 876)

    def test_ten_percent_prong_governs_when_deductions_dominate(self):
        self.assertEqual(self._ttp(self._default_screen(), 15_000, annual_adjusted=4_040), 125)

    def test_minimum_rent_prong_governs_when_both_percentages_fall_below_it(self):
        self.assertEqual(self._ttp(self._default_screen(), 3_600, annual_adjusted=0), 50)

    def test_rounds_half_up_not_half_even(self):
        # 30% of $4,645.00/mo = $1,393.50 — half-up gives $1,394, banker's $1,394
        # agrees here, so use an odd-cents case: 30% of monthly $1,712.42 = $513.73.
        self.assertEqual(self._ttp(self._default_screen(), 24_300, annual_adjusted=20_549), 514)

    def test_zero_income_gives_the_minimum_rent(self):
        self.assertEqual(self._ttp(self._default_screen(), 0), 50)

    def test_deductions_never_drive_adjusted_income_negative(self):
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", age=68)
        self.add_income(head, 200, income_type="sSRetirement", frequency="yearly")
        self.add_member(screen, "child", age=10)

        self.assertEqual(self.make_calculator(screen)._adjusted_income(200), Decimal(0))


class TestMoHcvGrossRentProxy(MoHcvTestCase):
    def _default_screen(self):
        screen = self.make_screen(household_size=1)
        head = self.add_member(screen, "headOfHousehold", age=36)
        return screen, head

    def test_reported_rent_is_used_when_present(self):
        screen, head = self._default_screen()
        self.add_expense(head, 900, expense_type="rent", frequency="monthly")

        self.assertEqual(self.make_calculator(screen)._gross_rent_proxy(1_160), 900)

    def test_falls_back_to_the_payment_standard_with_no_rent(self):
        screen, _head = self._default_screen()

        self.assertEqual(self.make_calculator(screen)._gross_rent_proxy(1_160), 1_160)

    def test_mortgage_is_not_a_rent_proxy(self):
        screen, head = self._default_screen()
        self.add_expense(head, 700, expense_type="mortgage", frequency="monthly")

        self.assertEqual(self.make_calculator(screen)._gross_rent_proxy(1_020), 1_020)


class TestMoHcvHouseholdEligible(MoHcvTestCase):
    def _screen_with_wages(self, wages, household_size=1):
        screen = self.make_screen(household_size=household_size)
        head = self.add_member(screen, "headOfHousehold", age=38)
        self.add_income(head, wages, income_type="wages", frequency="yearly")
        return screen

    def test_household_size_trivially_passes(self):
        screen = self._screen_with_wages(12_000)
        with self.hud_ami(KANSAS_CITY_VLI[1], payment_standard=1_020):
            e = self.calculate(screen)
        self.assertTrue(e.eligible)

    def test_already_holding_section_8_is_ineligible(self):
        screen = self._screen_with_wages(12_000)
        self.give_section_8(screen)
        with self.hud_ami(KANSAS_CITY_VLI[1], payment_standard=1_020):
            e = self.calculate(screen)
        self.assertFalse(e.eligible)

    def test_not_holding_section_8_proceeds_normally(self):
        screen = self._screen_with_wages(12_000)
        with self.hud_ami(KANSAS_CITY_VLI[1], payment_standard=1_020):
            e = self.calculate(screen)
        self.assertTrue(e.eligible)

    def test_checks_has_base_benefit_with_section_8(self):
        screen = self._screen_with_wages(12_000)

        with patch.object(screen, "has_base_benefit", wraps=screen.has_base_benefit) as spy:
            with self.hud_ami(KANSAS_CITY_VLI[1], payment_standard=1_020):
                self.calculate(screen)

        spy.assert_called_with("section_8")

    def test_income_at_the_limit_is_eligible(self):
        screen = self._screen_with_wages(39_700)
        with self.hud_ami(KANSAS_CITY_VLI[1], payment_standard=1_020):
            self.assertTrue(self.calculate(screen).eligible)

    def test_one_dollar_over_the_limit_is_not_eligible(self):
        screen = self._screen_with_wages(39_701)
        with self.hud_ami(KANSAS_CITY_VLI[1], payment_standard=1_020):
            self.assertFalse(self.calculate(screen).eligible)

    def test_the_limit_is_looked_up_at_fifty_percent_for_the_screen_and_year(self):
        screen = self._screen_with_wages(12_000)
        with self.hud_ami(KANSAS_CITY_VLI[1], payment_standard=1_020) as hud:
            self.calculate(screen)
        self.assertEqual(hud.get_screen_il_ami.call_args.args[1], "50%")
        self.assertEqual(hud.get_screen_il_ami.call_args.args[2], "2026")

    def test_null_household_size_passes_the_gate_inclusively(self):
        screen = self.make_screen(household_size=None)
        head = self.add_member(screen, "headOfHousehold", age=38)
        self.add_income(head, 999_999, income_type="wages", frequency="yearly")
        with self.hud_ami(KANSAS_CITY_VLI[1], payment_standard=1_020):
            self.assertTrue(self.calculate(screen).eligible)

    def test_no_asset_gate_is_applied(self):
        screen = self._screen_with_wages(12_000)
        screen.household_assets = 500_000
        screen.save(update_fields=["household_assets"])
        with self.hud_ami(KANSAS_CITY_VLI[1], payment_standard=1_020):
            self.assertTrue(self.calculate(screen).eligible)


class TestMoHcvNeverRaises(MoHcvTestCase):
    def _screen(self):
        screen = self.make_screen(household_size=1)
        head = self.add_member(screen, "headOfHousehold", age=36)
        self.add_income(head, 12_000, income_type="wages", frequency="yearly")
        return screen

    def test_income_lookup_hud_error(self):
        screen = self._screen()
        with self.hud_ami(unavailable=True, payment_standard=1_020):
            e = self.calculate(screen)
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)

    def test_income_lookup_unexpected_exception(self):
        screen = self._screen()
        with patch.multiple(
            "programs.programs.white_labels.mo.hcv.calculator.hud_client",
            get_screen_il_ami=Mock(side_effect=ValueError("unexpected boom")),
            get_screen_payment_standard=Mock(return_value=1_020),
        ):
            e = self.calculate(screen)
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)

    def test_payment_standard_hud_error_degrades_to_zero_unfloored(self):
        screen = self._screen()
        with self.hud_ami(KANSAS_CITY_VLI[1], payment_standard_unavailable=True):
            e = self.calculate(screen)
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 0)

    def test_payment_standard_unexpected_exception_degrades_to_zero(self):
        screen = self._screen()
        with patch.multiple(
            "programs.programs.white_labels.mo.hcv.calculator.hud_client",
            get_screen_il_ami=Mock(return_value=KANSAS_CITY_VLI[1]),
            get_screen_payment_standard=Mock(side_effect=KeyError("unexpected")),
        ):
            e = self.calculate(screen)
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 0)

    def test_unconfigured_program_year_is_not_eligible(self):
        screen = self._screen()

        # A standalone `Mock(year=None)` rather than `self.program`, so this test
        # doesn't mutate the class's shared `Program` row out from under the rest
        # of the suite.
        calc = MoHcv(screen, Mock(year=None), {}, Dependencies(()))
        e = calc.calc()

        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)

    def test_a_household_with_no_head_raises_from_estimate_bedrooms(self):
        """`_generation_counts` calls `Screen.get_head()` unguarded, which raises
        when the household has no `headOfHousehold` member (`Screen.get_head`,
        screener/models.py) rather than returning `None`. Not reachable from a
        screen the frontend can submit — `relationshipToHH` always includes
        exactly one head — but the API can still produce one, and this pins what
        actually happens rather than the `None` a mocked `get_head` used to
        pretend was possible."""
        screen = self.make_screen(household_size=1)
        self.add_member(screen, "child", age=10)

        with self.assertRaises(Exception):
            self.make_calculator(screen)._estimate_bedrooms()

    def test_a_household_with_no_head_degrades_to_zero_rather_than_crashing(self):
        """`household_value()`'s broad `except Exception` is what keeps the
        `Screen.get_head()` raise above from crashing the whole eligibility
        response for an otherwise well-formed screen."""
        screen = self.make_screen(household_size=1)
        self.add_member(screen, "child", age=10)

        with self.hud_ami(KANSAS_CITY_VLI[1], payment_standard=1_020):
            e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 0)


class TestMoHcvSpecScenarios(MoHcvTestCase):
    """One test per Test Scenario in spec.md, asserting eligibility and value."""

    def _assert_eligible(self, screen, income_limit, payment_standard, expected_value):
        with self.hud_ami(income_limit, payment_standard=payment_standard):
            e = self.calculate(screen)
        self.assertTrue(e.eligible, "expected eligible")
        self.assertEqual(e.value, expected_value)

    def _assert_ineligible(self, screen, income_limit):
        with self.hud_ami(income_limit):
            e = self.calculate(screen)
        self.assertFalse(e.eligible)

    def _kc_family_of_four(self, head_income, rent=1_900):
        """Scenarios 1, 2, 3, 5, 9 and 11's household."""
        screen = self.make_screen(household_size=4)
        head = self.add_member(screen, "headOfHousehold", age=36)
        self.add_income(head, head_income, income_type="wages", frequency="yearly")
        self.add_member(screen, "spouse", age=35)
        self.add_member(screen, "child", age=12)
        self.add_member(screen, "child", age=8)
        self.add_expense(head, rent, expense_type="rent", frequency="monthly")
        return screen

    def test_scenario_1_kansas_city_family_well_within_the_income_limit(self):
        screen = self._kc_family_of_four(36_000)
        self._assert_eligible(
            screen,
            income_limit=KANSAS_CITY_VLI[4],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=3_408,
        )

    def test_scenario_2_kansas_city_family_exactly_at_the_income_limit_floors_at_one_dollar(self):
        screen = self._kc_family_of_four(56_700)
        self._assert_eligible(
            screen,
            income_limit=KANSAS_CITY_VLI[4],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=1,
        )

    def test_scenario_3_kansas_city_family_one_dollar_over_the_income_limit(self):
        screen = self._kc_family_of_four(56_701)
        self._assert_ineligible(screen, income_limit=KANSAS_CITY_VLI[4])

    def test_scenario_4_st_louis_income_under_st_louis_limit_but_over_springfields(self):
        screen = self.make_screen(household_size=5, county="St. Louis City", zipcode="63118")
        head = self.add_member(screen, "headOfHousehold", age=38)
        self.add_income(head, 50_000, income_type="wages", frequency="yearly")
        self.add_member(screen, "spouse", age=37)
        self.add_member(screen, "child", age=13)
        self.add_member(screen, "child", age=10)
        self.add_member(screen, "child", age=7)
        self.add_expense(head, 1_900, expense_type="rent", frequency="monthly")

        self._assert_eligible(
            screen,
            income_limit=ST_LOUIS_VLI[5],
            payment_standard=ST_LOUIS_SAFMR[3],
            expected_value=3_312,
        )

    def test_scenario_5_kansas_city_family_already_holding_a_voucher(self):
        screen = self._kc_family_of_four(36_000)
        self.give_section_8(screen)
        self._assert_ineligible(screen, income_limit=KANSAS_CITY_VLI[4])

    def test_scenario_6_single_adult_in_springfield(self):
        screen = self.make_screen(household_size=1, county="Greene County", zipcode="65806")
        head = self.add_member(screen, "headOfHousehold", age=30)
        self.add_income(head, 18_000, income_type="wages", frequency="yearly")
        self.add_expense(head, 900, expense_type="rent", frequency="monthly")

        self._assert_eligible(
            screen,
            income_limit=SPRINGFIELD_VLI[1],
            payment_standard=SPRINGFIELD_FMR[1],
            expected_value=5_196,
        )

    def test_scenario_7_five_person_columbia_household(self):
        screen = self.make_screen(household_size=5, county="Boone County", zipcode="65203")
        head = self.add_member(screen, "headOfHousehold", age=38)
        self.add_income(head, 40_000, income_type="wages", frequency="yearly")
        self.add_member(screen, "spouse", age=37)
        self.add_member(screen, "child", age=13)
        self.add_member(screen, "child", age=10)
        self.add_member(screen, "child", age=7)
        self.add_expense(head, 2_000, expense_type="rent", frequency="monthly")

        self._assert_eligible(
            screen,
            income_limit=COLUMBIA_VLI[5],
            payment_standard=COLUMBIA_FMR[3],
            expected_value=7_308,
        )

    def test_scenario_8_rural_non_metro_household_in_texas_county(self):
        screen = self.make_screen(household_size=7, county="Texas County", zipcode="65483")
        head = self.add_member(screen, "headOfHousehold", age=41)
        self.add_income(head, 38_000, income_type="wages", frequency="yearly")
        self.add_member(screen, "spouse", age=40)
        student = self.add_member(screen, "child", age=19, student_full_time=True)
        self.add_income(student, 5_000, income_type="wages", frequency="yearly")
        self.add_member(screen, "child", age=14)
        self.add_member(screen, "child", age=12)
        self.add_member(screen, "child", age=9)
        self.add_member(screen, "child", age=6)
        self.add_expense(head, 1_200, expense_type="rent", frequency="monthly")

        self._assert_eligible(
            screen,
            income_limit=TEXAS_COUNTY_VLI[7],
            payment_standard=TEXAS_COUNTY_FMR[4],
            expected_value=3_576,
        )

    def test_scenario_9_kansas_city_family_renting_below_the_payment_standard(self):
        screen = self._kc_family_of_four(36_000, rent=1_000)
        self._assert_eligible(
            screen,
            income_limit=KANSAS_CITY_VLI[4],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=1_488,
        )

    def test_scenario_10_kansas_city_single_adult_with_an_elderly_deduction(self):
        screen = self.make_screen(household_size=1)
        head = self.add_member(screen, "headOfHousehold", age=63)
        self.add_income(head, 30_000, income_type="wages", frequency="yearly")
        self.add_expense(head, 1_200, expense_type="rent", frequency="monthly")

        self._assert_eligible(
            screen,
            income_limit=KANSAS_CITY_VLI[1],
            payment_standard=KANSAS_CITY_SAFMR[1],
            expected_value=3_360,
        )

    def test_scenario_11_eligible_immigration_status_is_config_only(self):
        """Criterion 3 is evaluated at `config` scope via `legal_status_required`
        and the results-page citizenship filter — no `MoHcv` branch reads legal
        status, so this scenario cannot be exercised as a calculator-level unit
        test. What the calculator *can* promise is asserted instead: this is
        Scenario 1's exact household, which the calculator computes as eligible
        at the same value regardless of any citizenship selection, because that
        selection is applied by a different layer entirely."""
        screen = self._kc_family_of_four(36_000)
        self._assert_eligible(
            screen,
            income_limit=KANSAS_CITY_VLI[4],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=3_408,
        )

    def test_scenario_12_minors_earned_income_excluded_and_generations_bedroom_rule(self):
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", age=38)
        self.add_income(head, 40_000, income_type="wages", frequency="yearly")
        child = self.add_member(screen, "child", age=16)
        self.add_income(child, 10_000, income_type="wages", frequency="yearly")
        self.add_expense(head, 1_500, expense_type="rent", frequency="monthly")

        self._assert_eligible(
            screen,
            income_limit=KANSAS_CITY_VLI[2],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=2_064,
        )

    def test_scenario_13_kansas_city_single_adult_reporting_no_current_rent(self):
        screen = self.make_screen(household_size=1)
        head = self.add_member(screen, "headOfHousehold", age=30)
        self.add_income(head, 20_000, income_type="wages", frequency="yearly")

        self._assert_eligible(
            screen,
            income_limit=KANSAS_CITY_VLI[1],
            payment_standard=KANSAS_CITY_SAFMR[1],
            expected_value=6_240,
        )

    def test_scenario_14_kansas_city_single_adult_aged_exactly_62(self):
        screen = self.make_screen(household_size=1)
        head = self.add_member(screen, "headOfHousehold", age=62)
        self.add_income(head, 24_000, income_type="wages", frequency="yearly")
        self.add_expense(head, 1_200, expense_type="rent", frequency="monthly")

        self._assert_eligible(
            screen,
            income_limit=KANSAS_CITY_VLI[1],
            payment_standard=KANSAS_CITY_SAFMR[1],
            expected_value=5_160,
        )

    def test_scenario_15_kansas_city_family_with_an_eighteen_year_old_non_student(self):
        screen = self.make_screen(household_size=4)
        head = self.add_member(screen, "headOfHousehold", age=36)
        self.add_income(head, 36_000, income_type="wages", frequency="yearly")
        self.add_member(screen, "spouse", age=35)
        adult_child = self.add_member(screen, "child", age=18, student_full_time=False)
        self.add_income(adult_child, 8_000, income_type="wages", frequency="yearly")
        self.add_member(screen, "child", age=12)
        self.add_expense(head, 1_900, expense_type="rent", frequency="monthly")

        self._assert_eligible(
            screen,
            income_limit=KANSAS_CITY_VLI[4],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=864,
        )

    def test_scenario_16_kansas_city_elderly_adult_with_medical_expenses(self):
        screen = self.make_screen(household_size=1)
        head = self.add_member(screen, "headOfHousehold", age=70)
        self.add_income(head, 20_000, income_type="wages", frequency="yearly")
        self.add_expense(head, 1_200, expense_type="rent", frequency="monthly")
        self.add_expense(head, 200 * 12, expense_type="medical", frequency="yearly")

        self._assert_eligible(
            screen,
            income_limit=KANSAS_CITY_VLI[1],
            payment_standard=KANSAS_CITY_SAFMR[1],
            expected_value=6_900,
        )

    def test_scenario_17_kansas_city_parent_whose_childcare_costs_exceed_earnings(self):
        screen = self.make_screen(household_size=3)
        head = self.add_member(screen, "headOfHousehold", age=30)
        self.add_income(head, 5_000, income_type="wages", frequency="yearly")
        self.add_income(head, 15_000, income_type="unemployment", frequency="yearly")
        self.add_member(screen, "child", age=5)
        self.add_member(screen, "child", age=3)
        self.add_expense(head, 1_400, expense_type="rent", frequency="monthly")
        self.add_expense(head, 650 * 12, expense_type="childCare", frequency="yearly")

        self._assert_eligible(
            screen,
            income_limit=KANSAS_CITY_VLI[3],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=9_708,
        )

    def test_scenario_18_kansas_city_household_with_a_foster_child_who_has_earnings(self):
        screen = self.make_screen(household_size=3)
        head = self.add_member(screen, "headOfHousehold", age=40)
        self.add_income(head, 30_000, income_type="wages", frequency="yearly")
        foster = self.add_member(screen, "fosterChild", age=19, student_full_time=False)
        self.add_income(foster, 5_000, income_type="wages", frequency="yearly")
        self.add_member(screen, "child", age=8)
        self.add_expense(head, 1_900, expense_type="rent", frequency="monthly")

        self._assert_eligible(
            screen,
            income_limit=KANSAS_CITY_VLI[3],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=5_064,
        )

    def test_scenario_19_kansas_city_adult_receiving_workers_compensation(self):
        screen = self.make_screen(household_size=1)
        head = self.add_member(screen, "headOfHousehold", age=45)
        self.add_income(head, 22_000, income_type="wages", frequency="yearly")
        self.add_income(head, 12_000, income_type="workersComp", frequency="yearly")
        self.add_expense(head, 1_200, expense_type="rent", frequency="monthly")

        self._assert_eligible(
            screen,
            income_limit=KANSAS_CITY_VLI[1],
            payment_standard=KANSAS_CITY_SAFMR[1],
            expected_value=5_640,
        )

    def test_scenario_20_kansas_city_pregnant_sole_applicant(self):
        screen = self.make_screen(household_size=1)
        head = self.add_member(screen, "headOfHousehold", age=30, pregnant=True)
        self.add_income(head, 20_000, income_type="wages", frequency="yearly")

        self._assert_eligible(
            screen,
            income_limit=KANSAS_CITY_VLI[1],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=7_920,
        )

    def test_scenario_21_kansas_city_eight_person_household_bedroom_cap(self):
        screen = self.make_screen(household_size=8)
        head = self.add_member(screen, "headOfHousehold", age=40)
        self.add_income(head, 40_000, income_type="wages", frequency="yearly")
        self.add_member(screen, "spouse", age=39)
        self.add_member(screen, "sisterOrBrother", age=29)
        self.add_member(screen, "sisterOrBrother", age=27)
        self.add_member(screen, "sisterOrBrother", age=25)
        self.add_member(screen, "child", age=14)
        self.add_member(screen, "child", age=11)
        self.add_member(screen, "child", age=8)
        self.add_expense(head, 2_200, expense_type="rent", frequency="monthly")

        self._assert_eligible(
            screen,
            income_limit=KANSAS_CITY_VLI[8],
            payment_standard=KANSAS_CITY_SAFMR[4],
            expected_value=10_032,
        )

    def test_scenario_22_kansas_city_four_generation_household(self):
        screen = self.make_screen(household_size=5)
        head = self.add_member(screen, "headOfHousehold", age=38)
        self.add_income(head, 34_000, income_type="wages", frequency="yearly")
        self.add_member(screen, "grandParent", age=70)
        self.add_member(screen, "parent", age=60)
        self.add_member(screen, "child", age=12)
        self.add_member(screen, "child", age=9)
        self.add_expense(head, 2_000, expense_type="rent", frequency="monthly")

        self._assert_eligible(
            screen,
            income_limit=KANSAS_CITY_VLI[5],
            payment_standard=KANSAS_CITY_SAFMR[4],
            expected_value=11_688,
        )

    def test_scenario_23_kansas_city_homeowner_paying_a_mortgage_and_no_rent(self):
        screen = self.make_screen(household_size=1)
        head = self.add_member(screen, "headOfHousehold", age=30)
        self.add_income(head, 20_000, income_type="wages", frequency="yearly")
        self.add_expense(head, 700, expense_type="mortgage", frequency="monthly")

        self._assert_eligible(
            screen,
            income_limit=KANSAS_CITY_VLI[1],
            payment_standard=KANSAS_CITY_SAFMR[1],
            expected_value=6_240,
        )

    def test_scenario_24_kansas_city_household_of_three_in_a_single_generation(self):
        screen = self.make_screen(household_size=3)
        head = self.add_member(screen, "headOfHousehold", age=36)
        self.add_income(head, 24_000, income_type="wages", frequency="yearly")
        self.add_member(screen, "roommate", age=34)
        self.add_member(screen, "roommate", age=32)
        self.add_expense(head, 1_500, expense_type="rent", frequency="monthly")

        self._assert_eligible(
            screen,
            income_limit=KANSAS_CITY_VLI[3],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=6_720,
        )

    def test_scenario_25_kansas_city_head_with_an_elderly_domestic_partner(self):
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", age=40)
        self.add_income(head, 24_000, income_type="wages", frequency="yearly")
        self.add_member(screen, "domesticPartner", age=65)
        self.add_expense(head, 1_200, expense_type="rent", frequency="monthly")

        self._assert_eligible(
            screen,
            income_limit=KANSAS_CITY_VLI[2],
            payment_standard=KANSAS_CITY_SAFMR[1],
            expected_value=5_160,
        )

    def test_scenario_26_kansas_city_seventeen_year_old_sole_head_with_wages(self):
        screen = self.make_screen(household_size=1)
        head = self.add_member(screen, "headOfHousehold", age=17)
        self.add_income(head, 18_000, income_type="wages", frequency="yearly")

        self._assert_eligible(
            screen,
            income_limit=KANSAS_CITY_VLI[1],
            payment_standard=KANSAS_CITY_SAFMR[1],
            expected_value=6_840,
        )

    def test_scenario_27_kansas_city_seventeen_year_old_sole_head_over_the_limit(self):
        screen = self.make_screen(household_size=1)
        head = self.add_member(screen, "headOfHousehold", age=17)
        self.add_income(head, 42_000, income_type="wages", frequency="yearly")

        self._assert_ineligible(screen, income_limit=KANSAS_CITY_VLI[1])

    def test_scenario_28_kansas_city_head_with_a_disabled_domestic_partner(self):
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", age=40)
        self.add_income(head, 28_000, income_type="wages", frequency="yearly")
        self.add_member(screen, "domesticPartner", age=45, disabled=True)
        self.add_expense(head, 1_200, expense_type="rent", frequency="monthly")

        self._assert_eligible(
            screen,
            income_limit=KANSAS_CITY_VLI[2],
            payment_standard=KANSAS_CITY_SAFMR[1],
            expected_value=3_960,
        )

    def test_scenario_29_kansas_city_foster_child_young_enough_to_be_a_dependent(self):
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", age=40)
        self.add_income(head, 32_000, income_type="wages", frequency="yearly")
        self.add_member(screen, "fosterChild", age=10)
        self.add_expense(head, 1_900, expense_type="rent", frequency="monthly")

        self._assert_eligible(
            screen,
            income_limit=KANSAS_CITY_VLI[2],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=4_320,
        )

    def test_scenario_30_kansas_city_elderly_couple_both_head_relationship_members_qualifying(self):
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", age=65)
        self.add_income(head, 26_000, income_type="wages", frequency="yearly")
        self.add_member(screen, "spouse", age=63)
        self.add_expense(head, 1_200, expense_type="rent", frequency="monthly")

        self._assert_eligible(
            screen,
            income_limit=KANSAS_CITY_VLI[2],
            payment_standard=KANSAS_CITY_SAFMR[1],
            expected_value=4_560,
        )

    def test_scenario_31_kansas_city_minor_full_time_students_earnings(self):
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", age=38)
        self.add_income(head, 40_000, income_type="wages", frequency="yearly")
        child = self.add_member(screen, "child", age=16, student_full_time=True)
        self.add_income(child, 10_000, income_type="wages", frequency="yearly")
        self.add_expense(head, 1_500, expense_type="rent", frequency="monthly")

        self._assert_eligible(
            screen,
            income_limit=KANSAS_CITY_VLI[2],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=2_064,
        )

    def test_scenario_32_childcare_cap_set_by_an_excluded_minors_earnings(self):
        screen = self.make_screen(household_size=3)
        head = self.add_member(screen, "headOfHousehold", age=35)
        self.add_income(head, 30_000, income_type="wages", frequency="yearly")
        child = self.add_member(screen, "child", age=16)
        self.add_income(child, 6_000, income_type="wages", frequency="yearly")
        self.add_member(screen, "child", age=8)
        self.add_expense(head, 1_900, expense_type="rent", frequency="monthly")
        self.add_expense(head, 8_000, expense_type="childCare", frequency="yearly")

        self._assert_eligible(
            screen,
            income_limit=KANSAS_CITY_VLI[3],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=7_608,
        )

    def test_scenario_33_childcare_deduction_uncapped_and_ten_percent_prong_binds(self):
        screen = self.make_screen(household_size=3)
        head = self.add_member(screen, "headOfHousehold", age=30)
        self.add_income(head, 15_000, income_type="unemployment", frequency="yearly")
        child = self.add_member(screen, "child", age=16)
        self.add_income(child, 6_000, income_type="wages", frequency="yearly")
        self.add_member(screen, "child", age=5)
        self.add_expense(head, 1_400, expense_type="rent", frequency="monthly")
        self.add_expense(head, 10_000, expense_type="childCare", frequency="yearly")

        self._assert_eligible(
            screen,
            income_limit=KANSAS_CITY_VLI[3],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=12_420,
        )

    def test_scenario_34_elderly_head_with_medical_expenses_and_a_working_minor(self):
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", age=70)
        self.add_income(head, 24_300, income_type="wages", frequency="yearly")
        child = self.add_member(screen, "child", age=16)
        self.add_income(child, 6_000, income_type="wages", frequency="yearly")
        self.add_expense(head, 1_500, expense_type="rent", frequency="monthly")
        self.add_expense(head, 300 * 12, expense_type="medical", frequency="yearly")

        self._assert_eligible(
            screen,
            income_limit=KANSAS_CITY_VLI[2],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=7_752,
        )

    def test_scenario_35_two_earner_household_childcare_cap_is_the_lower_wage(self):
        screen = self.make_screen(household_size=4)
        head = self.add_member(screen, "headOfHousehold", age=38)
        self.add_income(head, 30_000, income_type="wages", frequency="yearly")
        spouse = self.add_member(screen, "spouse", age=36)
        self.add_income(spouse, 12_000, income_type="wages", frequency="yearly")
        self.add_member(screen, "child", age=6)
        self.add_member(screen, "child", age=3)
        self.add_expense(head, 1_900, expense_type="rent", frequency="monthly")
        self.add_expense(head, 18_000, expense_type="childCare", frequency="yearly")

        self._assert_eligible(
            screen,
            income_limit=KANSAS_CITY_VLI[4],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=5_208,
        )

    def test_scenario_36_deductions_zero_adjusted_income_minimum_rent_binds(self):
        screen = self.make_screen(household_size=3)
        head = self.add_member(screen, "headOfHousehold", age=35)
        self.add_income(head, 3_600, income_type="wages", frequency="yearly")
        child = self.add_member(screen, "child", age=16)
        self.add_income(child, 14_000, income_type="wages", frequency="yearly")
        self.add_member(screen, "child", age=5)
        self.add_expense(head, 1_500, expense_type="rent", frequency="monthly")
        self.add_expense(head, 3_000, expense_type="childCare", frequency="yearly")

        self._assert_eligible(
            screen,
            income_limit=KANSAS_CITY_VLI[3],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=13_320,
        )

    def test_scenario_37_childcare_cap_set_by_a_students_480_of_included_earnings(self):
        screen = self.make_screen(household_size=3)
        head = self.add_member(screen, "headOfHousehold", age=40)
        self.add_income(head, 28_000, income_type="wages", frequency="yearly")
        student = self.add_member(screen, "child", age=19, student_full_time=True)
        self.add_income(student, 5_000, income_type="wages", frequency="yearly")
        self.add_member(screen, "child", age=5)
        self.add_expense(head, 1_800, expense_type="rent", frequency="monthly")
        self.add_expense(head, 3_000, expense_type="childCare", frequency="yearly")

        self._assert_eligible(
            screen,
            income_limit=KANSAS_CITY_VLI[3],
            payment_standard=KANSAS_CITY_SAFMR[2],
            expected_value=5_808,
        )

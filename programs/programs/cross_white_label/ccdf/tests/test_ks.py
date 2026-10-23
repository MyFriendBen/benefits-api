"""
Unit tests for the KsCcap calculator.

Coverage maps to ``specs/ks.md`` — its five Covered Eligibility Criteria, its
Benefit Value section, and one test per entry in its 31-scenario Test Scenarios
list.

Built on real ``Screen`` / ``HouseholdMember`` / ``IncomeStream`` /
``CurrentBenefit`` rows rather than mocks. Almost every committed figure in the
spec is a question about an accessor the calculator does not own —
``IncomeStream.monthly()`` multiplying by the float-derived ``Decimal(4.35)``,
``calc_age`` flipping on the first of the birth month, ``has_base_benefit``
resolving a state TANF row structurally — and several scenarios are pinned to the
cent *because* of those. A mock standing in for them would assert the mock's own
arithmetic instead of the calculator's.

Every scenario states a birth month, so members carry a real
``birth_year_month`` and the reference date is pinned to the spec's 2026-09-02.
Without the pin, Scenarios 5a/5b, 6a/6b and 13 — each one month either side of a
band or age boundary — would change answer on a calendar boundary.

Not tested here, because the calculator does not implement them:
- Criterion 2 (the child's citizenship) — ``legal_status_required`` is program
  config, never applied as a backend eligibility gate, so asserting an outcome on
  it would test the frontend.
- Kansas residency — enforced structurally by the program row's white label.
- The seventeen data gaps. Where one is handled inclusively no committed result
  turns on it; where one is exclusionary the exclusion is a limit on what the
  screener can see, and the criterion doing the screening carries its own
  scenarios.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from programs.framework.base import Eligibility, ProgramCalculator
from programs.framework.registry import build
from programs.models import Program
from programs.programs.cross_white_label.ccdf.ks import (
    CENTRE_HOURLY_RATES,
    FAMILY_SHARE_DEDUCTIONS,
    MAX_FAMILY_SIZE,
    KsCcap,
)
from programs.programs.testing_fixtures.pe_integration import add_member, make_program, make_screen
from programs.util import DependencyError
from screener.models import HouseholdMember, IncomeStream, Screen
from screener.serializers import _write_current_benefits
from screener.tests.helpers import seed_program

YEAR = "2026"

# Every scenario in the spec is stated against this date.
REFERENCE_DATE = date(2026, 9, 2)

JOHNSON = ("66210", "Johnson County")  # rate Group #1
SEDGWICK = ("67202", "Sedgwick County")  # rate Group #2
COWLEY = ("67156", "Cowley County")  # rate Group #3


class KsCcapTestCase(TestCase):
    """Household builder shared by every test below."""

    # Distinct ids per household keep the members of one screen from colliding
    # with another's when a test builds more than one.
    next_screen_id = 1

    def setUp(self):
        reference_date = patch.object(Screen, "get_reference_date", return_value=REFERENCE_DATE)
        reference_date.start()
        self.addCleanup(reference_date.stop)

    def build(self, household_size, location=JOHNSON, assets=Decimal("2000")):
        zipcode, county = location
        screen = make_screen(
            self.next_screen_id,
            white_label_code="ks",
            state_code="KS",
            household_size=household_size,
            zipcode=zipcode,
            county=county,
            household_assets=assets,
        )
        # Reused rather than recreated: a test that builds more than one household
        # would otherwise collide on the program row's unique
        # (white_label, name_abbreviated).
        existing = Program.objects.filter(white_label=screen.white_label, name_abbreviated="ks_ccap").first()
        self.program = existing or make_program("ks", "ks_ccap", YEAR)
        self.member_id = self.next_screen_id * 100
        KsCcapTestCase.next_screen_id += 1
        return screen

    def add_person(self, screen, relationship, born, **kwargs):
        """A member stated by the (year, month) the scenario gives.

        Both ``birth_year_month`` and ``age`` are set: the calculator reads
        ``calc_age()``, which prefers the birth date, while ``missing_fields()``
        reads ``age`` and would drop the program from results if it were null.
        """
        self.member_id += 1
        birth_year_month = date(born[0], born[1], 1)
        return add_member(
            screen,
            self.member_id,
            relationship,
            HouseholdMember.age_from_date(birth_year_month, REFERENCE_DATE),
            birth_year_month=birth_year_month,
            **kwargs,
        )

    def add_hourly(self, member, rate, hours, income_type="wages"):
        """An hourly wage stream, the only frequency carrying ``hours_worked``."""
        return IncomeStream.objects.create(
            screen=member.screen,
            household_member=member,
            type=income_type,
            amount=Decimal(str(rate)),
            frequency="hourly",
            hours_worked=hours,
        )

    def add_monthly(self, member, amount, income_type="wages"):
        return IncomeStream.objects.create(
            screen=member.screen,
            household_member=member,
            type=income_type,
            amount=Decimal(str(amount)),
            frequency="monthly",
        )

    def receive_tanf(self, screen):
        """A real ``CurrentBenefit`` row, so ``has_base_benefit`` resolves it the
        way it does in production — structurally, off ``base_program``."""
        seed_program(screen.white_label, "ks_tanf", base_program="tanf")
        _write_current_benefits(screen, ["ks_tanf"])
        screen.invalidate_current_benefits_cache()

    def calculator(self, screen):
        return KsCcap(screen, self.program, {}, screen.missing_fields())

    def calc(self, screen):
        return self.calculator(screen).calc()

    def assert_eligible(self, screen, value):
        eligibility = self.calc(screen)
        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, value)
        return eligibility

    def assert_ineligible(self, screen):
        eligibility = self.calc(screen)
        self.assertFalse(eligibility.eligible)
        return eligibility

    # The household Scenarios 1, 5a/5b, 8b, 16 and 17 all perturb: a head working
    # 30 hours at $23.00, a preschooler, and a 16-year-old who counts toward family
    # size without being an eligible child.
    def baseline(self, location=JOHNSON, assets=Decimal("2000"), child_born=(2022, 1)):
        screen = self.build(3, location=location, assets=assets)
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "23.00", 30)
        self.add_person(screen, "child", child_born)
        self.add_person(screen, "child", (2010, 5))
        return screen


class TestClassAttributes(KsCcapTestCase):
    def test_is_a_plain_program_calculator(self):
        # Deliberately not a subclass of this family's `Ccdf` base, which wraps
        # PolicyEngine's `is_ccdf_eligible`.
        self.assertTrue(issubclass(KsCcap, ProgramCalculator))

    def test_registered_under_ks_ccap(self):
        self.assertIs(build("programs.programs", ProgramCalculator).get("ks_ccap"), KsCcap)

    def test_resource_limit_is_the_kansas_figure_not_the_federal_one(self):
        # KEESM 5140. `il_ccap` uses the federal CCDF $1,000,000 ceiling; inheriting
        # it would apply a limit 100 times too high.
        self.assertEqual(KsCcap.RESOURCE_LIMIT, Decimal("10000"))

    def test_federal_minimum_wage_is_7_25(self):
        self.assertEqual(KsCcap.FEDERAL_MINIMUM_WAGE, Decimal("7.25"))

    def test_minimum_weekly_hours_is_20(self):
        self.assertEqual(KsCcap.MINIMUM_WEEKLY_HOURS, 20)

    def test_authorized_hours_are_keesm_7620s_two_blocks(self):
        self.assertEqual(KsCcap.PART_TIME_HOURS, 129)
        self.assertEqual(KsCcap.FULL_TIME_HOURS, 215)
        self.assertEqual(KsCcap.HOURS_NEEDED_THRESHOLD, 108)

    def test_child_relationships_carry_keesm_4410s_catch_all(self):
        # `relatedOther` is the catch-all limb `il_ccap`'s six-value set omits.
        self.assertEqual(
            set(KsCcap.child_relationships),
            {
                "child",
                "stepChild",
                "fosterChild",
                "grandChild",
                "sisterOrBrother",
                "stepSisterOrBrother",
                "relatedOther",
            },
        )

    def test_only_the_head_and_a_spouse_or_partner_are_activity_tested(self):
        self.assertEqual(set(KsCcap.tested_relationships), {"headOfHousehold", "spouse", "domesticPartner"})

    def test_household_assets_is_not_a_declared_dependency(self):
        # Declaring it would drop the program from results before the committed
        # fall-open resource test could run, contradicting Scenario 17.
        self.assertNotIn("household_assets", KsCcap.dependencies)

    def test_household_size_is_a_declared_dependency(self):
        # The opposite call: it keys both the income ceiling and the family share
        # deduction, and no other field recovers it.
        self.assertIn("household_size", KsCcap.dependencies)


class TestPublishedTables(KsCcapTestCase):
    def test_family_share_grid_covers_sizes_two_through_eight(self):
        self.assertEqual(sorted(FAMILY_SHARE_DEDUCTIONS), [2, 3, 4, 5, 6, 7, 8])

    def test_every_family_size_has_eleven_bands(self):
        for size, bands in FAMILY_SHARE_DEDUCTIONS.items():
            with self.subTest(size=size):
                self.assertEqual(len(bands), 11)

    def test_bands_ascend_in_both_bound_and_deduction(self):
        # A band out of order would silently shadow the ones after it, since the
        # lookup returns the first bound the income falls under.
        for size, bands in FAMILY_SHARE_DEDUCTIONS.items():
            with self.subTest(size=size):
                bounds = [bound for bound, _ in bands]
                deductions = [deduction for _, deduction in bands]
                self.assertEqual(bounds, sorted(bounds))
                self.assertEqual(deductions, sorted(deductions))

    def test_first_band_charges_nothing(self):
        # F-1 assesses no family share below 100% FPL (KEESM 7541).
        for size, bands in FAMILY_SHARE_DEDUCTIONS.items():
            with self.subTest(size=size):
                self.assertEqual(bands[0][1], 0)

    def test_income_limit_is_the_top_bands_bound(self):
        # The two are one published table read twice; deriving the limit is what
        # stops them drifting apart on the next annual refresh.
        published_85_percent_smi = {
            2: Decimal("5439"),
            3: Decimal("6719"),
            4: Decimal("7998"),
            5: Decimal("9278"),
            6: Decimal("10558"),
            7: Decimal("10798"),
            8: Decimal("11038"),
        }
        for size, limit in published_85_percent_smi.items():
            with self.subTest(size=size):
                screen = self.build(size)
                self.assertEqual(self.calculator(screen).income_limit(), limit)

    def test_centre_rates_are_not_monotonic_across_county_groups(self):
        # Group #3's 36-59 month rate exceeds Group #2's, as printed in C-18a. An
        # implementation deriving Group #3 by scaling Group #2 cannot reproduce this.
        _, (_, group_2, group_3) = CENTRE_HOURLY_RATES[2]
        self.assertGreater(group_3, group_2)

    def test_county_groups_use_the_white_labels_spellings(self):
        # C-18/C-18a print "Greely" and "Pottawatomi"; those match no county in the
        # KS white label and would drop both silently into Group #3.
        screen = self.build(2)
        calculator = self.calculator(screen)
        for county in ("Greeley County", "Pottawatomie County"):
            with self.subTest(county=county):
                screen.county = county
                self.assertEqual(calculator.county_group_index(), 1)


class TestScenarios(KsCcapTestCase):
    """One test per entry in the spec's Test Scenarios section."""

    def test_scenario_1_baseline_johnson_county_one_eligible_child(self):
        # $5.51 x 129 = $710.79/month; - $89 FSD (family of 3, $2,960.01-$3,187
        # band) = $621.79; x 12 = $7,461.48 -> $7,461. Assets sit at exactly
        # $10,000, so a strict `<` would deny this household.
        screen = self.baseline(assets=Decimal("10000.00"))
        self.assert_eligible(screen, 13_147)

    def test_scenario_2a_family_share_band_lower_edge(self):
        # The F-1 band is read inclusively at its upper bound, and this is also the
        # exactly-20-hours pass case for criterion 3.
        screen = self.build(2)
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "10.00", 20)
        self.add_monthly(head, "2015.00")  # total $2,885.00
        self.add_person(screen, "child", (2022, 1))
        self.assert_eligible(screen, 7_557)

    def test_scenario_2b_one_cent_moves_the_band(self):
        # Kills an off-by-one band comparison (`<` where `<=` belongs) — the
        # likeliest table bug, worth $72/year here.
        screen = self.build(2)
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "10.00", 20)
        self.add_monthly(head, "2015.01")  # total $2,885.01
        self.add_person(screen, "child", (2022, 1))
        self.assert_eligible(screen, 7_485)

    def test_scenario_3a_county_group_2(self):
        # $4.13 x 129 = $532.77; - $89 = $443.77; x 12 = $5,325.24 -> $5,325.
        self.assert_eligible(self.baseline(location=SEDGWICK), 9_587)

    def test_scenario_3b_county_group_3_pays_more_than_group_2(self):
        # $4.27 x 129 = $550.83; - $89 = $461.83; x 12 = $5,541.96 -> $5,541. Also a
        # truncation case: rounding would return $5,542.
        self.assert_eligible(self.baseline(location=COWLEY), 9_948)

    def test_scenario_4a_income_exactly_at_the_85_percent_smi_limit(self):
        # A strict `<` at the ceiling would deny a family sitting on the published
        # limit.
        screen = self.build(2)
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "10.00", 20)
        self.add_monthly(head, "4569.00")  # total $5,439.00, the family-of-2 limit
        self.add_person(screen, "child", (2022, 1))
        self.assert_eligible(screen, 6_525)

    def test_scenario_4b_income_one_cent_over_the_limit(self):
        # Paired with 4a: kills a table that falls through to the top band instead
        # of denying above it.
        screen = self.build(2)
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "10.00", 20)
        self.add_monthly(head, "4569.01")  # total $5,439.01
        self.add_person(screen, "child", (2022, 1))
        self.assert_ineligible(screen)

    def test_scenario_5a_rate_age_band_59_months(self):
        # The upper edge of the 36-59 month centre band.
        self.assert_eligible(self.baseline(child_born=(2021, 10)), 13_147)

    def test_scenario_5b_rate_age_band_60_months(self):
        # One month of age is worth $1,083.60/year. Also a truncation case:
        # $6,377.88 would round to $6,378.
        self.assert_eligible(self.baseline(child_born=(2021, 9)), 11_341)

    def test_scenario_6a_child_reaches_13_in_the_reference_month(self):
        # `calc_age` flips on the first of the birth month, not the birthday, so
        # this kills a day-precision age test.
        screen = self.build(2)
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "23.00", 30)
        self.add_person(screen, "child", (2013, 9))
        self.assert_ineligible(screen)

    def test_scenario_6b_child_one_month_younger(self):
        # The other side of the same boundary. A two-person household, so the
        # deduction is the family-of-2 $87 rather than 5a/5b's family-of-3 $89.
        screen = self.build(2)
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "23.00", 30)
        self.add_person(screen, "child", (2013, 10))
        self.assert_eligible(screen, 11_365)

    def test_scenario_7_disabled_15_year_old(self):
        # Kills an unconditional `age < 13`, which would drop every eligible
        # disabled teenager.
        screen = self.build(2)
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "10.00", 20)
        self.add_monthly(head, "2015.00")
        self.add_person(screen, "child", (2011, 1), long_term_disability=True)
        self.assert_eligible(screen, 6_473)

    def test_scenario_8_a_second_adult_works_19_hours(self):
        # The scenario separating the sourced Kansas rule from `il_ccap`, which
        # tests only the head. 19 hours also pins the threshold to the hour.
        screen = self.build(3)
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "23.00", 30)
        spouse = self.add_person(screen, "spouse", (1993, 7))
        self.add_hourly(spouse, "15.00", 19)
        self.add_person(screen, "child", (2022, 1))
        self.assert_ineligible(screen)

    def test_scenario_8b_a_non_working_grandparent_is_not_tested(self):
        # KEESM 4410 does not put a non-caretaking grandparent on the case, so
        # neither half of the activity test reaches them. They still count toward
        # family size, which is why the value matches Scenario 1 exactly.
        screen = self.build(3)
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "23.00", 30)
        self.add_person(screen, "child", (2022, 1))
        self.add_person(screen, "grandParent", (1958, 6))
        self.assert_eligible(screen, 13_147)

    def test_scenario_8c_a_disabled_adult_under_20_hours_is_excused(self):
        # Scenario 8 with the 19-hour spouse made disabled. The only scenario
        # reaching the incapacity exemption; the spouse earns $15.00/hr so the wage
        # floor, which carries no such exemption, stays clear.
        screen = self.build(3)
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "23.00", 30)
        spouse = self.add_person(screen, "spouse", (1993, 7), long_term_disability=True)
        self.add_hourly(spouse, "15.00", 19)
        self.add_person(screen, "child", (2022, 1))
        self.assert_eligible(screen, 5_997)

    def test_scenario_8d_a_spouse_with_no_employment_at_all(self):
        # The branch Data Gap 6 does not reach. Summing hours over an empty set of
        # hourly streams and treating the result as unevaluable — the fall-open the
        # gap directs for a salaried earner — would return Eligible at $7,461.
        screen = self.build(3)
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "23.00", 30)
        self.add_person(screen, "spouse", (1993, 7))
        self.add_person(screen, "child", (2022, 1))
        self.assert_ineligible(screen)

    def test_scenario_9_hourly_wage_one_cent_below_the_federal_minimum(self):
        # Kills an implementation checking hours only, even at 30 hours a week.
        screen = self.build(2)
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "7.24", 30)
        self.add_person(screen, "child", (2022, 1))
        self.assert_ineligible(screen)

    def test_scenario_9b_wage_exactly_at_the_minimum_income_below_100_percent_fpl(self):
        # Two rules at once: a strict `> 7.25` would deny this household, and the
        # only scenario in the $0 deduction band — omitting F-1's $0-$1,803 row and
        # falling through to the 110% row would charge $54 a month not owed.
        screen = self.build(2)
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "7.25", 20)
        self.add_person(screen, "child", (2021, 9))
        self.assert_eligible(screen, 7_445)

    def test_scenario_9c_two_hourly_jobs_one_below_the_floor(self):
        # ($12.00 x 20 + $6.00 x 10) / 30 = $10.00/hour. Testing each stream on its
        # own returns Ineligible on the $6.00 job, which no captured source directs.
        screen = self.build(2)
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "12.00", 20)
        self.add_hourly(head, "6.00", 10)
        self.add_monthly(head, "700.00")  # total $2,005.00
        self.add_person(screen, "child", (2022, 1))
        self.assert_eligible(screen, 13_495)

    def test_scenario_10_a_16_year_olds_wages_are_exempt(self):
        # Kills the default `calc_gross_income` call, which sums every stream
        # regardless of the earner's age: counting the teenager's $1,200 gives
        # $4,160.00, the $123 band and $7,053.
        screen = self.build(3)
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "10.00", 20)
        self.add_monthly(head, "2090.00")
        self.add_person(screen, "child", (2022, 1))
        teenager = self.add_person(screen, "child", (2010, 5))
        self.add_monthly(teenager, "1200.00")
        self.assert_eligible(screen, 7_545)

    def test_scenario_11_resources_one_cent_over_the_limit(self):
        # Paired with Scenario 1's exactly-$10,000 pass, pins the limit to the cent.
        screen = self.build(2, assets=Decimal("10000.01"))
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "23.00", 30)
        self.add_person(screen, "child", (2022, 1))
        self.assert_ineligible(screen)

    def test_scenario_12_tanf_household_above_the_income_ceiling(self):
        # All three TANF branches at once: the income test waived at $7,001.50
        # against a $6,719 limit, the resource limit bypassed at $12,000, and the
        # family share zeroed.
        screen = self.build(3, assets=Decimal("12000"))
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "23.00", 30)
        self.add_monthly(head, "4000.00")
        self.add_person(screen, "child", (2022, 1))
        self.add_person(screen, "child", (2010, 5))
        self.receive_tanf(screen)
        self.assert_eligible(screen, 14_215)

    def test_scenario_13_three_eligible_children_one_family_share(self):
        # $7.33 + $6.25 + $5.51 = $19.09/hour x 129 = $2,462.61; - one $298 FSD.
        # Deducting per child would subtract $894 and understate by $7,152/year.
        # The two younger children sit on the 11/12 and 35/36 month band edges.
        screen = self.build(5)
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "10.00", 20)
        self.add_monthly(head, "5000.00")
        spouse = self.add_person(screen, "spouse", (1993, 7))
        self.add_hourly(spouse, "12.00", 25)
        self.add_person(screen, "child", (2025, 10))  # 11 months
        self.add_person(screen, "child", (2023, 10))  # 35 months
        self.add_person(screen, "child", (2022, 1))  # 56 months
        self.assert_eligible(screen, 25_975)

    def test_scenario_14_a_grandchild_and_a_niece_both_count(self):
        # Neither child is the head's own, so both are admitted through KEESM
        # 4410's catch-all. Shipping `il_ccap`'s six-value set drops the
        # `relatedOther` and returns $7,377, understating by $8,529/year.
        screen = self.build(3)
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "10.00", 20)
        self.add_monthly(head, "2545.00")  # total $3,415.00
        self.add_person(screen, "grandChild", (2022, 1))
        self.add_person(screen, "relatedOther", (2022, 1))
        self.assert_eligible(screen, 15_906)

    def test_scenario_15_the_deduction_exceeds_the_gross_benefit(self):
        # $3.16 x 129 = $407.64 against a $430 family share. Unclamped this returns
        # -$268.32; clamped to $0 without the outer floor the household is dropped
        # from the results page by `programValue > 0`. Returning $12 would mean the
        # floor had been applied per month rather than once to the annual figure.
        #
        # The clamp is reachable only on the part-time block: at 215 hours the
        # smallest gross this program can produce is $2.42 x 215 = $520.30, above
        # every published deduction. So both adults work exactly 20 hours -- the
        # criterion 3 minimum -- and earn enough per hour to reach family-of-8's top
        # band, which is the only band whose $430 deduction can exceed the benefit.
        screen = self.build(8, location=COWLEY, assets=Decimal("5000"))
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "50.00", 20)
        spouse = self.add_person(screen, "spouse", (1993, 7))
        self.add_hourly(spouse, "50.00", 20)  # household total $8,700.00/month
        self.add_person(screen, "child", (2019, 3))  # 90 months, the only eligible child
        for born in ((2009, 5), (2010, 5), (2011, 5), (2012, 5), (2013, 5)):
            self.add_person(screen, "child", born)
        self.assert_eligible(screen, 1)

    def test_scenario_16_the_band_whose_f_1_bound_carries_a_source_typo(self):
        # $3,870.05 falls inside the gap a literal transcription of the PDF leaves
        # unmapped ($3,870.01-$3,870.09), where such a table finds no band at all.
        screen = self.build(3)
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "10.00", 20)
        self.add_monthly(head, "3000.05")  # total $3,870.05
        self.add_person(screen, "child", (2022, 1))
        self.add_person(screen, "child", (2010, 5))
        self.assert_eligible(screen, 7_137)

    def test_scenario_17_assets_not_provided(self):
        # Scenario 1 with the asset figure omitted. Kills both a null-as-failure
        # reading and a crash on `None`.
        self.assert_eligible(self.baseline(assets=None), 13_147)

    def test_scenario_18_an_ssi_parents_wages_are_exempt_too(self):
        # KEESM 6410 exempts the income of an SSI *recipient*. Counting the head's
        # income gives $4,447.00, the $211 band and $5,997; exempting only the `sSI`
        # stream gives $3,480.00, the $102 band and $7,305.
        screen = self.build(3)
        head = self.add_person(screen, "headOfHousehold", (1994, 3), disabled=True)
        self.add_monthly(head, "967.00", income_type="sSI")
        self.add_hourly(head, "10.00", 20)
        spouse = self.add_person(screen, "spouse", (1993, 7))
        self.add_hourly(spouse, "20.00", 30)
        self.add_person(screen, "child", (2022, 1))
        self.assert_eligible(screen, 7_629)

    def test_scenario_18b_the_ssi_recipient_is_the_parent_not_the_child(self):
        # Scenario 18 with assets over the limit. A household-level
        # `has_base_benefit("ssi")` reading is true here — it is set from the head's
        # own stream — and would waive the resource limit, returning $7,629.
        screen = self.build(3, assets=Decimal("15000"))
        head = self.add_person(screen, "headOfHousehold", (1994, 3), disabled=True)
        self.add_monthly(head, "967.00", income_type="sSI")
        self.add_hourly(head, "10.00", 20)
        spouse = self.add_person(screen, "spouse", (1993, 7))
        self.add_hourly(spouse, "20.00", 30)
        self.add_person(screen, "child", (2022, 1))
        self.assert_ineligible(screen)

    def test_scenario_19_tanf_household_under_both_the_hours_and_the_wage_floor(self):
        # The head fails both halves — 10 hours against 20, $7.00 against $7.25 —
        # and Kansas applies neither to a TANF case. Bypassing only the hours half
        # returns Ineligible.
        screen = self.build(2, location=SEDGWICK)
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "7.00", 10)
        self.add_person(screen, "child", (2022, 1))
        self.receive_tanf(screen)
        self.assert_eligible(screen, 6_393)

    def test_scenario_20_the_only_eligible_child_receives_ssi(self):
        # One household kills both halves of the SSI treatment: applying the
        # $10,000 limit unconditionally returns Ineligible, and counting the child's
        # SSI as income gives $3,337.00, the top band's $167 and $6,525.
        screen = self.build(2, assets=Decimal("15000"))
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "10.00", 20)
        self.add_monthly(head, "1500.00")  # total $2,370.00
        child = self.add_person(screen, "child", (2022, 1))
        self.add_monthly(child, "967.00", income_type="sSI")
        self.assert_eligible(screen, 7_689)


class TestValueShape(KsCcapTestCase):
    def test_the_whole_figure_is_the_household_value(self):
        # Both `max` operations are on the household total, so `il_ccap`'s split
        # across `member_value` and a negative `household_value` cannot express
        # either clamp.
        eligibility = self.calc(self.baseline())
        self.assertEqual(eligibility.household_value, 13_147)
        self.assertEqual([member.value for member in eligibility.eligible_members], [0, 0, 0])

    def test_value_is_truncated_rather_than_rounded(self):
        # $9,948.60 -> $9,948. The `math.trunc` in `screener/views.py` touches only
        # the payload's `estimated_value`, while the results card reads
        # `household_value` and formats it with `maximumFractionDigits: 0`.
        screen = self.baseline(location=COWLEY)
        self.assertEqual(self.calculator(screen).household_value(), 9_948)

    def test_an_ineligible_child_contributes_no_hours_block(self):
        # The 16-year-old in the baseline counts toward family size but is not in
        # the sum: a second block would make this $15,990.
        screen = self.baseline()
        self.assertEqual(len(self.calculator(screen).eligible_children()), 1)


class TestAuthorizedHoursBlock(KsCcapTestCase):
    """
    KEESM 7620's block, derived from the adults' reported schedule rather than
    pinned. 108 hours a month is 24.83 hours a week at the screener's own 4.35
    weeks-per-month factor, so the block turns over between 24 and 25 hours.
    """

    def hours_for(self, adults):
        """`adults` is a list of (relationship, weekly hours or None)."""
        screen = self.build(3)
        for relationship, weekly in adults:
            member = self.add_person(
                screen, relationship, (1994, 3) if relationship == "headOfHousehold" else (1993, 7)
            )
            if weekly is not None:
                self.add_hourly(member, "20.00", weekly)
            elif weekly is None and relationship != "headOfHousehold":
                self.add_monthly(member, "3000.00")  # salaried: no hours_worked
        self.add_person(screen, "child", (2022, 1))
        return self.calculator(screen).authorized_monthly_hours()

    def test_twenty_hours_is_part_time(self):
        # 20 x 4.35 = 87 hours needed, at or under the 108 threshold.
        self.assertEqual(self.hours_for([("headOfHousehold", 20)]), 129)

    def test_twenty_four_hours_is_still_part_time(self):
        # 24 x 4.35 = 104.4, the last whole week under the threshold.
        self.assertEqual(self.hours_for([("headOfHousehold", 24)]), 129)

    def test_twenty_five_hours_crosses_to_full_time(self):
        # 25 x 4.35 = 108.75, the first whole week over it.
        self.assertEqual(self.hours_for([("headOfHousehold", 25)]), 215)

    def test_forty_hours_is_full_time(self):
        self.assertEqual(self.hours_for([("headOfHousehold", 40)]), 215)

    def test_the_block_follows_the_least_working_adult(self):
        # Care is needed only while every adult on the case is away, and without
        # schedules the overlap cannot exceed the shorter of the two. A 40-hour
        # parent alongside a 20-hour parent needs the part-time block, not the
        # full-time one the 40 alone would give.
        self.assertEqual(self.hours_for([("headOfHousehold", 40), ("spouse", 20)]), 129)
        self.assertEqual(self.hours_for([("headOfHousehold", 40), ("spouse", 30)]), 215)

    def test_a_non_nuclear_adults_hours_are_ignored(self):
        # A grandparent is not on the case, so their schedule is not DCF's input.
        screen = self.build(3)
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "20.00", 40)
        grandparent = self.add_person(screen, "grandParent", (1958, 6))
        self.add_hourly(grandparent, "20.00", 20)
        self.add_person(screen, "child", (2022, 1))
        self.assertEqual(self.calculator(screen).authorized_monthly_hours(), 215)

    def test_one_unreadable_schedule_falls_back_to_part_time(self):
        # A salaried spouse carries no `hours_worked`, so the household's minimum
        # is unknowable and the estimate takes the lower block rather than reading
        # the head's hours as if they were the household's.
        self.assertEqual(self.hours_for([("headOfHousehold", 40), ("spouse", None)]), 129)

    def test_no_derivable_hours_at_all_falls_back_to_part_time(self):
        screen = self.build(2)
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_monthly(head, "3000.00")
        self.add_person(screen, "child", (2022, 1))
        self.assertEqual(self.calculator(screen).authorized_monthly_hours(), 129)

    def test_the_block_is_per_child_and_the_deduction_is_not(self):
        # Scenario 13's household on the full-time block: three children each get
        # 215 hours, but still one family share between them.
        screen = self.build(5)
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "10.00", 30)
        self.add_monthly(head, "3695.00")
        spouse = self.add_person(screen, "spouse", (1993, 7))
        self.add_hourly(spouse, "12.00", 30)
        for born in ((2025, 10), (2023, 10), (2022, 1)):
            self.add_person(screen, "child", born)
        calculator = self.calculator(screen)
        self.assertEqual(calculator.authorized_monthly_hours(), 215)
        # ($7.33 + $6.25 + $5.51) x 215 = $4,104.35, less one $298 deduction.
        self.assertEqual(calculator.household_value(), 45_676)


class TestCommittedBranchesWithoutScenarios(KsCcapTestCase):
    """
    Behaviour the spec commits to but writes no scenario for, either because the
    screener form cannot produce the input or because it shifts only the deduction
    band. Each is reachable through the API path, so each is pinned here.
    """

    def test_a_null_birth_date_and_age_is_not_an_eligible_child(self):
        # Tested on the predicate rather than through `calc()`: a null `age` is a
        # missing dependency, so the program would be dropped before this ran.
        screen = self.build(2)
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "23.00", 30)
        self.member_id += 1
        undated = add_member(screen, self.member_id, "child", None, birth_year_month=None)
        self.assertFalse(self.calculator(screen).is_eligible_child(undated))

    def test_a_null_hours_worked_falls_open_on_both_halves(self):
        # Unevaluable rather than a failure: the same direction Data Gap 6 takes for
        # a non-hourly earner.
        screen = self.build(2)
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        IncomeStream.objects.create(
            screen=screen,
            household_member=head,
            type="wages",
            amount=Decimal("2000.00"),
            frequency="hourly",
            hours_worked=None,
        )
        self.add_person(screen, "child", (2022, 1))
        self.assertTrue(self.calculator(screen).meets_personal_need())

    def test_a_salaried_earner_is_not_screened_out_on_either_half(self):
        # Data Gap 6: `hours_worked` is populated only on hourly streams, so a
        # monthly earner's hours and implied wage are both underivable.
        screen = self.build(2)
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_monthly(head, "1200.00")
        self.add_person(screen, "child", (2022, 1))
        self.assertTrue(self.calculator(screen).meets_personal_need())

    def test_an_18_year_olds_earnings_are_exempt_while_a_student(self):
        # The under-19 limb of KEESM 6410's child-earnings exemption. It shifts the
        # deduction band rather than the verdict, so no scenario turns on it.
        screen = self.build(3)
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "10.00", 20)
        self.add_person(screen, "child", (2022, 1))
        eighteen = self.add_person(screen, "child", (2008, 5), student=True)
        self.add_monthly(eighteen, "1000.00")
        self.assertEqual(self.calculator(screen).countable_monthly_income(), Decimal("870.00"))

    def test_an_18_year_old_who_is_not_a_student_has_earnings_counted(self):
        screen = self.build(3)
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "10.00", 20)
        self.add_person(screen, "child", (2022, 1))
        eighteen = self.add_person(screen, "child", (2008, 5), student=False)
        self.add_monthly(eighteen, "1000.00")
        self.assertEqual(self.calculator(screen).countable_monthly_income(), Decimal("1870.00"))

    def test_a_null_student_flag_reads_as_a_student(self):
        # The inclusive direction: exempting the earnings lowers countable income.
        screen = self.build(3)
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "10.00", 20)
        self.add_person(screen, "child", (2022, 1))
        eighteen = self.add_person(screen, "child", (2008, 5))
        self.add_monthly(eighteen, "1000.00")
        self.assertEqual(self.calculator(screen).countable_monthly_income(), Decimal("870.00"))

    def test_a_null_household_size_drops_the_program_from_results(self):
        # Rather than substituting the member count, which is a different number:
        # `household_size` is user-entered and independent of the member list, and
        # it keys both the income ceiling and the family share deduction. Guessing
        # it wrong denies an eligible household or inflates an ineligible one's
        # value with no signal; `DependencyError` is what the eligibility loop
        # catches to leave the program out instead.
        screen = self.build(3)
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "23.00", 30)
        self.add_person(screen, "child", (2022, 1))
        screen.household_size = None
        screen.save()

        calculator = self.calculator(screen)
        self.assertFalse(calculator.can_calc())
        with self.assertRaises(DependencyError):
            calculator.calc()

    def test_family_size_is_clamped_to_the_implemented_range(self):
        # Deliberately the implemented range, not the published one: Appendix F-1
        # publishes sizes 2-11, and this calculator carries 2-8 because the screener
        # form validates `.lte(8)`. Both ends are API-path only -- below 2 cannot
        # arise because criterion 1 requires an eligible child.
        for household_size, expected in ((1, 2), (9, 8), (11, 8)):
            with self.subTest(household_size=household_size):
                screen = self.build(household_size)
                self.assertEqual(self.calculator(screen).family_size(), expected)

    def test_the_grid_stops_at_the_screener_form_cap(self):
        # Pins the ceiling to the form's `.lte(8)`. If that cap is ever raised, this
        # fails and points at the three F-1 rows (9, 10, 11) that must be added.
        self.assertEqual(MAX_FAMILY_SIZE, 8)

    def test_no_eligible_child_means_no_ssi_resource_exemption(self):
        # `all()` over an empty set is vacuously true, which would waive the
        # $10,000 limit for a household with no children at all.
        screen = self.build(2, assets=Decimal("15000"))
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "23.00", 30)
        self.add_person(screen, "child", (2013, 9))  # turns 13, not an eligible child
        self.assertFalse(self.calculator(screen).resources_within_limit())

    def test_household_eligibility_reports_the_income_that_failed(self):
        screen = self.build(2)
        head = self.add_person(screen, "headOfHousehold", (1994, 3))
        self.add_hourly(head, "10.00", 20)
        self.add_monthly(head, "4569.01")
        self.add_person(screen, "child", (2022, 1))

        eligibility = Eligibility()
        self.calculator(screen).household_eligible(eligibility)
        self.assertFalse(eligibility.eligible)
        self.assertEqual(len(eligibility.fail_messages), 1)

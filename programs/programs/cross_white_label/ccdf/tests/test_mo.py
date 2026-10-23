"""
Unit tests for the MoChildCareSubsidy calculator.

Coverage maps to ``specs/mo.md`` — its Covered Eligibility Criteria, its Benefit Value
section, and one test per entry in its 51-scenario Test Scenarios list.

Built on real ``Screen`` / ``HouseholdMember`` / ``IncomeStream`` / ``Expense`` rows
rather than mocks, for the reason ``test_ks.py`` gives: the boundaries the spec pins
are questions about ``calc_age``'s month granularity and ``IncomeStream.monthly()``,
which a mock would stand in for rather than test.

Every scenario states a birth month, so members carry a real ``birth_year_month`` and
the reference date is pinned — to the spec's 2026-09-04 unless a scenario states its
own evaluation date.

Not tested here, because the calculator does not implement them:
- Criteria 1-3 (residency, co-residence, the child's citizenship) — ``assumed-met`` or
  program config, with no calculator branch.
- Criterion 5 (valid need) — it cannot screen a household out, so has no condition.
- The Protective Services route and the homelessness waiver — unobservable.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from configuration.white_labels.mo import MoConfigurationData
from programs.framework.base import ProgramCalculator
from programs.framework.registry import build
from programs.programs.cross_white_label.ccdf.mo import (
    CHART_MAXIMUM,
    COUNTY_REGIONS,
    DAILY_FEES,
    FEE_BAND_TOPS,
    REGION_1,
    REGION_5,
    REGION_BY_COUNTY,
    SMI_85_PERCENT,
    MoChildCareSubsidy,
    normalize_county,
)
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from programs.util import DependencyError
from screener.models import IncomeStream, Screen

YEAR = "2026"

# Every scenario without its own evaluation date is stated against this one.
REFERENCE_DATE = date(2026, 9, 4)

ST_LOUIS_CITY = ("63101", "St. Louis City")  # Region 1 Dense Urban
FRANKLIN = ("63084", "Franklin County")  # Region 2 Metro
GREENE = ("65806", "Greene County")  # Region 3 Urban
PHELPS = ("65401", "Phelps County")  # Region 4 Micropolitan
TEXAS = ("65483", "Texas County")  # Region 5 Rural
ST_LOUIS_COUNTY = ("63011", "St. Louis County")  # Region 1 Dense Urban


class MoChildCareSubsidyTestCase(CustomCalculatorTestCase):
    """Household builder shared by every test below."""

    calculator_class = MoChildCareSubsidy
    white_label_code = "mo"
    state_code = "MO"
    fpl_year = YEAR

    def setUp(self):
        # Not the base class's `reference_date`, which is fixed for the whole test:
        # a few scenarios move the evaluation date before building their household.
        super().setUp()
        self.evaluation_date = REFERENCE_DATE
        evaluation_date = patch.object(Screen, "get_reference_date", side_effect=lambda: self.evaluation_date)
        evaluation_date.start()
        self.addCleanup(evaluation_date.stop)

    def build(self, household_size, location=ST_LOUIS_CITY, assets=Decimal("500")):
        zipcode, county = location
        return self.make_screen(household_size, zipcode=zipcode, county=county, household_assets=assets)

    def add_person(self, screen, relationship, born, **kwargs):
        """A member stated by the (year, month) the scenario gives."""
        return self.add_member(screen, relationship, age=None, birth_year_month=date(born[0], born[1], 1), **kwargs)

    def calc(self, screen):
        # The screen's own missing fields, so a null the screener would send withholds
        # the program here too.
        return self.calculate(screen, missing=screen.missing_fields())

    def assert_eligible(self, screen, value):
        eligibility = self.calc(screen)
        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, value)
        return eligibility

    def assert_ineligible(self, screen):
        eligibility = self.calc(screen)
        self.assertFalse(eligibility.eligible)
        return eligibility

    def baseline(
        self,
        location=ST_LOUIS_CITY,
        wages=2_000,
        child_born=(2023, 3),
        child_relationship="child",
        person_3_relationship="spouse",
        person_3_born=(1990, 6),
        person_4_born=(2011, 3),
        assets=Decimal("500"),
        child_kwargs=None,
    ):
        """Scenario 1's household, which most scenarios perturb: a working head, the
        eligible child, a spouse with no income, and a 15-year-old who counts toward
        the Eligibility Unit without being an eligible child."""
        screen = self.build(4, location=location, assets=assets)
        self.head = self.add_person(screen, "headOfHousehold", (1991, 3))
        if wages:
            self.add_income(self.head, wages)
        self.child = self.add_person(screen, child_relationship, child_born, **(child_kwargs or {}))
        self.person_3 = self.add_person(screen, person_3_relationship, person_3_born)
        self.person_4 = self.add_person(screen, "child", person_4_born)
        return screen


class TestClassAttributes(MoChildCareSubsidyTestCase):
    def test_is_a_plain_program_calculator(self):
        self.assertTrue(issubclass(MoChildCareSubsidy, ProgramCalculator))

    def test_registered_under_mo_ccs(self):
        self.assertIs(build("programs.programs", ProgramCalculator).get("mo_ccs"), MoChildCareSubsidy)

    def test_dependencies(self):
        self.assertEqual(
            MoChildCareSubsidy.dependencies, ["age", "relationship", "county", "income_amount", "income_frequency"]
        )

    def test_household_assets_and_household_size_are_not_dependencies(self):
        # The net-worth test never screens out, and unit size is read off the roster.
        self.assertNotIn("household_assets", MoChildCareSubsidy.dependencies)
        self.assertNotIn("household_size", MoChildCareSubsidy.dependencies)

    def test_child_relationships_include_related_other(self):
        self.assertEqual(
            set(MoChildCareSubsidy.child_relationships),
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

    def test_proxy_constants(self):
        self.assertEqual(MoChildCareSubsidy.CARE_DAYS_PER_MONTH, 21)
        self.assertEqual(MoChildCareSubsidy.SCHOOL_YEAR_FULL_DAYS_PER_MONTH, Decimal("0.625"))
        self.assertEqual(MoChildCareSubsidy.SCHOOL_YEAR_MONTHS, (9, 10, 11, 12, 1, 2, 3, 4))
        self.assertEqual(MoChildCareSubsidy.BASE_AGE_LIMIT, 13)
        self.assertEqual(MoChildCareSubsidy.SPECIAL_NEEDS_AGE_LIMIT, 18)


class TestPublishedTables(MoChildCareSubsidyTestCase):
    def test_every_table_covers_sizes_one_through_twenty(self):
        for table in (CHART_MAXIMUM, SMI_85_PERCENT, FEE_BAND_TOPS):
            self.assertEqual(sorted(table), list(range(1, 21)))

    def test_band_tops_ascend_and_close_under_the_chart_maximum(self):
        # A band out of order would shadow the ones after it; the $5.00 band's top is
        # the chart maximum, so every other top must sit below it.
        for size, tops in FEE_BAND_TOPS.items():
            with self.subTest(size=size):
                self.assertEqual(len(tops), len(DAILY_FEES))
                self.assertEqual(list(tops), sorted(tops))
                self.assertLess(tops[-1], CHART_MAXIMUM[size])

    def test_chart_binds_through_sixteen_and_smi_from_seventeen(self):
        for size in range(1, 17):
            self.assertLess(CHART_MAXIMUM[size], SMI_85_PERCENT[size])
        for size in range(17, 21):
            self.assertGreater(CHART_MAXIMUM[size], SMI_85_PERCENT[size])

    def test_county_lists_cover_all_115_entries_without_overlap(self):
        self.assertEqual(sum(len(counties) for counties in COUNTY_REGIONS.values()), 115)
        self.assertEqual(len(REGION_BY_COUNTY), 115)

    def test_every_mo_screener_county_matches_a_grouping(self):
        # No MFB county may fall to the Region 5 default.
        counties = {county for mapping in MoConfigurationData.counties_by_zipcode.values() for county in mapping}
        unmatched = [county for county in counties if normalize_county(county) not in REGION_BY_COUNTY]
        self.assertEqual(unmatched, [])


class TestCountyNormalization(MoChildCareSubsidyTestCase):
    def test_strips_suffix_and_periods(self):
        self.assertEqual(normalize_county("St. Charles County"), "st charles")
        self.assertEqual(normalize_county("St. Louis City"), "st louis city")

    def test_ste_is_read_as_sainte_before_casefolding(self):
        self.assertEqual(normalize_county("Ste. Genevieve County"), "sainte genevieve")
        self.assertIn(normalize_county("Ste. Genevieve County"), REGION_BY_COUNTY)

    def test_casefolds(self):
        self.assertEqual(normalize_county("DeKalb County"), "dekalb")

    def test_st_louis_county_and_city_are_both_region_1(self):
        self.assertEqual(REGION_BY_COUNTY[normalize_county("St. Louis County")], REGION_1)
        self.assertEqual(REGION_BY_COUNTY[normalize_county("St. Louis City")], REGION_1)

    def test_unmatched_county_takes_region_5(self):
        screen = self.baseline(location=("00000", "Nowhere County"))
        self.assertEqual(self.make_calculator(screen).region(), REGION_5)


class TestNonScenarioBranches(MoChildCareSubsidyTestCase):
    def test_assets_above_the_limit_do_not_screen_out(self):
        # Data Gap 19: gross assets cannot establish a net-worth fail without debts.
        self.assert_eligible(self.baseline(assets=Decimal("5000000")), 11_340)

    def test_null_assets_do_not_screen_out(self):
        self.assert_eligible(self.baseline(assets=None), 11_340)

    def test_null_county_withholds_the_program(self):
        screen = self.baseline(location=("63101", None))
        with self.assertRaises(DependencyError):
            self.calc(screen)

    def test_null_frequency_medical_expense_is_skipped_rather_than_raising(self):
        screen = self.baseline(location=GREENE, wages=4_100)
        self.add_expense(self.head, 200, "medical", frequency=None)
        self.assert_ineligible(screen)

    def test_null_amount_medical_expense_is_skipped_rather_than_raising(self):
        screen = self.baseline(location=GREENE, wages=4_100)
        self.add_expense(self.head, None, "medical")
        self.assert_ineligible(screen)

    def test_income_message_reports_annual_figures(self):
        # The message reads "per year", so the monthly test is annualized for display.
        eligibility = self.assert_ineligible(self.baseline(location=GREENE, wages=4_020))
        self.assertEqual(eligibility.fail_messages[0][1], " $48240 ")
        self.assertEqual(eligibility.fail_messages[0][3], " $48228")

    def test_null_birth_month_five_year_old_is_held_at_preschool(self):
        screen = self.baseline()
        self.child.birth_year_month = None
        self.child.age = 5
        self.child.save()
        self.assert_eligible(screen, 11_340)

    def test_null_birth_month_six_year_old_is_not_held(self):
        screen = self.baseline()
        self.child.birth_year_month = None
        self.child.age = 6
        self.child.save()
        self.assert_eligible(screen, 6_217)

    def test_school_year_hold_follows_the_child_through_june(self):
        # Born August 2020, the child was 4 on 2025-07-31, so stays Preschool for the
        # school year running to 2026-07-31 even though `calc_age` is 5 by June.
        self.evaluation_date = date(2026, 6, 15)
        self.assert_eligible(self.baseline(child_born=(2020, 8)), 11_340)

    def test_tanf_with_an_excluded_ssi_stream_is_not_the_only_income(self):
        # SSI is excluded from the income test but is still a second source of income,
        # so the daily fee applies: $1,000 at size 4 is the $0.75 band.
        screen = self.baseline(wages=0)
        self.add_income(self.head, 1_000, income_type="cashAssistance")
        # On the spouse: SSI on a child would make them a special-needs eligible child.
        self.add_income(self.person_3, 700, income_type="sSI")
        self.assert_eligible(screen, 12_411)

    def test_tanf_with_a_childs_excluded_earnings_is_not_the_only_income(self):
        screen = self.baseline(wages=0)
        self.add_income(self.head, 1_000, income_type="cashAssistance")
        self.add_income(self.person_4, 200)
        self.assert_eligible(screen, 12_411)

    def test_tanf_alongside_wages_is_not_the_only_income(self):
        screen = self.baseline(wages=500)
        self.add_income(self.head, 500, income_type="cashAssistance")
        # $1,000 at size 4 is the $0.75 band.
        self.assert_eligible(screen, 12_411)

    def test_waived_only_household_pays_no_annual_fee(self):
        # $700 at size 4 is in the $1.00-per-year band, but the only child is waived.
        self.assert_eligible(self.baseline(wages=700, child_kwargs={"disabled": True}), 12_600)

    def test_unit_size_above_twenty_takes_the_size_twenty_row(self):
        screen = self.baseline()
        for _ in range(18):
            self.add_person(screen, "child", (2010, 3))
        self.assertEqual(self.make_calculator(screen).unit_size(), 20)

    def test_hourly_wages_are_quantised_to_the_cent(self):
        screen = self.baseline(location=GREENE, wages=0)
        IncomeStream.objects.create(
            screen=screen,
            household_member=self.head,
            type="wages",
            amount=Decimal("20"),
            frequency="hourly",
            hours_worked=20,
        )
        income = self.make_calculator(screen).adjusted_monthly_income()
        self.assertEqual(income, income.quantize(Decimal("0.01")))

    def test_no_member_values(self):
        eligibility = self.calc(self.baseline())
        self.assertTrue(all(member.value == 0 for member in eligibility.eligible_members))
        self.assertEqual(eligibility.household_value, 11_340)


class TestSpecScenarios(MoChildCareSubsidyTestCase):
    """One test per ``specs/mo.md`` Test Scenario, asserting the annual value."""

    def test_scenario_1_region_1_preschool(self):
        self.assert_eligible(self.baseline(), 11_340)

    def test_scenario_2_region_2_preschool(self):
        self.assert_eligible(self.baseline(location=FRANKLIN), 8_064)

    def test_scenario_3_region_3_preschool(self):
        self.assert_eligible(self.baseline(location=GREENE), 8_820)

    def test_scenario_4_region_4_preschool(self):
        self.assert_eligible(self.baseline(location=PHELPS), 6_930)

    def test_scenario_5_region_5_preschool(self):
        self.assert_eligible(self.baseline(location=TEXAS), 6_552)

    def test_scenario_6_income_at_the_ceiling(self):
        self.assert_eligible(self.baseline(location=GREENE, wages=4_019), 8_820)

    def test_scenario_7_income_one_dollar_over_the_ceiling(self):
        self.assert_ineligible(self.baseline(location=GREENE, wages=4_020))

    def test_scenario_8_medical_deduction_brings_income_under(self):
        screen = self.baseline(location=GREENE, wages=4_100)
        self.add_expense(self.head, 200, "medical")
        self.assert_eligible(screen, 8_820)

    def test_scenario_9_same_income_without_the_deduction(self):
        self.assert_ineligible(self.baseline(location=GREENE, wages=4_100))

    def test_scenario_10_ssi_is_excluded(self):
        screen = self.baseline(location=GREENE, wages=3_900)
        self.add_income(self.person_3, 700, income_type="sSI")
        self.assert_eligible(screen, 8_820)

    def test_scenario_11_school_year_hold_born_august(self):
        self.assert_eligible(self.baseline(child_born=(2021, 8)), 11_340)

    def test_scenario_12_hold_boundary_born_july(self):
        self.assert_eligible(self.baseline(child_born=(2021, 7)), 6_217)

    def test_scenario_13_region_3_hold_born_august(self):
        self.assert_eligible(self.baseline(location=GREENE, child_born=(2021, 8)), 8_820)

    def test_scenario_14_region_3_school_age_born_july(self):
        self.assert_eligible(self.baseline(location=GREENE, child_born=(2021, 7)), 8_288)

    def test_scenario_15_under_18_earnings_excluded(self):
        screen = self.baseline(location=GREENE, wages=3_900, person_4_born=(2008, 10))
        self.add_income(self.person_4, 400)
        self.assert_eligible(screen, 8_820)

    def test_scenario_16_earnings_counted_at_18(self):
        screen = self.baseline(location=GREENE, wages=3_900, person_4_born=(2008, 9))
        self.add_income(self.person_4, 400)
        self.assert_ineligible(screen)

    def test_scenario_17_annual_wage_at_the_ceiling(self):
        screen = self.baseline(location=GREENE, wages=0)
        self.add_income(self.head, 48_228, frequency="yearly")
        self.assert_eligible(screen, 8_820)

    def test_scenario_18_caregiver_relative_as_head(self):
        screen = self.build(3)
        head = self.add_person(screen, "headOfHousehold", (1985, 3))
        self.add_income(head, 2_000)
        self.add_person(screen, "relatedOther", (2023, 3))
        self.add_person(screen, "relatedOther", (2011, 3))
        self.assert_eligible(screen, 11_340)

    def test_scenario_19_member_outside_the_accepted_set(self):
        self.assert_ineligible(self.baseline(child_relationship="roommate"))

    def test_scenario_20_assets_at_the_limit(self):
        self.assert_eligible(self.baseline(assets=Decimal("1000000")), 11_340)

    def test_scenario_21_top_of_the_4_dollar_band(self):
        self.assert_eligible(self.baseline(location=GREENE, wages=1_764), 9_072)

    def test_scenario_22_bottom_of_the_5_dollar_band(self):
        self.assert_eligible(self.baseline(location=GREENE, wages=1_765), 8_820)

    def test_scenario_23_ssi_child_fee_waived(self):
        screen = self.baseline()
        self.add_income(self.child, 700, income_type="sSI")
        self.assert_eligible(screen, 12_600)

    def test_scenario_24_waiver_is_per_child(self):
        screen = self.baseline(person_3_relationship="child", person_3_born=(2023, 3))
        self.add_income(self.child, 700, income_type="sSI")
        self.assert_eligible(screen, 23_940)

    def test_scenario_25_income_in_the_annual_dollar_band(self):
        self.assert_eligible(self.baseline(wages=802), 12_599)

    def test_scenario_26_only_income_is_temporary_assistance(self):
        screen = self.baseline(wages=0)
        self.add_income(self.head, 1_000, income_type="cashAssistance")
        self.assert_eligible(screen, 12_599)

    def test_scenario_27_annual_fee_charged_once(self):
        self.assert_eligible(
            self.baseline(wages=700, person_3_relationship="child", person_3_born=(2023, 3)),
            25_199,
        )

    def test_scenario_28_waiver_outranks_the_annual_fee(self):
        screen = self.baseline(wages=700)
        self.add_income(self.child, 700, income_type="sSI")
        self.assert_eligible(screen, 12_600)

    def test_scenario_29_mixed_household_in_the_annual_band(self):
        screen = self.baseline(wages=700, person_3_relationship="child", person_3_born=(2023, 3))
        self.add_income(self.child, 700, income_type="sSI")
        self.assert_eligible(screen, 25_199)

    def test_scenario_30_the_50_cent_band(self):
        self.assert_eligible(self.baseline(wages=803), 12_474)

    def test_scenario_31_child_aged_12(self):
        self.assert_eligible(self.baseline(child_born=(2013, 10)), 6_217)

    def test_scenario_32_child_aged_13(self):
        self.assert_ineligible(self.baseline(child_born=(2013, 9)))

    def test_scenario_33_unit_size_changes_the_band(self):
        screen = self.build(2, location=GREENE)
        head = self.add_person(screen, "headOfHousehold", (1991, 3))
        self.add_income(head, 900)
        self.add_person(screen, "child", (2023, 3))
        self.assert_eligible(screen, 9_576)

    def test_scenario_34_disability_waiver(self):
        self.assert_eligible(self.baseline(child_kwargs={"disabled": True}), 12_600)

    def test_scenario_35_school_age_outside_the_school_year(self):
        self.evaluation_date = date(2026, 8, 15)
        self.assert_eligible(self.baseline(child_born=(2021, 7)), 7_812)

    def test_scenario_36_special_needs_extension_past_13(self):
        self.assert_eligible(
            self.baseline(location=GREENE, child_born=(2012, 3), child_kwargs={"disabled": True}),
            9_145,
        )

    def test_scenario_37_roommate_counts_toward_unit_size(self):
        screen = self.build(3, location=GREENE)
        head = self.add_person(screen, "headOfHousehold", (1991, 3))
        self.add_income(head, 900)
        self.add_person(screen, "child", (2023, 3))
        self.add_person(screen, "roommate", (1988, 3))
        self.assert_eligible(screen, 9_891)

    def test_scenario_38_daily_fee_charged_per_child(self):
        self.assert_eligible(
            self.baseline(person_3_relationship="child", person_3_born=(2023, 3)),
            22_680,
        )

    def test_scenario_39_special_needs_extension_upper_edge(self):
        self.assert_eligible(self.baseline(child_born=(2008, 10), child_kwargs={"disabled": True}), 7_074)

    def test_scenario_40_one_month_past_the_extension(self):
        self.assert_ineligible(self.baseline(child_born=(2008, 9), child_kwargs={"disabled": True}))

    def test_scenario_41_school_year_pattern_in_april(self):
        self.evaluation_date = date(2026, 4, 15)
        self.assert_eligible(self.baseline(child_born=(2019, 3)), 6_217)

    def test_scenario_42_school_year_pattern_lapses_in_may(self):
        self.evaluation_date = date(2026, 5, 1)
        self.assert_eligible(self.baseline(child_born=(2019, 3)), 7_812)

    def test_scenario_43_just_turned_2_is_preschool(self):
        self.assert_eligible(self.baseline(child_born=(2024, 9)), 11_340)

    def test_scenario_44_one_month_younger_is_infant(self):
        self.assert_eligible(self.baseline(child_born=(2024, 10)), 22_932)

    def test_scenario_45_region_2_infant(self):
        self.assert_eligible(self.baseline(location=FRANKLIN, child_born=(2025, 3)), 16_783)

    def test_scenario_46_region_3_infant(self):
        self.assert_eligible(self.baseline(location=GREENE, child_born=(2025, 3)), 18_648)

    def test_scenario_47_region_4_infant(self):
        self.assert_eligible(self.baseline(location=PHELPS, child_born=(2025, 3)), 13_482)

    def test_scenario_48_the_1_dollar_band(self):
        self.assert_eligible(self.baseline(wages=1_200), 12_348)

    def test_scenario_49_the_3_dollar_band(self):
        self.assert_eligible(self.baseline(wages=1_500), 11_844)

    def test_scenario_50_unit_of_five(self):
        screen = self.baseline(wages=1_600)
        self.add_person(screen, "child", (2010, 3))
        self.assert_eligible(screen, 12_096)

    def test_scenario_51_st_louis_county_is_region_1(self):
        self.assert_eligible(self.baseline(location=ST_LOUIS_COUNTY), 11_340)

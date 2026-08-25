"""
Unit tests for the Missouri Nurse-Family Partnership (NFP) calculator.

Each of the nine scenarios in spec.md maps to a test below, plus coverage for
every branch of the calculator: the county gate across all three provider
regions, the 185% FPL boundary in both directions, the pregnancy gate, and the
per-member value semantics.

Unlike the KS sibling, MO does not gate on first-time-parent status: the screener
cannot attribute a child to a specific parent, so the spec applies the inclusive
default. `test_existing_child_does_not_disqualify` locks that decision in.
"""

from django.test import TestCase
from programs.programs.white_labels.mo.nfp.calculator import MoNurseFamilyPartnership
from screener.models import Screen, HouseholdMember, IncomeStream, WhiteLabel
from programs.models import Program, FederalPoveryLimit
from programs.util import Dependencies

EXPECTED_VALUE = 6_000 / 2.5  # $2,400/year, per eligible member

# 2026 FPL: size 1 = 15,960; size 3 = 27,320; size 4 = 33,000
FPL_185_SIZE_1 = 29_526  # 15,960 * 1.85, exactly
FPL_185_SIZE_3 = 50_542  # 27,320 * 1.85, exactly


class TestMoNurseFamilyPartnership(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mo_white_label = WhiteLabel.objects.create(name="Missouri", code="mo", state_code="MO")
        cls.fpl_year = FederalPoveryLimit.objects.create(year="2026", period="2026")
        cls.program = Program.objects.new_program(white_label="mo", name_abbreviated="mo_nfp")
        cls.program.year = cls.fpl_year
        cls.program.save()

    def make_screen(self, county="St. Louis County", household_size=1, zipcode="63121"):
        return Screen.objects.create(
            agree_to_tos=True,
            zipcode=zipcode,
            county=county,
            household_size=household_size,
            white_label=self.mo_white_label,
            completed=False,
        )

    def add_member(
        self,
        screen,
        relationship="headOfHousehold",
        age=25,
        pregnant=False,
        monthly_income=0,
        yearly_income=0,
        income_type="wages",
    ):
        member = HouseholdMember.objects.create(
            screen=screen,
            relationship=relationship,
            age=age,
            pregnant=pregnant,
            has_income=(monthly_income > 0 or yearly_income > 0),
        )
        if monthly_income > 0:
            IncomeStream.objects.create(
                screen=screen,
                household_member=member,
                type=income_type,
                amount=monthly_income,
                frequency="monthly",
            )
        if yearly_income > 0:
            IncomeStream.objects.create(
                screen=screen,
                household_member=member,
                type=income_type,
                amount=yearly_income,
                frequency="yearly",
            )
        return member

    def calculator(self, screen):
        return MoNurseFamilyPartnership(screen, self.program, {}, Dependencies())

    def eligible_member_count(self, eligibility):
        return sum(1 for m in eligibility.eligible_members if m.eligible)

    # ------------------------------------------------------------------ #
    # Class attributes / registration
    # ------------------------------------------------------------------ #
    def test_class_attributes(self):
        self.assertEqual(MoNurseFamilyPartnership.program_code, "mo_nfp")
        self.assertEqual(MoNurseFamilyPartnership.fpl_percent, 1.85)
        # Value is per eligible member, not per household (see spec Scenario 9).
        self.assertEqual(MoNurseFamilyPartnership.member_amount, EXPECTED_VALUE)
        self.assertEqual(MoNurseFamilyPartnership.amount, 0)

    def test_registered_in_calculator_registry(self):
        from programs.framework.base import ProgramCalculator
        from programs.framework.registry import build

        registry = build("programs.programs", ProgramCalculator)
        self.assertIs(registry["mo_nfp"], MoNurseFamilyPartnership)

    def test_eligible_counties_are_the_14_served_jurisdictions(self):
        self.assertEqual(
            sorted(MoNurseFamilyPartnership.eligible_counties),
            [
                "Butler County",
                "Cass County",
                "Clay County",
                "Dunklin County",
                "Jackson County",
                "Johnson County",
                "Lafayette County",
                "Pemiscot County",
                "Platte County",
                "Ray County",
                "Ripley County",
                "St. Louis City",
                "St. Louis County",
                "Wayne County",
            ],
        )

    def test_eligible_counties_match_the_mo_screener_crosswalk(self):
        """Every gated county must be a name the MO screener actually sends.

        A bare name (e.g. "Jackson") or a wrong suffix would silently never match
        `Screen.county`, making the program unreachable in that county.
        """
        from configuration.white_labels.mo import MoConfigurationData

        valid_names = set()
        for county_map in MoConfigurationData.counties_by_zipcode.values():
            valid_names.update(county_map.keys())

        for county in MoNurseFamilyPartnership.eligible_counties:
            self.assertIn(county, valid_names, f"'{county}' is not a county the MO screener sends")

    # ------------------------------------------------------------------ #
    # Scenario 1: golden path — pregnant, low income, St. Louis County
    # ------------------------------------------------------------------ #
    def test_scenario_1_golden_path_st_louis_county(self):
        screen = self.make_screen(county="St. Louis County", zipcode="63121")
        self.add_member(screen, age=24, pregnant=True, monthly_income=1_500)
        eligibility = self.calculator(screen).calc()
        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, EXPECTED_VALUE)

    # ------------------------------------------------------------------ #
    # Scenario 2: Kansas City region — Jackson County
    # ------------------------------------------------------------------ #
    def test_scenario_2_kansas_city_region_jackson_county(self):
        screen = self.make_screen(county="Jackson County", zipcode="64106")
        self.add_member(screen, age=23, pregnant=True, monthly_income=1_200)
        eligibility = self.calculator(screen).calc()
        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, EXPECTED_VALUE)

    # ------------------------------------------------------------------ #
    # Scenario 3: Southeast region — Butler County
    # ------------------------------------------------------------------ #
    def test_scenario_3_southeast_region_butler_county(self):
        screen = self.make_screen(county="Butler County", zipcode="63901")
        self.add_member(screen, age=22, pregnant=True, monthly_income=900)
        eligibility = self.calculator(screen).calc()
        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, EXPECTED_VALUE)

    # ------------------------------------------------------------------ #
    # Scenario 4: not pregnant -> not eligible, despite valid county/income
    # ------------------------------------------------------------------ #
    def test_scenario_4_not_pregnant_not_eligible(self):
        screen = self.make_screen(county="St. Louis City", household_size=2, zipcode="63101")
        self.add_member(screen, relationship="headOfHousehold", age=30, monthly_income=2_500)
        self.add_member(screen, relationship="spouse", age=28)
        eligibility = self.calculator(screen).calc()
        self.assertFalse(eligibility.eligible)
        self.assertEqual(self.eligible_member_count(eligibility), 0)

    # ------------------------------------------------------------------ #
    # Scenario 5: outside all three provider footprints (Greene County)
    # ------------------------------------------------------------------ #
    def test_scenario_5_outside_service_area_greene_county(self):
        screen = self.make_screen(county="Greene County", zipcode="65806")
        self.add_member(screen, age=24, pregnant=True, monthly_income=1_200)
        self.assertFalse(self.calculator(screen).calc().eligible)

    # ------------------------------------------------------------------ #
    # Scenario 6: income exactly at 185% FPL for a household of 1 -> eligible.
    # 15,960 * 1.85 = 29,526 exactly, so the boundary must pass (`<=`, not `<`).
    # ------------------------------------------------------------------ #
    def test_scenario_6_income_exactly_at_fpl_boundary(self):
        screen = self.make_screen(county="St. Louis County", zipcode="63121")
        self.add_member(screen, age=25, pregnant=True, yearly_income=FPL_185_SIZE_1)
        eligibility = self.calculator(screen).calc()
        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, EXPECTED_VALUE)

    def test_income_boundary_via_monthly_income(self):
        """$2,460.50/month annualizes to exactly $29,526 — the spec's stated input."""
        screen = self.make_screen(county="St. Louis County", zipcode="63121")
        self.add_member(screen, age=25, pregnant=True, monthly_income=2_460.50)
        self.assertTrue(self.calculator(screen).calc().eligible)

    # ------------------------------------------------------------------ #
    # Scenario 7: income just above 185% FPL -> not eligible
    # ------------------------------------------------------------------ #
    def test_scenario_7_income_just_above_fpl_boundary(self):
        screen = self.make_screen(county="St. Louis County", zipcode="63121")
        self.add_member(screen, age=25, pregnant=True, monthly_income=2_500)  # $30,000/yr
        self.assertFalse(self.calculator(screen).calc().eligible)

    def test_income_one_dollar_above_boundary_not_eligible(self):
        screen = self.make_screen(county="St. Louis County", zipcode="63121")
        self.add_member(screen, age=25, pregnant=True, yearly_income=FPL_185_SIZE_1 + 1)
        self.assertFalse(self.calculator(screen).calc().eligible)

    # ------------------------------------------------------------------ #
    # Scenario 8: mixed household, one pregnant member -> eligible for that member
    # Household of 3 earning $43,200/yr, under the $50,542 limit.
    # ------------------------------------------------------------------ #
    def test_scenario_8_mixed_household_one_eligible_member(self):
        screen = self.make_screen(county="St. Louis County", household_size=3, zipcode="63121")
        self.add_member(screen, relationship="headOfHousehold", age=28, monthly_income=2_400)
        self.add_member(screen, relationship="spouse", age=26, pregnant=True)
        self.add_member(screen, relationship="other", age=60, monthly_income=1_200, income_type="sSRetirement")

        eligibility = self.calculator(screen).calc()
        self.assertTrue(eligibility.eligible)
        self.assertEqual(self.eligible_member_count(eligibility), 1)
        self.assertEqual(eligibility.value, EXPECTED_VALUE)
        # Confirm the household income assumption the scenario rests on.
        self.assertEqual(int(screen.calc_gross_income("yearly", ["all"])), 43_200)
        self.assertLess(43_200, FPL_185_SIZE_3)

    # ------------------------------------------------------------------ #
    # Scenario 9: two pregnant members -> $2,400 each, $4,800 total.
    # This is the reason MO uses `member_amount` where CO/IL/KS use `amount`.
    # ------------------------------------------------------------------ #
    def test_scenario_9_two_pregnant_members_value_is_per_member(self):
        screen = self.make_screen(county="St. Louis City", household_size=4, zipcode="63101")
        self.add_member(screen, relationship="headOfHousehold", age=25, pregnant=True, monthly_income=1_500)
        self.add_member(screen, relationship="other", age=21, pregnant=True)
        self.add_member(screen, relationship="spouse", age=27, monthly_income=2_800)
        self.add_member(screen, relationship="other", age=2)

        eligibility = self.calculator(screen).calc()
        self.assertTrue(eligibility.eligible)
        self.assertEqual(self.eligible_member_count(eligibility), 2)
        self.assertEqual(eligibility.value, EXPECTED_VALUE * 2)  # $4,800

    # ------------------------------------------------------------------ #
    # County gate — every served county, and a rejected one per region
    # ------------------------------------------------------------------ #
    def test_all_served_counties_are_eligible(self):
        for county in MoNurseFamilyPartnership.eligible_counties:
            with self.subTest(county=county):
                screen = self.make_screen(county=county)
                self.add_member(screen, age=24, pregnant=True, monthly_income=1_000)
                self.assertTrue(self.calculator(screen).calc().eligible)

    def test_unserved_counties_are_not_eligible(self):
        # Boone (Columbia) and Greene (Springfield) are outside all three
        # footprints. Cape Girardeau and Stoddard were on the outdated 2024
        # Southeast map that the reviewed spec dropped, so they must not pass.
        for county in ["Boone County", "Greene County", "Cape Girardeau County", "Stoddard County", "Jasper County"]:
            with self.subTest(county=county):
                screen = self.make_screen(county=county)
                self.add_member(screen, age=24, pregnant=True, monthly_income=1_000)
                self.assertFalse(self.calculator(screen).calc().eligible)

    # ------------------------------------------------------------------ #
    # Data-gap decisions (inclusive default)
    # ------------------------------------------------------------------ #
    def test_existing_child_does_not_disqualify(self):
        """First-time-parent status is a data gap in MO: do not exclude.

        The KS sibling excludes any household with a child of the head. MO
        deliberately does not, because the screener cannot tell whose child it is.
        """
        screen = self.make_screen(county="St. Louis County", household_size=2, zipcode="63121")
        self.add_member(screen, relationship="headOfHousehold", age=29, pregnant=True, monthly_income=1_200)
        self.add_member(screen, relationship="child", age=4)
        self.assertTrue(self.calculator(screen).calc().eligible)

    def test_pregnant_member_with_no_income_is_eligible(self):
        screen = self.make_screen(county="Ray County", zipcode="64085")
        self.add_member(screen, age=20, pregnant=True)
        eligibility = self.calculator(screen).calc()
        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, EXPECTED_VALUE)

    def test_only_pregnant_members_receive_value(self):
        screen = self.make_screen(county="Jackson County", household_size=2, zipcode="64106")
        self.add_member(screen, relationship="headOfHousehold", age=30, pregnant=True, monthly_income=1_000)
        self.add_member(screen, relationship="spouse", age=32)

        eligibility = self.calculator(screen).calc()
        values = {m.member.relationship: m.value for m in eligibility.eligible_members}
        self.assertEqual(values["headOfHousehold"], EXPECTED_VALUE)
        self.assertEqual(values["spouse"], 0)

    # ------------------------------------------------------------------ #
    # Messages
    # ------------------------------------------------------------------ #
    def test_failing_county_produces_a_location_message(self):
        screen = self.make_screen(county="Greene County", zipcode="65806")
        self.add_member(screen, age=24, pregnant=True, monthly_income=1_000)
        eligibility = self.calculator(screen).calc()
        self.assertTrue(len(eligibility.fail_messages) >= 1)

    def test_failing_income_produces_an_income_message(self):
        screen = self.make_screen(county="St. Louis County", zipcode="63121")
        self.add_member(screen, age=24, pregnant=True, monthly_income=5_000)
        eligibility = self.calculator(screen).calc()
        self.assertTrue(len(eligibility.fail_messages) >= 1)

    # ------------------------------------------------------------------ #
    # Dependencies
    # ------------------------------------------------------------------ #
    def test_dependencies_cover_every_screener_field_read(self):
        for dependency in ("pregnant", "county", "household_size", "income_amount", "income_frequency"):
            self.assertIn(dependency, MoNurseFamilyPartnership.dependencies)

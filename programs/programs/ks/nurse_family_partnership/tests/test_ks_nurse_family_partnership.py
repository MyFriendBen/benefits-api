"""
Unit tests for the Kansas Nurse-Family Partnership (NFP) calculator.

Each test maps to a scenario in spec.md. Two scenarios diverge from the spec's
stated expectation due to deliberate implementation decisions (documented inline
and in spec.md):

- Scenario 9 (mixed household with a partner's child present): the screener has
  no per-member child attribution, so a household-level "no existing children"
  gate returns NOT eligible. This is the intended trade-off for correctly
  excluding Scenario 8.
- Scenario 10 (two pregnant members): NFP value is stored household-level
  (matching co_nfp / il_nfp), so the household value is $2,400 (counted once),
  not $4,800. The household is still correctly flagged eligible.

- Scenario 7 (already enrolled): suppression of applicants who already receive
  NFP is handled by the framework (`show_on_current_benefits` / `already_has` at
  the view layer), not by this calculator. The calculator itself still returns
  eligible; the test asserts that and verifies the framework signal
  (`screen.has_benefit`).
"""

from django.test import TestCase
from programs.programs.ks import ks_calculators
from programs.programs.ks.nurse_family_partnership.calculator import KsNurseFamilyPartnership
from screener.models import Screen, HouseholdMember, IncomeStream, WhiteLabel
from screener.serializers import _write_current_benefits
from programs.models import Program, FederalPoveryLimit
from programs.util import Dependencies

EXPECTED_VALUE = 6_000 / 2.5  # $2,400/year


class TestKsNurseFamilyPartnership(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ks_white_label = WhiteLabel.objects.create(name="Kansas", code="ks", state_code="KS")
        cls.fpl_year = FederalPoveryLimit.objects.create(year="2026", period="2026")
        cls.program = Program.objects.new_program(white_label="ks", name_abbreviated="ks_nurse_family_partnership")
        cls.program.year = cls.fpl_year
        cls.program.save()

    def make_screen(self, county="Shawnee County", household_size=1, zipcode="66604"):
        return Screen.objects.create(
            agree_to_tos=True,
            zipcode=zipcode,
            county=county,
            household_size=household_size,
            white_label=self.ks_white_label,
            completed=False,
        )

    def add_member(self, screen, relationship="headOfHousehold", age=25, pregnant=False, monthly_income=0):
        member = HouseholdMember.objects.create(
            screen=screen,
            relationship=relationship,
            age=age,
            pregnant=pregnant,
            has_income=monthly_income > 0,
        )
        if monthly_income > 0:
            IncomeStream.objects.create(
                screen=screen,
                household_member=member,
                type="wages",
                amount=monthly_income,
                frequency="monthly",
            )
        return member

    def calculator(self, screen):
        return KsNurseFamilyPartnership(screen, self.program, {}, Dependencies())

    def eligible_member_count(self, eligibility):
        return sum(1 for m in eligibility.eligible_members if m.eligible)

    # ------------------------------------------------------------------ #
    # Class attributes / registration
    # ------------------------------------------------------------------ #
    def test_registered_in_ks_calculators(self):
        self.assertIn("ks_nurse_family_partnership", ks_calculators)
        self.assertIs(ks_calculators["ks_nurse_family_partnership"], KsNurseFamilyPartnership)

    def test_class_attributes(self):
        self.assertEqual(KsNurseFamilyPartnership.fpl_percent, 1.71)
        self.assertEqual(KsNurseFamilyPartnership.amount, EXPECTED_VALUE)
        self.assertEqual(
            sorted(KsNurseFamilyPartnership.eligible_counties),
            ["Johnson County", "Shawnee County"],
        )

    # ------------------------------------------------------------------ #
    # Scenario 1: clearly eligible first-time pregnant mother, Shawnee
    # ------------------------------------------------------------------ #
    def test_scenario_1_eligible_shawnee(self):
        screen = self.make_screen(county="Shawnee County", zipcode="66604")
        self.add_member(screen, age=22, pregnant=True, monthly_income=1_200)
        eligibility = self.calculator(screen).calc()
        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, EXPECTED_VALUE)

    # ------------------------------------------------------------------ #
    # Scenario 2: young (17) first-time pregnant, low income, Shawnee
    # ------------------------------------------------------------------ #
    def test_scenario_2_young_pregnant_eligible(self):
        screen = self.make_screen(county="Shawnee County", zipcode="66612")
        self.add_member(screen, age=17, pregnant=True, monthly_income=1_300)
        eligibility = self.calculator(screen).eligible()
        self.assertTrue(eligibility.eligible)
        # The head is not counted as a "child" (relationship != "child"), so a
        # minor head is not self-disqualified by the num_children proxy.
        self.assertEqual(self.eligible_member_count(eligibility), 1)

    # ------------------------------------------------------------------ #
    # Scenario 3: income just below the 171% FPL threshold -> eligible
    # ------------------------------------------------------------------ #
    def test_scenario_3_income_just_below_threshold(self):
        screen = self.make_screen(county="Shawnee County")
        self.add_member(screen, age=24, pregnant=True, monthly_income=2_200)
        self.assertTrue(self.calculator(screen).eligible().eligible)

    # ------------------------------------------------------------------ #
    # Scenario 4: income exactly at the 171% FPL threshold -> eligible
    # 2026 FPL(1) = 15,960; 171% = 27,291 (int). $2,274/mo = 27,288/yr <= limit
    # ------------------------------------------------------------------ #
    def test_scenario_4_income_at_threshold(self):
        screen = self.make_screen(county="Shawnee County", zipcode="66603")
        self.add_member(screen, age=23, pregnant=True, monthly_income=2_274)
        self.assertTrue(self.calculator(screen).eligible().eligible)

    # ------------------------------------------------------------------ #
    # Scenario 5: income just above the threshold -> not eligible
    # ------------------------------------------------------------------ #
    def test_scenario_5_income_above_threshold(self):
        screen = self.make_screen(county="Shawnee County")
        self.add_member(screen, age=26, pregnant=True, monthly_income=2_800)
        self.assertFalse(self.calculator(screen).eligible().eligible)

    # ------------------------------------------------------------------ #
    # Scenario 6: second distinct ZIP within Shawnee County -> eligible
    # Geography is gated at the county level; ZIP is informational.
    # ------------------------------------------------------------------ #
    def test_scenario_6_second_shawnee_zip(self):
        screen = self.make_screen(county="Shawnee County", zipcode="66602")
        self.add_member(screen, age=24, pregnant=True, monthly_income=1_500)
        self.assertTrue(self.calculator(screen).eligible().eligible)

    # ------------------------------------------------------------------ #
    # Scenario 7: already enrolled in NFP.
    # Suppression is a framework concern, not a calculator condition: the
    # calculator still returns eligible; the view layer flags `already_has`.
    # ------------------------------------------------------------------ #
    def test_scenario_7_already_enrolled_is_framework_handled(self):
        screen = self.make_screen(county="Shawnee County", zipcode="66603")
        self.add_member(screen, age=22, pregnant=True, monthly_income=1_200)
        _write_current_benefits(screen, ["ks_nurse_family_partnership"])

        # Framework signal the results view uses to render "already have this".
        self.assertTrue(screen.has_benefit("ks_nurse_family_partnership"))
        # Calculator itself is unaffected and still reports eligible.
        self.assertTrue(self.calculator(screen).eligible().eligible)

    # ------------------------------------------------------------------ #
    # Scenario 8: second-time mother (existing child in household) -> not eligible
    # ------------------------------------------------------------------ #
    def test_scenario_8_second_time_mother_not_eligible(self):
        screen = self.make_screen(county="Shawnee County", household_size=3, zipcode="66603")
        self.add_member(screen, relationship="headOfHousehold", age=27, pregnant=True, monthly_income=1_800)
        self.add_member(screen, relationship="child", age=2)
        self.assertFalse(self.calculator(screen).eligible().eligible)

    # ------------------------------------------------------------------ #
    # Scenario 9: mixed household with a partner's child present.
    # DIVERGES from spec's "Eligible": the screener cannot attribute the child to
    # the partner, so the household-level first-time-parent gate returns NOT
    # eligible. Documented limitation (see spec.md).
    # ------------------------------------------------------------------ #
    def test_scenario_9_mixed_household_child_present(self):
        screen = self.make_screen(county="Shawnee County", household_size=3, zipcode="66604")
        self.add_member(screen, relationship="headOfHousehold", age=27, pregnant=True, monthly_income=1_200)
        self.add_member(screen, relationship="spouse", age=30, monthly_income=1_800)
        self.add_member(screen, relationship="child", age=4)
        # Known data-model limitation: child in household -> household not eligible.
        self.assertFalse(self.calculator(screen).eligible().eligible)

    # ------------------------------------------------------------------ #
    # Scenario 10: two first-time pregnant women in one household.
    # Both members eligible; household is eligible. Value is HOUSEHOLD-level
    # ($2,400 counted once), NOT $4,800 -- diverges from spec's per-member figure
    # to match the co_nfp / il_nfp precedent. Documented (see spec.md).
    # ------------------------------------------------------------------ #
    def test_scenario_10_two_pregnant_members(self):
        screen = self.make_screen(county="Shawnee County", household_size=3, zipcode="66604")
        self.add_member(screen, relationship="headOfHousehold", age=23, pregnant=True, monthly_income=1_200)
        self.add_member(screen, relationship="sibling", age=20, pregnant=True, monthly_income=800)
        self.add_member(screen, relationship="spouse", age=26, monthly_income=1_500)
        eligibility = self.calculator(screen).calc()
        self.assertTrue(eligibility.eligible)
        self.assertEqual(self.eligible_member_count(eligibility), 2)
        self.assertEqual(eligibility.value, EXPECTED_VALUE)  # household-level, counted once

    # ------------------------------------------------------------------ #
    # Scenario 11: prior stillbirth, no living children -> eligible
    # ------------------------------------------------------------------ #
    def test_scenario_11_stillbirth_no_children_eligible(self):
        screen = self.make_screen(county="Shawnee County", zipcode="66603")
        self.add_member(screen, age=27, pregnant=True, monthly_income=1_200)
        self.assertTrue(self.calculator(screen).eligible().eligible)

    # ------------------------------------------------------------------ #
    # Scenario 12: Johnson County -> eligible (second service area)
    # ------------------------------------------------------------------ #
    def test_scenario_12_johnson_county_eligible(self):
        screen = self.make_screen(county="Johnson County", zipcode="66061")
        self.add_member(screen, age=26, pregnant=True, monthly_income=1_400)
        self.assertTrue(self.calculator(screen).eligible().eligible)

    # ------------------------------------------------------------------ #
    # Scenario 13: outside any service area (Douglas County) -> not eligible
    # ------------------------------------------------------------------ #
    def test_scenario_13_outside_service_area_not_eligible(self):
        screen = self.make_screen(county="Douglas County", zipcode="66044")
        self.add_member(screen, age=24, pregnant=True, monthly_income=1_200)
        self.assertFalse(self.calculator(screen).eligible().eligible)

    # ------------------------------------------------------------------ #
    # Scenario 14: not pregnant -> not eligible
    # ------------------------------------------------------------------ #
    def test_scenario_14_not_pregnant_not_eligible(self):
        screen = self.make_screen(county="Shawnee County")
        self.add_member(screen, age=24, pregnant=False, monthly_income=1_200)
        eligibility = self.calculator(screen).eligible()
        self.assertFalse(eligibility.eligible)
        self.assertEqual(self.eligible_member_count(eligibility), 0)

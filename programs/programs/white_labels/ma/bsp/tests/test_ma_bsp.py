"""
Unit tests for MaBabySteps (MA BabySteps Savings Plan) custom calculator.

Eligibility is evaluated per child: each beneficiary candidate inside the birth-pathway
window (born on or after Jan 1, 2020 and no more than one year ago) is worth a one-time $50
seed deposit. There is no income, asset, insurance, or benefit-receipt gate, and
Massachusetts residency is handled upstream by white-label routing.

Scenario numbers in the test names map to the "Test Scenarios" section of spec.md. Per that
section, every scenario is evaluated as of July 22, 2026, so `Screen.get_reference_date` is
frozen to that date for the whole suite — otherwise the fixed birth months below would drift
out of the branches they are meant to exercise.
"""

from datetime import date
from unittest.mock import patch

from django.test import TestCase

from programs.models import Program
from programs.framework.base import ProgramCalculator
from programs.programs.white_labels.ma.bsp.calculator import MaBabySteps
from programs.util import Dependencies
from screener.models import CurrentBenefit, HouseholdMember, IncomeStream, Screen, WhiteLabel
from programs.framework.pe_dependencies import member

FROZEN_DATE = date(2026, 7, 22)

# The full `relationship` enum, mapped to beneficiary candidacy per the Product-committed
# mapping in spec.md ("Beneficiary/member-identification mapping").
RELATIONSHIP_CANDIDACY = {
    "child": True,
    "fosterChild": True,
    "grandChild": True,
    "sibling": True,
    "other": True,
    "headOfHousehold": False,
    "spouse": False,
    "domesticPartner": False,
    "parent": False,
    "fosterParent": False,
    "stepParent": False,
    "grandParent": False,
}


class MaBabyStepsTestCase(TestCase):
    """Shared fixtures: an MA white label, a program row, and a frozen reference date."""

    @classmethod
    def setUpTestData(cls):
        cls.white_label = WhiteLabel.objects.create(name="Massachusetts", code="ma", state_code="MA")
        cls.program = Program.objects.new_program(white_label="ma", name_abbreviated="ma_bsp")

    def setUp(self):
        patcher = patch.object(Screen, "get_reference_date", lambda _self: FROZEN_DATE)
        patcher.start()
        self.addCleanup(patcher.stop)

    def make_screen(self, zipcode="02101", county="Boston", household_size=2):
        # MA stores city name in the county field (see MFB-548).
        return Screen.objects.create(
            white_label=self.white_label,
            agree_to_tos=True,
            zipcode=zipcode,
            county=county,
            household_size=household_size,
            completed=False,
        )

    def make_member(self, screen, relationship, birth_year_month=None, monthly_income=0):
        age = None
        if birth_year_month is not None:
            age = HouseholdMember.age_from_date(birth_year_month, FROZEN_DATE)

        member = HouseholdMember.objects.create(
            screen=screen,
            relationship=relationship,
            age=age,
            birth_year_month=birth_year_month,
        )

        if monthly_income:
            IncomeStream.objects.create(
                screen=screen,
                household_member=member,
                type="wages",
                amount=monthly_income,
                frequency="monthly",
            )

        return member

    def make_calculator(self, screen):
        return MaBabySteps(screen, self.program, {}, Dependencies())

    def calculate(self, screen):
        calculator = self.make_calculator(screen)
        eligibility = calculator.calc()
        return calculator, eligibility


class TestMaBabyStepsClassAttributes(MaBabyStepsTestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(MaBabySteps, ProgramCalculator))

    def test_member_amount_is_50(self):
        """$50 one-time seed deposit per child — a lump sum, so it is not annualized."""
        self.assertEqual(MaBabySteps.member_amount, 50)

    def test_program_start_is_january_2020(self):
        self.assertEqual(MaBabySteps.program_start, date(2020, 1, 1))

    def test_enrollment_window_is_twelve_months(self):
        self.assertEqual(MaBabySteps.enrollment_window_months, 12)

    def test_beneficiary_relationships(self):
        self.assertEqual(
            MaBabySteps.beneficiary_relationships,
            ["child", "fosterChild", "grandChild", "sibling", "other"],
        )


class TestBeneficiaryRelationshipMapping(MaBabyStepsTestCase):
    """
    spec.md requires the full 12-value `relationship` mapping to be asserted directly, not
    just through the household-level scenarios.
    """

    def test_is_beneficiary_candidate_for_all_relationship_values(self):
        calculator = self.make_calculator(self.make_screen())

        for relationship, expected in RELATIONSHIP_CANDIDACY.items():
            with self.subTest(relationship=relationship):
                self.assertEqual(calculator.is_beneficiary_candidate(relationship), expected)

    def test_covers_every_relationship_value(self):
        self.assertEqual(len(RELATIONSHIP_CANDIDACY), 12)

    def test_unknown_and_missing_relationships_are_not_candidates(self):
        calculator = self.make_calculator(self.make_screen())

        self.assertFalse(calculator.is_beneficiary_candidate(None))
        self.assertFalse(calculator.is_beneficiary_candidate("notARelationship"))


class TestMaBabyStepsScenarios(MaBabyStepsTestCase):
    def test_scenario_1_golden_path_recent_birth(self):
        """Scenario 1: MA household with a child born Feb 2026 → eligible, $50."""
        screen = self.make_screen(household_size=2)
        self.make_member(screen, "headOfHousehold", date(1994, 3, 1))
        self.make_member(screen, "child", date(2026, 2, 1))

        _, eligibility = self.calculate(screen)

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 50)

    def test_scenario_2_no_income_gate(self):
        """Scenario 2: high-income household with a qualifying child → eligible, $50."""
        screen = self.make_screen(zipcode="02139", county="Cambridge", household_size=3)
        self.make_member(screen, "headOfHousehold", date(1991, 3, 1), monthly_income=6_250)
        self.make_member(screen, "spouse", date(1992, 6, 1), monthly_income=5_417)
        self.make_member(screen, "child", date(2026, 2, 1))

        _, eligibility = self.calculate(screen)

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 50)
        # Sanity check that the household really does report a high income, so this test would
        # fail if an income gate were ever added.
        self.assertGreater(screen.calc_gross_income("yearly", ["all"]), 100_000)

    def test_scenario_3_twins_stack_per_child(self):
        """Scenario 3: two children inside the birth window → $100, not a flat $50."""
        screen = self.make_screen(zipcode="01201", county="Pittsfield", household_size=4)
        self.make_member(screen, "headOfHousehold", date(1990, 3, 1))
        self.make_member(screen, "spouse", date(1991, 8, 1))
        self.make_member(screen, "child", date(2025, 11, 1))
        self.make_member(screen, "child", date(2025, 11, 1))

        _, eligibility = self.calculate(screen)

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 100)

    def test_scenario_4_mixed_age_household_values_only_the_child_under_one(self):
        """
        Scenario 4: a recent birth plus an older sibling past the first-birthday cutoff.
        Only the child inside the birth-pathway window is valued.
        """
        screen = self.make_screen(zipcode="02148", county="Malden", household_size=4)
        self.make_member(screen, "headOfHousehold", date(1990, 3, 1))
        self.make_member(screen, "spouse", date(1991, 6, 1))
        older_sibling = self.make_member(screen, "child", date(2018, 9, 1))
        newborn = self.make_member(screen, "child", date(2026, 2, 1))

        calculator, eligibility = self.calculate(screen)

        self.assertTrue(eligibility.eligible)
        # $50, not $100 — the older sibling is past the cutoff.
        self.assertEqual(eligibility.value, 50)
        self.assertTrue(calculator.birth_pathway_eligible(newborn))
        self.assertFalse(calculator.birth_pathway_eligible(older_sibling))

    def test_scenario_5_no_beneficiary_candidate_is_ineligible(self):
        """Scenario 5: household of only headOfHousehold + spouse → ineligible."""
        screen = self.make_screen(zipcode="01201", county="Pittsfield", household_size=2)
        self.make_member(screen, "headOfHousehold", date(1990, 3, 1))
        self.make_member(screen, "spouse", date(1991, 8, 1))

        _, eligibility = self.calculate(screen)

        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.value, 0)

    def test_scenario_6_snap_receipt_does_not_change_result(self):
        """Scenario 6: SNAP is neither required nor disqualifying → eligible, $50."""
        snap = Program.objects.new_program(white_label="ma", name_abbreviated="ma_snap")
        screen = self.make_screen(zipcode="02148", county="Malden", household_size=3)
        self.make_member(screen, "headOfHousehold", date(1990, 3, 1), monthly_income=2_800)
        self.make_member(screen, "spouse", date(1989, 8, 1), monthly_income=2_200)
        self.make_member(screen, "child", date(2026, 2, 1))
        CurrentBenefit.objects.create(screen=screen, program=snap)

        _, eligibility = self.calculate(screen)

        self.assertTrue(screen.has_benefit("ma_snap"))
        self.assertTrue(eligibility.eligible)
        # Still exactly $50 — the separate "SNAP into BabySteps" $120 add-on is out of scope.
        self.assertEqual(eligibility.value, 50)

    def test_scenario_7_grandchild_qualifies(self):
        """Scenario 7: a `grandChild` beneficiary candidate → eligible, $50."""
        screen = self.make_screen(household_size=2)
        self.make_member(screen, "headOfHousehold", date(1968, 3, 1))
        self.make_member(screen, "grandChild", date(2026, 3, 1))

        _, eligibility = self.calculate(screen)

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 50)

    def test_scenario_8_birth_pathway_month_boundary(self):
        """
        Scenario 8: a child turning one during the current month is still inside the window.
        Asserting `birth_pathway_eligible` pins the month-level boundary directly.
        """
        screen = self.make_screen(zipcode="02148", county="Malden", household_size=2)
        self.make_member(screen, "headOfHousehold", date(1990, 5, 1))
        child = self.make_member(screen, "child", date(2025, 7, 1))

        calculator, eligibility = self.calculate(screen)

        self.assertTrue(calculator.birth_pathway_eligible(child))
        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 50)

    def test_scenario_9_birth_pathway_expired_is_ineligible(self):
        """
        Scenario 9: the paired case — a child whose birth window has closed is ineligible.
        The adoption pathway would need an adoption date the screener does not collect.
        """
        screen = self.make_screen(zipcode="02139", county="Cambridge", household_size=2)
        self.make_member(screen, "headOfHousehold", date(1990, 3, 1))
        child = self.make_member(screen, "child", date(2025, 6, 1))

        calculator, eligibility = self.calculate(screen)

        self.assertFalse(calculator.birth_pathway_eligible(child))
        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.value, 0)

    def test_scenario_10_reported_bug_household(self):
        """
        Scenario 10 — the MFB-1729 repro household shape: two children under one plus a two-year-old.
        Only the two under-one children are valued. Birth dates are re-anchored to the
        frozen July 22, 2026 evaluation date rather than copied from the ticket, which
        reported ages relative to the live date.
        """
        screen = self.make_screen(zipcode="02148", county="Malden", household_size=5)
        self.make_member(screen, "headOfHousehold", date(1990, 3, 1))
        self.make_member(screen, "domesticPartner", date(1991, 3, 1))
        infant = self.make_member(screen, "child", date(2026, 1, 1))
        foster_infant = self.make_member(screen, "fosterChild", date(2025, 10, 1))
        two_year_old = self.make_member(screen, "child", date(2024, 5, 1))

        calculator, eligibility = self.calculate(screen)

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 100)
        self.assertTrue(calculator.birth_pathway_eligible(infant))
        self.assertTrue(calculator.birth_pathway_eligible(foster_infant))
        self.assertFalse(calculator.birth_pathway_eligible(two_year_old))


class TestBirthPathwayBoundaries(MaBabyStepsTestCase):
    """Direct coverage of `birth_pathway_eligible`, which the scenarios only sample."""

    def birth_pathway_result(self, birth_year_month):
        screen = self.make_screen(household_size=2)
        self.make_member(screen, "headOfHousehold", date(1990, 3, 1))
        child = self.make_member(screen, "child", birth_year_month)

        return self.make_calculator(screen).birth_pathway_eligible(child)

    def test_newborn_is_inside_window(self):
        self.assertTrue(self.birth_pathway_result(date(2026, 7, 1)))

    def test_eleven_months_old_is_inside_window(self):
        self.assertTrue(self.birth_pathway_result(date(2025, 8, 1)))

    def test_first_birthday_month_is_inside_window(self):
        """Month-level inclusive treatment: the screener has no day of birth to compare."""
        self.assertTrue(self.birth_pathway_result(date(2025, 7, 1)))

    def test_month_after_first_birthday_is_outside_window(self):
        self.assertFalse(self.birth_pathway_result(date(2025, 6, 1)))

    def test_born_before_program_start_is_outside_window(self):
        """A December 2019 birth predates the program, so the birth pathway cannot apply."""
        self.assertFalse(self.birth_pathway_result(date(2019, 12, 1)))

    def test_program_start_month_alone_does_not_qualify(self):
        """January 2020 is on or after the start date but far outside the one-year window."""
        self.assertFalse(self.birth_pathway_result(date(2020, 1, 1)))

    def test_missing_birth_year_month_is_outside_window(self):
        self.assertFalse(self.birth_pathway_result(None))

    def test_missing_birth_year_month_is_ineligible(self):
        """
        A candidate with no birth date cannot be placed inside the one-year window, so the
        birth pathway does not pass.

        This state is reachable: `HouseholdMemberSerializer` takes `birth_year`/`birth_month`
        as optional and accepts `age` directly, leaving `birth_year_month` null. The React
        wizard always sends both, so there is no user-facing regression, but an API-direct
        caller or a legacy row with only `age` set now returns $0 where it previously
        returned $50 via the removed adoption fallback.
        """
        screen = self.make_screen(household_size=2)
        self.make_member(screen, "headOfHousehold", date(1990, 3, 1))
        child = self.make_member(screen, "child", None)

        calculator, eligibility = self.calculate(screen)

        self.assertFalse(calculator.birth_pathway_eligible(child))
        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.value, 0)

    def test_non_candidate_adult_is_not_eligible(self):
        """An adult caregiver role is outside the assistance unit regardless of timing."""
        screen = self.make_screen(household_size=1)
        head = self.make_member(screen, "headOfHousehold", date(1990, 3, 1))

        calculator = self.make_calculator(screen)

        self.assertFalse(calculator.birth_pathway_eligible(head))
        self.assertFalse(calculator.is_beneficiary_candidate(head.relationship))


class TestMemberEligibilityAndValue(MaBabyStepsTestCase):
    def test_each_candidate_relationship_is_eligible_at_household_level(self):
        """Every candidate role qualifies on its own and is worth exactly $50."""
        for relationship in MaBabySteps.beneficiary_relationships:
            with self.subTest(relationship=relationship):
                screen = self.make_screen(household_size=2)
                self.make_member(screen, "headOfHousehold", date(1985, 3, 1))
                self.make_member(screen, relationship, date(2026, 2, 1))

                _, eligibility = self.calculate(screen)

                self.assertTrue(eligibility.eligible)
                self.assertEqual(eligibility.value, 50)

    def test_each_non_candidate_relationship_is_ineligible(self):
        """
        A household of only non-candidate roles is ineligible even when a member is young
        enough to be inside the birth-pathway window.
        """
        non_candidates = [rel for rel, expected in RELATIONSHIP_CANDIDACY.items() if not expected]

        for relationship in non_candidates:
            with self.subTest(relationship=relationship):
                screen = self.make_screen(household_size=1)
                self.make_member(screen, relationship, date(2026, 2, 1))

                _, eligibility = self.calculate(screen)

                self.assertFalse(eligibility.eligible)
                self.assertEqual(eligibility.value, 0)

    def test_only_candidate_members_are_valued(self):
        """Non-candidate members in an eligible household contribute no value."""
        screen = self.make_screen(household_size=3)
        self.make_member(screen, "headOfHousehold", date(1990, 3, 1))
        self.make_member(screen, "spouse", date(1991, 3, 1))
        self.make_member(screen, "child", date(2026, 2, 1))

        _, eligibility = self.calculate(screen)

        valued = [m for m in eligibility.eligible_members if m.value > 0]
        self.assertEqual(len(valued), 1)
        self.assertEqual(valued[0].member.relationship, "child")
        self.assertEqual(eligibility.value, 50)

    def test_three_children_stack_to_150(self):
        screen = self.make_screen(household_size=4)
        self.make_member(screen, "headOfHousehold", date(1990, 3, 1))
        self.make_member(screen, "child", date(2026, 2, 1))
        self.make_member(screen, "child", date(2025, 9, 1))
        self.make_member(screen, "grandChild", date(2026, 1, 1))

        _, eligibility = self.calculate(screen)

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 150)

    def test_no_household_value_component(self):
        """The benefit is entirely per-child; nothing is added at the household level."""
        screen = self.make_screen(household_size=2)
        self.make_member(screen, "headOfHousehold", date(1990, 3, 1))
        self.make_member(screen, "child", date(2026, 2, 1))

        _, eligibility = self.calculate(screen)

        self.assertEqual(eligibility.household_value, 0)

    def test_no_fail_messages(self):
        """No household condition carries a message — there is no evaluable household gate."""
        screen = self.make_screen(household_size=2)
        self.make_member(screen, "headOfHousehold", date(1990, 3, 1))
        self.make_member(screen, "spouse", date(1991, 3, 1))

        _, eligibility = self.calculate(screen)

        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.fail_messages, [])


class TestDataGapDefaults(MaBabyStepsTestCase):
    """
    The three data gaps in spec.md have no screener input, so they are covered as assertions
    about the calculator's inclusive defaults rather than as distinguishable inputs.
    """

    def test_prior_babysteps_receipt_does_not_exclude_the_household(self):
        """
        Criterion 3: prior receipt is per-child, but current benefits are household-level. Even
        if BabySteps is reported as a current benefit, a newly born child still qualifies.
        """
        screen = self.make_screen(household_size=3)
        self.make_member(screen, "headOfHousehold", date(1990, 3, 1))
        self.make_member(screen, "child", date(2022, 4, 1))
        self.make_member(screen, "child", date(2026, 2, 1))
        CurrentBenefit.objects.create(screen=screen, program=self.program)

        _, eligibility = self.calculate(screen)

        self.assertTrue(screen.has_benefit("ma_bsp"))
        self.assertTrue(eligibility.eligible)
        # $50: the household-level receipt flag does not exclude the newly born child. The
        # 2022 child is excluded by the age cutoff, not by the receipt flag.
        self.assertEqual(eligibility.value, 50)

    def test_older_child_is_denied_by_the_age_cutoff(self):
        """
        The first-birthday cutoff applies to every candidate, including one who could qualify
        via the adoption pathway (Criterion 2b).
        """
        screen = self.make_screen(household_size=2)
        self.make_member(screen, "headOfHousehold", date(1975, 3, 1))
        teenager = self.make_member(screen, "child", date(2009, 5, 1))

        calculator, eligibility = self.calculate(screen)

        self.assertFalse(calculator.birth_pathway_eligible(teenager))
        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.value, 0)

    def test_birthplace_is_not_used_to_exclude(self):
        """
        Criterion 4: born or adopted in Massachusetts is a real rule with no screener field, so
        it is applied inclusively — the calculator reads no birthplace input at all.
        """
        screen = self.make_screen(household_size=2)
        self.make_member(screen, "headOfHousehold", date(1990, 3, 1))
        self.make_member(screen, "child", date(2026, 2, 1))

        calculator, eligibility = self.calculate(screen)

        self.assertTrue(eligibility.eligible)
        self.assertEqual(calculator.dependencies, ["relationship", "birth_year"])

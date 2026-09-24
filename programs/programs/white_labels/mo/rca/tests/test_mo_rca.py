"""
MO Refugee Cash Assistance.

Builds real Screen/HouseholdMember/IncomeStream rows via the shared
`programs.programs.testing_fixtures.pe_integration` builders and runs the real
`MoRca.calc()` against them — no Mocks. Each test names the spec.md scenario it
comes from; scenarios that carry a dollar figure assert the value to the cent as
well as the verdict and the per-member marks, since a calculator that returns the
right household verdict on the wrong case split or the wrong member marks is
exactly the failure the value scenarios were written to catch.

Immigration status has no test: it lives on the program row's `legal_status_required`,
which is config-level and outside the calculator's test universe (spec.md).
"""

from django.test import TestCase

from programs.programs.testing_fixtures.pe_integration import add_income, add_member, make_program, make_screen
from programs.programs.white_labels.mo.rca.calculator import MoRca, rca_max_payment
from programs.util import DependencyError, Dependencies
from screener.models import IncomeStream
from screener.serializers import _write_current_benefits
from screener.tests.helpers import seed_program


class MoRcaTestCase(TestCase):
    """Shared household builder: a real Screen, real HouseholdMembers/IncomeStreams,
    and the real MoRca calculator run against them."""

    def build_screen(self, household_size, zipcode="63118", county="St. Louis City"):
        screen = make_screen(
            1,
            white_label_code="mo",
            state_code="MO",
            household_size=household_size,
            zipcode=zipcode,
            county=county,
        )
        # make_screen creates the white label; make_program looks it up, so it has
        # to run second.
        self.program = make_program("mo", "mo_rca", "2026")
        return screen

    def calc(self, screen):
        return MoRca(screen, self.program, {}, Dependencies()).calc()

    def marks_by_id(self, result):
        return {
            member_eligibility.member.id: member_eligibility.eligible for member_eligibility in result.eligible_members
        }


class TestRegistration(MoRcaTestCase):
    def test_program_code(self):
        self.assertEqual(MoRca.program_code, "mo_rca")

    def test_dependencies(self):
        """income_type is the non-obvious one: a null `type` does not raise the way a
        null `amount` or `frequency` does, so it must be declared or it is silently
        counted as unearned in full (spec.md Implementation)."""
        self.assertEqual(set(MoRca.dependencies), {"income_type", "income_amount", "income_frequency"})


class TestDependencyError(MoRcaTestCase):
    def test_missing_income_field_raises(self):
        """A screen carrying an income stream with a missing type, amount or
        frequency is suppressed rather than valued: `can_calc()` returns False and
        `calc()` raises — using the real `Screen.missing_fields()` production read,
        not a stubbed one."""
        screen = self.build_screen(household_size=1)
        member = add_member(screen, 1, "headOfHousehold", 30)
        IncomeStream.objects.create(
            screen=screen, household_member=member, type="wages", amount=None, frequency="monthly"
        )

        with self.assertRaises(DependencyError):
            MoRca(screen, self.program, {}, screen.missing_fields()).calc()


class TestRcaMaxPayment(TestCase):
    """The tabulated sizes 1-5, and the +$113 extension applied once per additional
    member beyond 5. A pure function — no household needed."""

    def test_tabulated_sizes(self):
        self.assertEqual(rca_max_payment(1), 537)
        self.assertEqual(rca_max_payment(2), 726)
        self.assertEqual(rca_max_payment(3), 915)
        self.assertEqual(rca_max_payment(4), 1104)
        self.assertEqual(rca_max_payment(5), 1217)

    def test_extrapolated_sizes(self):
        self.assertEqual(rca_max_payment(6), 1330)
        self.assertEqual(rca_max_payment(7), 1443)
        self.assertEqual(rca_max_payment(10), 1217 + 113 * 5)


class TestExcludedUnearnedIncome(MoRcaTestCase):
    """`cashAssistanceOther` and `gifts` are excluded from countable unearned
    income — a proxy for cash grants MFB cannot otherwise identify. Not one of the
    numbered Test Scenarios (spec.md deliberately leaves this proxy untested at the
    scenario level); asserted directly here instead."""

    def test_excludes_cash_assistance_other(self):
        screen = self.build_screen(household_size=1)
        member = add_member(screen, 1, "headOfHousehold", 30)
        add_income(member, 500, "cashAssistanceOther", "monthly")

        result = self.calc(screen)

        self.assertEqual((result.eligible, result.value), (True, 4296.0))

    def test_excludes_gifts(self):
        screen = self.build_screen(household_size=1)
        member = add_member(screen, 1, "headOfHousehold", 30)
        add_income(member, 500, "gifts", "monthly")

        result = self.calc(screen)

        self.assertEqual((result.eligible, result.value), (True, 4296.0))


class TestScenarios(MoRcaTestCase):
    def test_scenario_1_single_adult_no_income(self):
        screen = self.build_screen(household_size=1)
        add_member(screen, 1, "headOfHousehold", 30)

        result = self.calc(screen)

        self.assertEqual((result.eligible, result.value), (True, 4296.0))

    def test_scenario_2_single_adult_with_wages(self):
        screen = self.build_screen(household_size=1)
        member = add_member(screen, 1, "headOfHousehold", 30)
        add_income(member, 1000, "wages", "monthly")

        result = self.calc(screen)

        self.assertEqual((result.eligible, result.value), (True, 2476.0))

    def test_scenario_3_net_income_equals_standard_is_ineligible(self):
        """The boundary is strict: net income equal to the standard fails."""
        screen = self.build_screen(household_size=1)
        member = add_member(screen, 1, "headOfHousehold", 30)
        add_income(member, 2238, "wages", "monthly")

        result = self.calc(screen)

        self.assertFalse(result.eligible)

    def test_scenario_4_one_dollar_under_the_standard(self):
        screen = self.build_screen(household_size=1)
        member = add_member(screen, 1, "headOfHousehold", 30)
        add_income(member, 2234, "wages", "monthly")

        result = self.calc(screen)

        self.assertEqual((result.eligible, result.value), (True, 8.0))

    def test_scenario_5_unearned_income_only(self):
        """Unearned income receives no disregard."""
        screen = self.build_screen(household_size=1, zipcode="64110", county="Jackson County")
        member = add_member(screen, 1, "headOfHousehold", 30)
        add_income(member, 400, "childSupport", "monthly")

        result = self.calc(screen)

        self.assertEqual((result.eligible, result.value), (True, 1096.0))

    def test_scenario_6_family_of_four_earned_and_unearned(self):
        screen = self.build_screen(household_size=4)
        p1 = add_member(screen, 1, "headOfHousehold", 30)
        add_member(screen, 2, "spouse", 28)
        add_member(screen, 3, "child", 8)
        p4 = add_member(screen, 4, "child", 5)
        add_income(p1, 1200, "wages", "monthly")
        add_income(p4, 200, "childSupport", "monthly")

        result = self.calc(screen)

        self.assertEqual((result.eligible, result.value), (True, 5012.0))
        self.assertEqual(self.marks_by_id(result), {1: True, 2: True, 3: True, 4: True})

    def test_scenario_7_family_of_five_no_income(self):
        screen = self.build_screen(household_size=5, zipcode="65806", county="Greene County")
        add_member(screen, 1, "headOfHousehold", 30)
        add_member(screen, 2, "spouse", 28)
        add_member(screen, 3, "child", 8)
        add_member(screen, 4, "child", 5)
        add_member(screen, 5, "child", 3)

        result = self.calc(screen)

        self.assertEqual((result.eligible, result.value), (True, 9736.0))

    def test_scenario_8_family_of_six_no_income(self):
        """The +$113 extension beyond the tabulated sizes."""
        screen = self.build_screen(household_size=6, zipcode="65806", county="Greene County")
        add_member(screen, 1, "headOfHousehold", 30)
        add_member(screen, 2, "spouse", 28)
        add_member(screen, 3, "child", 8)
        add_member(screen, 4, "child", 5)
        add_member(screen, 5, "child", 3)
        add_member(screen, 6, "child", 1)

        result = self.calc(screen)

        self.assertEqual((result.eligible, result.value), (True, 10640.0))

    def test_scenario_9_two_earning_adults_exemption_is_per_member(self):
        """The $90 exemption applies per earning member, not once per case, and
        selfEmployment counts as earned."""
        screen = self.build_screen(household_size=2, zipcode="64110", county="Jackson County")
        p1 = add_member(screen, 1, "headOfHousehold", 30)
        p2 = add_member(screen, 2, "spouse", 28)
        add_income(p1, 600, "wages", "monthly")
        add_income(p2, 600, "selfEmployment", "monthly")

        result = self.calc(screen)

        self.assertEqual((result.eligible, result.value), (True, 3768.0))
        self.assertEqual(self.marks_by_id(result), {1: True, 2: True})

    def test_scenario_10_member_reporting_tanf_cash_is_removed(self):
        """A single-member case that reports `cashAssistance` loses its only
        member and so pays nothing."""
        screen = self.build_screen(household_size=1)
        member = add_member(screen, 1, "headOfHousehold", 30)
        add_income(member, 400, "cashAssistance", "monthly")

        result = self.calc(screen)

        self.assertEqual((result.eligible, result.value), (False, 0))
        self.assertEqual(self.marks_by_id(result), {1: False})

    def test_scenario_11_member_receiving_ssi_is_removed(self):
        screen = self.build_screen(household_size=2)
        add_member(screen, 1, "headOfHousehold", 30)
        p2 = add_member(screen, 2, "spouse", 28)
        add_income(p2, 400, "sSI", "monthly")

        result = self.calc(screen)

        self.assertEqual((result.eligible, result.value), (True, 4296.0))
        self.assertEqual(self.marks_by_id(result), {1: True, 2: False})

    def test_scenario_12_age_blindness_disability_do_not_exclude(self):
        """The SSI-pending pathway: none of age 65+, disability, or blindness is
        an exclusion — only a reported SSI amount removes a member."""
        screen = self.build_screen(household_size=1)
        add_member(
            screen,
            1,
            "headOfHousehold",
            67,
            disabled=True,
            visually_impaired=True,
            long_term_disability=True,
        )

        result = self.calc(screen)

        self.assertEqual((result.eligible, result.value), (True, 4296.0))

    def test_scenario_13_non_monthly_income_arithmetic(self):
        """A biweekly income stream is normalised through the real
        `IncomeStream.monthly()` before the disregard applies."""
        screen = self.build_screen(household_size=1)
        member = add_member(screen, 1, "headOfHousehold", 30)
        add_income(member, 600, "wages", "biweekly")

        result = self.calc(screen)

        self.assertTrue(result.eligible)
        self.assertAlmostEqual(result.value, 1866.0, places=2)

    def test_scenario_14_earned_income_clamped_at_zero(self):
        """Earning less than the $90 exemption contributes $0, never a negative
        amount."""
        screen = self.build_screen(household_size=1)
        member = add_member(screen, 1, "headOfHousehold", 30)
        add_income(member, 50, "wages", "monthly")

        result = self.calc(screen)

        self.assertEqual((result.eligible, result.value), (True, 4296.0))

    def test_scenario_15_adult_child_splits_at_the_age_18_boundary(self):
        screen = self.build_screen(household_size=4)
        add_member(screen, 1, "headOfHousehold", 30)
        add_member(screen, 2, "spouse", 28)
        add_member(screen, 3, "stepChild", 18)
        add_member(screen, 4, "child", 17)

        result = self.calc(screen)

        self.assertEqual((result.eligible, result.value), (True, 11616.0))
        self.assertEqual(self.marks_by_id(result), {1: True, 2: True, 3: True, 4: True})

    def test_scenario_16_income_summed_per_case_not_pooled(self):
        screen = self.build_screen(household_size=3)
        add_member(screen, 1, "headOfHousehold", 30)
        add_member(screen, 2, "spouse", 28)
        p3 = add_member(screen, 3, "child", 18)
        add_income(p3, 1000, "wages", "monthly")

        result = self.calc(screen)

        self.assertEqual((result.eligible, result.value), (True, 8284.0))
        self.assertEqual(self.marks_by_id(result), {1: True, 2: True, 3: True})

    def test_scenario_17_ineligible_case_contributes_nothing(self):
        """An ineligible case's members are marked ineligible even though a
        sibling case in the same household is still payable."""
        screen = self.build_screen(household_size=3)
        p1 = add_member(screen, 1, "headOfHousehold", 30)
        add_member(screen, 2, "spouse", 28)
        add_member(screen, 3, "child", 18)
        add_income(p1, 3000, "wages", "monthly")

        result = self.calc(screen)

        self.assertEqual((result.eligible, result.value), (True, 4296.0))
        self.assertEqual(self.marks_by_id(result), {1: False, 2: False, 3: True})

    def test_scenario_18_additional_member_amount_applies_per_member(self):
        screen = self.build_screen(household_size=7, zipcode="65806", county="Greene County")
        add_member(screen, 1, "headOfHousehold", 30)
        add_member(screen, 2, "spouse", 28)
        add_member(screen, 3, "child", 8)
        add_member(screen, 4, "child", 5)
        add_member(screen, 5, "child", 3)
        add_member(screen, 6, "child", 1)
        add_member(screen, 7, "child", 9)

        result = self.calc(screen)

        self.assertEqual((result.eligible, result.value), (True, 11544.0))

    def test_scenario_19_household_level_tanf_report_gates_nothing(self):
        """A ticked current-benefits tile is never read for this gate — only a
        member's own reported `cashAssistance` amount removes them."""
        screen = self.build_screen(household_size=2)
        add_member(screen, 1, "headOfHousehold", 30)
        add_member(screen, 2, "spouse", 28)
        seed_program(screen.white_label, "mo_tanf_current", base_program="tanf")
        _write_current_benefits(screen, ["mo_tanf_current"])
        screen.invalidate_current_benefits_cache()

        result = self.calc(screen)

        self.assertEqual((result.eligible, result.value), (True, 5808.0))
        self.assertEqual(self.marks_by_id(result), {1: True, 2: True})

    def test_scenario_20_value_is_carried_to_the_cent(self):
        screen = self.build_screen(household_size=1, zipcode="64110", county="Jackson County")
        member = add_member(screen, 1, "headOfHousehold", 30)
        add_income(member, 400.33, "childSupport", "monthly")

        result = self.calc(screen)

        self.assertTrue(result.eligible)
        self.assertAlmostEqual(result.value, 1093.36, places=2)

"""
MO Refugee Cash Assistance.

MoRca is a plain custom (non-PolicyEngine) calculator, so `CustomCalculatorTestCase`
is the purpose-built home for it — it builds real Screen/HouseholdMember/IncomeStream
rows and runs the real `MoRca.calc()` against them, no Mocks. Each test names the
spec.md scenario it comes from; scenarios that carry a dollar figure assert the value
to the cent as well as the verdict and the per-member marks, since a calculator that
returns the right household verdict on the wrong case split or the wrong member marks
is exactly the failure the value scenarios were written to catch.

Immigration status has no test: it lives on the program row's `legal_status_required`,
which is config-level and outside the calculator's test universe (spec.md).
"""

from django.test import TestCase

from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from programs.programs.white_labels.mo.rca.calculator import MoRca, rca_max_payment
from programs.util import DependencyError
from screener.models import IncomeStream
from screener.serializers import _write_current_benefits
from screener.tests.helpers import seed_program


class MoRcaTestCase(CustomCalculatorTestCase):
    calculator_class = MoRca
    program_code = "mo_rca"
    white_label_code = "mo"
    state_code = "MO"
    default_zipcode = "63118"
    default_county = "St. Louis City"

    # MoRca never reads self.program — no FPL or SMI lookup — so setUpTestData can
    # skip the real Program row (and the ~10 translated fields it writes per language).
    needs_program_row = False

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
        screen = self.make_screen(household_size=1)
        member = self.add_member(screen, "headOfHousehold", 30)
        IncomeStream.objects.create(
            screen=screen, household_member=member, type="wages", amount=None, frequency="monthly"
        )

        with self.assertRaises(DependencyError):
            self.calculate(screen, missing=screen.missing_fields())


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
        screen = self.make_screen(household_size=1)
        self.add_member(screen, "headOfHousehold", 30, monthly_income=500, income_type="cashAssistanceOther")

        result = self.calculate(screen)

        self.assertEqual((result.eligible, result.value), (True, 4296.0))

    def test_excludes_gifts(self):
        screen = self.make_screen(household_size=1)
        self.add_member(screen, "headOfHousehold", 30, monthly_income=500, income_type="gifts")

        result = self.calculate(screen)

        self.assertEqual((result.eligible, result.value), (True, 4296.0))


class TestScenarios(MoRcaTestCase):
    def test_scenario_1_single_adult_no_income(self):
        screen = self.make_screen(household_size=1)
        self.add_member(screen, "headOfHousehold", 30)

        result = self.calculate(screen)

        self.assertEqual((result.eligible, result.value), (True, 4296.0))

    def test_scenario_2_single_adult_with_wages(self):
        screen = self.make_screen(household_size=1)
        self.add_member(screen, "headOfHousehold", 30, monthly_income=1000, income_type="wages")

        result = self.calculate(screen)

        self.assertEqual((result.eligible, result.value), (True, 2476.0))

    def test_scenario_3_net_income_equals_standard_is_ineligible(self):
        """The boundary is strict: net income equal to the standard fails."""
        screen = self.make_screen(household_size=1)
        self.add_member(screen, "headOfHousehold", 30, monthly_income=2238, income_type="wages")

        result = self.calculate(screen)

        self.assertFalse(result.eligible)

    def test_scenario_4_one_dollar_under_the_standard(self):
        screen = self.make_screen(household_size=1)
        self.add_member(screen, "headOfHousehold", 30, monthly_income=2234, income_type="wages")

        result = self.calculate(screen)

        self.assertEqual((result.eligible, result.value), (True, 8.0))

    def test_scenario_5_unearned_income_only(self):
        """Unearned income receives no disregard."""
        screen = self.make_screen(household_size=1, zipcode="64110", county="Jackson County")
        self.add_member(screen, "headOfHousehold", 30, monthly_income=400, income_type="childSupport")

        result = self.calculate(screen)

        self.assertEqual((result.eligible, result.value), (True, 1096.0))

    def test_scenario_6_family_of_four_earned_and_unearned(self):
        screen = self.make_screen(household_size=4)
        p1 = self.add_member(screen, "headOfHousehold", 30, monthly_income=1200, income_type="wages")
        p2 = self.add_member(screen, "spouse", 28)
        p3 = self.add_member(screen, "child", 8)
        p4 = self.add_member(screen, "child", 5, monthly_income=200, income_type="childSupport")

        result = self.calculate(screen)

        self.assertEqual((result.eligible, result.value), (True, 5012.0))
        self.assertEqual(self.marks_by_id(result), {p1.id: True, p2.id: True, p3.id: True, p4.id: True})

    def test_scenario_7_family_of_five_no_income(self):
        screen = self.make_screen(household_size=5, zipcode="65806", county="Greene County")
        self.add_member(screen, "headOfHousehold", 30)
        self.add_member(screen, "spouse", 28)
        self.add_member(screen, "child", 8)
        self.add_member(screen, "child", 5)
        self.add_member(screen, "child", 3)

        result = self.calculate(screen)

        self.assertEqual((result.eligible, result.value), (True, 9736.0))

    def test_scenario_8_family_of_six_no_income(self):
        """The +$113 extension beyond the tabulated sizes."""
        screen = self.make_screen(household_size=6, zipcode="65806", county="Greene County")
        self.add_member(screen, "headOfHousehold", 30)
        self.add_member(screen, "spouse", 28)
        self.add_member(screen, "child", 8)
        self.add_member(screen, "child", 5)
        self.add_member(screen, "child", 3)
        self.add_member(screen, "child", 1)

        result = self.calculate(screen)

        self.assertEqual((result.eligible, result.value), (True, 10640.0))

    def test_scenario_9_two_earning_adults_exemption_is_per_member(self):
        """The $90 exemption applies per earning member, not once per case, and
        selfEmployment counts as earned."""
        screen = self.make_screen(household_size=2, zipcode="64110", county="Jackson County")
        p1 = self.add_member(screen, "headOfHousehold", 30, monthly_income=600, income_type="wages")
        p2 = self.add_member(screen, "spouse", 28, monthly_income=600, income_type="selfEmployment")

        result = self.calculate(screen)

        self.assertEqual((result.eligible, result.value), (True, 3768.0))
        self.assertEqual(self.marks_by_id(result), {p1.id: True, p2.id: True})

    def test_scenario_10_member_reporting_tanf_cash_is_removed(self):
        """A single-member case that reports `cashAssistance` loses its only
        member and so pays nothing."""
        screen = self.make_screen(household_size=1)
        p1 = self.add_member(screen, "headOfHousehold", 30, monthly_income=400, income_type="cashAssistance")

        result = self.calculate(screen)

        self.assertEqual((result.eligible, result.value), (False, 0))
        self.assertEqual(self.marks_by_id(result), {p1.id: False})

    def test_scenario_11_member_receiving_ssi_is_removed(self):
        screen = self.make_screen(household_size=2)
        p1 = self.add_member(screen, "headOfHousehold", 30)
        p2 = self.add_member(screen, "spouse", 28, monthly_income=400, income_type="sSI")

        result = self.calculate(screen)

        self.assertEqual((result.eligible, result.value), (True, 4296.0))
        self.assertEqual(self.marks_by_id(result), {p1.id: True, p2.id: False})

    def test_scenario_12_age_blindness_disability_do_not_exclude(self):
        """The SSI-pending pathway: none of age 65+, disability, or blindness is
        an exclusion — only a reported SSI amount removes a member."""
        screen = self.make_screen(household_size=1)
        self.add_member(
            screen,
            "headOfHousehold",
            67,
            disabled=True,
            visually_impaired=True,
            long_term_disability=True,
        )

        result = self.calculate(screen)

        self.assertEqual((result.eligible, result.value), (True, 4296.0))

    def test_scenario_13_non_monthly_income_arithmetic(self):
        """A biweekly income stream is normalised through the real
        `IncomeStream.monthly()` before the disregard applies."""
        screen = self.make_screen(household_size=1)
        member = self.add_member(screen, "headOfHousehold", 30)
        self.add_income(member, 600, income_type="wages", frequency="biweekly")

        result = self.calculate(screen)

        self.assertTrue(result.eligible)
        self.assertAlmostEqual(result.value, 1866.0, places=2)

    def test_scenario_14_earned_income_clamped_at_zero(self):
        """Earning less than the $90 exemption contributes $0, never a negative
        amount."""
        screen = self.make_screen(household_size=1)
        self.add_member(screen, "headOfHousehold", 30, monthly_income=50, income_type="wages")

        result = self.calculate(screen)

        self.assertEqual((result.eligible, result.value), (True, 4296.0))

    def test_scenario_15_adult_child_splits_at_the_age_18_boundary(self):
        screen = self.make_screen(household_size=4)
        p1 = self.add_member(screen, "headOfHousehold", 30)
        p2 = self.add_member(screen, "spouse", 28)
        p3 = self.add_member(screen, "stepChild", 18)
        p4 = self.add_member(screen, "child", 17)

        result = self.calculate(screen)

        self.assertEqual((result.eligible, result.value), (True, 11616.0))
        self.assertEqual(self.marks_by_id(result), {p1.id: True, p2.id: True, p3.id: True, p4.id: True})

    def test_scenario_16_income_summed_per_case_not_pooled(self):
        screen = self.make_screen(household_size=3)
        p1 = self.add_member(screen, "headOfHousehold", 30)
        p2 = self.add_member(screen, "spouse", 28)
        p3 = self.add_member(screen, "child", 18, monthly_income=1000, income_type="wages")

        result = self.calculate(screen)

        self.assertEqual((result.eligible, result.value), (True, 8284.0))
        self.assertEqual(self.marks_by_id(result), {p1.id: True, p2.id: True, p3.id: True})

    def test_scenario_17_ineligible_case_contributes_nothing(self):
        """An ineligible case's members are marked ineligible even though a
        sibling case in the same household is still payable."""
        screen = self.make_screen(household_size=3)
        p1 = self.add_member(screen, "headOfHousehold", 30, monthly_income=3000, income_type="wages")
        p2 = self.add_member(screen, "spouse", 28)
        p3 = self.add_member(screen, "child", 18)

        result = self.calculate(screen)

        self.assertEqual((result.eligible, result.value), (True, 4296.0))
        self.assertEqual(self.marks_by_id(result), {p1.id: False, p2.id: False, p3.id: True})

    def test_scenario_18_additional_member_amount_applies_per_member(self):
        screen = self.make_screen(household_size=7, zipcode="65806", county="Greene County")
        self.add_member(screen, "headOfHousehold", 30)
        self.add_member(screen, "spouse", 28)
        self.add_member(screen, "child", 8)
        self.add_member(screen, "child", 5)
        self.add_member(screen, "child", 3)
        self.add_member(screen, "child", 1)
        self.add_member(screen, "child", 9)

        result = self.calculate(screen)

        self.assertEqual((result.eligible, result.value), (True, 11544.0))

    def test_scenario_19_household_level_tanf_report_gates_nothing(self):
        """A ticked current-benefits tile is never read for this gate — only a
        member's own reported `cashAssistance` amount removes them."""
        screen = self.make_screen(household_size=2)
        p1 = self.add_member(screen, "headOfHousehold", 30)
        p2 = self.add_member(screen, "spouse", 28)
        seed_program(screen.white_label, "mo_tanf_current", base_program="tanf")
        _write_current_benefits(screen, ["mo_tanf_current"])
        screen.invalidate_current_benefits_cache()

        result = self.calculate(screen)

        self.assertEqual((result.eligible, result.value), (True, 5808.0))
        self.assertEqual(self.marks_by_id(result), {p1.id: True, p2.id: True})

    def test_scenario_20_value_is_carried_to_the_cent(self):
        screen = self.make_screen(household_size=1, zipcode="64110", county="Jackson County")
        self.add_member(screen, "headOfHousehold", 30, monthly_income=400.33, income_type="childSupport")

        result = self.calculate(screen)

        self.assertTrue(result.eligible)
        self.assertAlmostEqual(result.value, 1093.36, places=2)

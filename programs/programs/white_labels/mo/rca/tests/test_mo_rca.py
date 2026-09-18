"""
MO Refugee Cash Assistance.

Each test names the spec.md scenario it comes from. Scenarios that carry a dollar
figure assert the value to the cent as well as the verdict and the per-member marks,
since a calculator that returns the right household verdict on the wrong case split
or the wrong member marks is exactly the failure the value scenarios were written to
catch (spec.md Acceptance Criterion 13).

Immigration status has no test: it lives on the program row's `legal_status_required`,
which is config-level and outside the calculator's test universe (spec.md).
"""

from unittest.mock import Mock

from django.test import TestCase

from programs.programs.white_labels.mo.rca.calculator import MoRca, rca_max_payment
from programs.util import DependencyError


def make_member(
    relationship="headOfHousehold",
    age=30,
    wages=0,
    self_employment=0,
    unearned=0,
    ssi=0,
    tanf=0,
):
    """A household member with the given monthly earned/unearned income and yearly
    SSI/TANF receipt. `calc_gross_income` is modelled directly at the (frequency,
    types) contract `HouseholdMember` exposes, rather than from raw `IncomeStream`
    rows — the biweekly normalisation `IncomeStream.monthly()` performs is exercised
    at that layer's own tests; here the "monthly" figure passed in already reflects
    it (Scenario 13)."""
    member = Mock()
    member.relationship = relationship
    member.calc_age.return_value = age

    def calc_gross_income(frequency, types, exclude=None):
        # `unearned` already models the amount left after Data Gap 5's exclusions, so
        # `exclude` (always the same fixed constant here) plays no further role.
        if frequency == "monthly":
            total = 0.0
            if "earned" in types:
                total += wages + self_employment
            if "unearned" in types:
                total += unearned
            return total
        if frequency == "yearly":
            total = 0.0
            if "sSI" in types:
                total += ssi * 12
            if "cashAssistance" in types:
                total += tanf * 12
            return total
        return 0.0

    member.calc_gross_income.side_effect = calc_gross_income
    return member


def make_calculator(members):
    screen = Mock()
    screen.household_members.all.return_value = members
    # Acceptance Criterion 6: the calculator must make no CurrentBenefit/has_benefit
    # read for TANF at all — only a member's own reported `cashAssistance` amount.
    screen.has_base_benefit.side_effect = AssertionError("mo_rca must not read has_base_benefit for TANF")

    missing_dependencies = Mock()
    missing_dependencies.has.return_value = False

    return MoRca(screen, Mock(), {}, missing_dependencies)


def run(members):
    """Returns (eligible, value, per-member eligibility marks in input order)."""
    e = make_calculator(members).calc()
    marks = [member_eligibility.eligible for member_eligibility in e.eligible_members]
    return e.eligible, e.value, marks


class TestRegistration(TestCase):
    def test_program_code(self):
        self.assertEqual(MoRca.program_code, "mo_rca")

    def test_dependencies(self):
        """income_type is the non-obvious one: a null `type` does not raise the way a
        null `amount` or `frequency` does, so it must be declared or it is silently
        counted as unearned in full (spec.md Implementation)."""
        self.assertEqual(set(MoRca.dependencies), {"income_type", "income_amount", "income_frequency"})


class TestDependencyError(TestCase):
    def test_missing_income_field_raises(self):
        """Acceptance Criterion 11: suppressed rather than valued, not defaulted."""
        screen = Mock()
        screen.household_members.all.return_value = [make_member()]
        missing_dependencies = Mock()
        missing_dependencies.has.return_value = True

        with self.assertRaises(DependencyError):
            MoRca(screen, Mock(), {}, missing_dependencies).calc()


class TestRcaMaxPayment(TestCase):
    """Acceptance Criterion 1: the tabulated sizes 1-5, and the +$113 extension
    applied once per additional member beyond 5."""

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


class TestDataGap5Exclusion(TestCase):
    """Acceptance Criterion 3: `cashAssistanceOther` and `gifts` are excluded from
    countable unearned income. Deliberately not one of the numbered Test Scenarios
    (spec.md "Known scenario gaps") — asserted directly against the call instead."""

    def test_excludes_cash_assistance_other_and_gifts(self):
        member = make_member()
        run([member])

        unearned_calls = [
            call for call in member.calc_gross_income.call_args_list if call.args[:2] == ("monthly", ["unearned"])
        ]
        self.assertTrue(unearned_calls, "expected a monthly unearned income read")
        for call in unearned_calls:
            self.assertEqual(set(call.kwargs.get("exclude", [])), {"cashAssistanceOther", "gifts"})


class TestScenarios(TestCase):
    def test_scenario_1_single_adult_no_income(self):
        eligible, value, marks = run([make_member()])
        self.assertEqual((eligible, value, marks), (True, 4296.0, [True]))

    def test_scenario_2_single_adult_with_wages(self):
        eligible, value, marks = run([make_member(wages=1000)])
        self.assertEqual((eligible, value, marks), (True, 2476.0, [True]))

    def test_scenario_3_net_income_equals_standard_is_ineligible(self):
        """The boundary is strict: net income equal to the standard fails."""
        eligible, value, marks = run([make_member(wages=2238)])
        self.assertEqual((eligible, marks), (False, [False]))

    def test_scenario_4_one_dollar_under_the_standard(self):
        eligible, value, marks = run([make_member(wages=2234)])
        self.assertEqual((eligible, value, marks), (True, 8.0, [True]))

    def test_scenario_5_unearned_income_only(self):
        """Unearned income receives no disregard."""
        eligible, value, marks = run([make_member(unearned=400)])
        self.assertEqual((eligible, value, marks), (True, 1096.0, [True]))

    def test_scenario_6_family_of_four_earned_and_unearned(self):
        members = [
            make_member(wages=1200),
            make_member(relationship="spouse"),
            make_member(relationship="child", age=8),
            make_member(relationship="child", age=5, unearned=200),
        ]
        eligible, value, marks = run(members)
        self.assertEqual((eligible, value, marks), (True, 5012.0, [True, True, True, True]))

    def test_scenario_7_family_of_five_no_income(self):
        members = [
            make_member(),
            make_member(relationship="spouse"),
            make_member(relationship="child", age=8),
            make_member(relationship="child", age=5),
            make_member(relationship="child", age=3),
        ]
        eligible, value, marks = run(members)
        self.assertEqual((eligible, value), (True, 9736.0))

    def test_scenario_8_family_of_six_no_income(self):
        """The +$113 extension beyond the tabulated sizes."""
        members = [
            make_member(),
            make_member(relationship="spouse"),
            make_member(relationship="child", age=8),
            make_member(relationship="child", age=5),
            make_member(relationship="child", age=3),
            make_member(relationship="child", age=1),
        ]
        eligible, value, marks = run(members)
        self.assertEqual((eligible, value), (True, 10640.0))

    def test_scenario_9_two_earning_adults_exemption_is_per_member(self):
        """The $90 exemption applies per earning member, not once per case, and
        selfEmployment counts as earned."""
        members = [make_member(wages=600), make_member(relationship="spouse", self_employment=600)]
        eligible, value, marks = run(members)
        self.assertEqual((eligible, value, marks), (True, 3768.0, [True, True]))

    def test_scenario_10_member_reporting_tanf_cash_is_removed(self):
        """A single-member case that reports `cashAssistance` loses its only member
        and so pays nothing."""
        eligible, value, marks = run([make_member(tanf=400)])
        self.assertEqual((eligible, value, marks), (False, 0, [False]))

    def test_scenario_11_member_receiving_ssi_is_removed(self):
        members = [make_member(), make_member(relationship="spouse", ssi=400)]
        eligible, value, marks = run(members)
        self.assertEqual((eligible, value, marks), (True, 4296.0, [True, False]))

    def test_scenario_12_age_blindness_disability_do_not_exclude(self):
        """The SSI-pending pathway: none of age 65+, disability, or blindness is an
        exclusion — only a reported SSI amount removes a member (criterion 3)."""
        member = make_member(age=67)
        member.disabled = True
        member.visually_impaired = True
        member.long_term_disability = True

        eligible, value, marks = run([member])
        self.assertEqual((eligible, value, marks), (True, 4296.0, [True]))

    def test_scenario_13_non_monthly_income_arithmetic(self):
        """Mirrors spec.md Scenario 13's biweekly $600 normalised to $1,305.00/month."""
        eligible, value, marks = run([make_member(wages=1305)])
        self.assertEqual((eligible, value, marks), (True, 1866.0, [True]))

    def test_scenario_14_earned_income_clamped_at_zero(self):
        """Earning less than the $90 exemption contributes $0, never a negative
        amount."""
        eligible, value, marks = run([make_member(wages=50)])
        self.assertEqual((eligible, value, marks), (True, 4296.0, [True]))

    def test_scenario_15_adult_child_splits_at_the_age_18_boundary(self):
        members = [
            make_member(),
            make_member(relationship="spouse"),
            make_member(relationship="stepChild", age=18),
            make_member(relationship="child", age=17),
        ]
        eligible, value, marks = run(members)
        self.assertEqual((eligible, value, marks), (True, 11616.0, [True, True, True, True]))

    def test_scenario_16_income_summed_per_case_not_pooled(self):
        members = [
            make_member(),
            make_member(relationship="spouse"),
            make_member(relationship="child", age=18, wages=1000),
        ]
        eligible, value, marks = run(members)
        self.assertEqual((eligible, value, marks), (True, 8284.0, [True, True, True]))

    def test_scenario_17_ineligible_case_contributes_nothing(self):
        """An ineligible case's members are marked ineligible even though a sibling
        case in the same household is still payable."""
        members = [
            make_member(wages=3000),
            make_member(relationship="spouse"),
            make_member(relationship="child", age=18),
        ]
        eligible, value, marks = run(members)
        self.assertEqual((eligible, value, marks), (True, 4296.0, [False, False, True]))

    def test_scenario_18_additional_member_amount_applies_per_member(self):
        members = [
            make_member(),
            make_member(relationship="spouse"),
            make_member(relationship="child", age=8),
            make_member(relationship="child", age=5),
            make_member(relationship="child", age=3),
            make_member(relationship="child", age=1),
            make_member(relationship="child", age=9),
        ]
        eligible, value, marks = run(members)
        self.assertEqual((eligible, value), (True, 11544.0))

    def test_scenario_19_household_level_tanf_report_gates_nothing(self):
        """The tile itself is never read (asserted by `make_calculator`'s trap on
        `has_base_benefit`); only a member's own reported `cashAssistance` amount
        removes them."""
        members = [make_member(), make_member(relationship="spouse")]
        eligible, value, marks = run(members)
        self.assertEqual((eligible, value, marks), (True, 5808.0, [True, True]))

    def test_scenario_20_value_is_carried_to_the_cent(self):
        eligible, value, marks = run([make_member(unearned=400.33)])
        self.assertTrue(eligible)
        self.assertAlmostEqual(value, 1093.36, places=2)
        self.assertEqual(marks, [True])

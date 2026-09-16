"""
KS Refugee Cash Assistance.

The three tested rules are the TANF gate, the member-scoped SSI exclusion, and the
payment table. Each test names the spec.md scenario it comes from; the scenarios that
carry a dollar figure assert the value as well as the verdict, since a calculator that
returns the right verdict on the wrong case size is the failure the value scenarios
were written to catch.

Immigration status has no test: it lives on the program row's `legal_status_required`,
which the backend emits rather than evaluates (spec.md Known scenario gaps).
"""

from unittest.mock import Mock

from django.test import TestCase

from programs.framework.base import Eligibility
from programs.programs.cross_white_label.tanf.ks import KsTanf
from programs.programs.white_labels.ks.rca.calculator import KsRca
from programs.util import DependencyError


def make_member(ssi_amount=0):
    """A household member reporting `ssi_amount` of monthly SSI and nothing else."""
    member = Mock()
    member.calc_gross_income.side_effect = lambda frequency, types: (
        ssi_amount * 12 if "sSI" in types and frequency == "yearly" else 0
    )
    return member


def make_calculator(members=None, tanf_eligible=False, reports_tanf=False, ssi_tile=False):
    """`tanf_eligible=None` models ks_tanf never being calculated."""
    members = members if members is not None else [make_member()]

    data = {}
    if tanf_eligible is not None:
        tanf = Eligibility()
        tanf.eligible = tanf_eligible
        data["ks_tanf"] = tanf

    screen = Mock()
    screen.household_size = len(members)
    screen.household_members.all.return_value = members
    screen.has_base_benefit.side_effect = lambda base: {"tanf": reports_tanf, "ssi": ssi_tile}[base]
    # Household-level SSI income, which `screen_reports_ssi_without_amount` reads to tell
    # a tile with a reported amount from one without.
    screen.calc_gross_income.side_effect = lambda frequency, types: sum(
        m.calc_gross_income(frequency, types) for m in members
    )

    missing_dependencies = Mock()
    missing_dependencies.has.return_value = False

    return KsRca(screen, Mock(), data, missing_dependencies)


def run(**kwargs):
    """Returns (eligible, value) the way `calc` composes them."""
    e = make_calculator(**kwargs).calc()
    return e.eligible, e.value


class TestRegistration(TestCase):
    def test_program_code(self):
        self.assertEqual(KsRca.program_code, "ks_rca")

    def test_declares_ks_tanf_screener_dependencies(self):
        """The strict gate is only sound if RCA is uncalculable wherever TANF is."""
        tanf_fields = {field for pe_input in KsTanf.pe_inputs for field in pe_input.dependencies}
        self.assertTrue(tanf_fields.issubset(set(KsRca.dependencies)))

    def test_ks_tanf_is_calculated_before_ks_rca(self):
        """An unlisted program sorts last in arbitrary relative order, so without this the
        strict gate would raise on households it can answer for."""
        from screener.views import CALC_ORDER

        self.assertIn("ks_tanf", CALC_ORDER)
        self.assertNotIn("ks_rca", CALC_ORDER)


class TestValueTable(TestCase):
    """Scenarios 1-6: the payment standard across tabulated and extrapolated case sizes."""

    def test_scenario_1_single_adult(self):
        self.assertEqual(run(members=[make_member()]), (True, 168))

    def test_scenario_2_two_adults(self):
        self.assertEqual(run(members=[make_member() for _ in range(2)]), (True, 263))

    def test_scenario_3_three_adults_with_earned_income(self):
        """Income neither gates eligibility nor reduces the figure shown: Kansas's income
        standard and its monthly reduction formula are both unpublished (Data Gap 1)."""
        earner = make_member()
        earner.calc_gross_income.side_effect = lambda frequency, types: (24_000 if "sSI" not in types else 0)
        self.assertEqual(run(members=[earner, make_member(), make_member()]), (True, 349))

    def test_scenario_4_four_adults_last_tabulated_size(self):
        self.assertEqual(run(members=[make_member() for _ in range(4)]), (True, 421))

    def test_scenario_5_five_adults_first_increment(self):
        self.assertEqual(run(members=[make_member() for _ in range(5)]), (True, 482))

    def test_scenario_6_nine_adults_repeated_increment(self):
        self.assertEqual(run(members=[make_member() for _ in range(9)]), (True, 726))

    def test_every_tabulated_size_matches_the_increment_rule(self):
        """Sizes 5-8 are in the table and also reachable by extrapolation; they must agree,
        or the value depends on which branch runs."""
        for size in range(4, 9):
            with self.subTest(size=size):
                self.assertEqual(
                    KsRca.payment_standard[size],
                    KsRca.payment_standard[4] + 61 * (size - 4),
                )


class TestTanfGate(TestCase):
    """Scenarios 7-8: the two halves of criterion 2."""

    def test_scenario_7_tanf_eligible_household_is_excluded(self):
        """The harder half — ineligibility, not merely non-receipt."""
        eligible, _ = run(tanf_eligible=True, reports_tanf=False)
        self.assertFalse(eligible)

    def test_scenario_8_household_reporting_tanf_receipt_is_excluded(self):
        """Isolated: the household is TANF-ineligible, so only the tile can produce this."""
        eligible, _ = run(tanf_eligible=False, reports_tanf=True)
        self.assertFalse(eligible)

    def test_uncalculated_tanf_raises_rather_than_guessing(self):
        """Absence is not 'not TANF-eligible' — reading it that way would offer RCA to a
        household whose TANF answer is unknown."""
        with self.assertRaises(DependencyError):
            run(tanf_eligible=None)

    def test_reported_receipt_short_circuits_the_calculated_read(self):
        """Already having TANF settles the exclusion, so an uncalculated ks_tanf cannot
        raise."""
        eligible, _ = run(tanf_eligible=None, reports_tanf=True)
        self.assertFalse(eligible)


class TestSsiExclusion(TestCase):
    """Scenarios 9-13: criterion 3, which is the member's exclusion rather than the
    household's."""

    def test_scenario_9_sole_member_receiving_ssi(self):
        eligible, _ = run(members=[make_member(ssi_amount=700)])
        self.assertFalse(eligible)

    def test_scenario_10_one_of_two_members_receiving_ssi(self):
        """The regression test for member scope: a household-wide exclusion returns
        ineligible here, and a value read off household_size returns $263."""
        members = [make_member(), make_member(ssi_amount=700)]
        self.assertEqual(run(members=members), (True, 168))

    def test_scenario_11_ssi_tile_without_amount_in_a_two_member_household(self):
        """The tile names no recipient and nothing tells the two members apart, so it
        excludes nobody."""
        members = [make_member(), make_member()]
        self.assertEqual(run(members=members, ssi_tile=True), (True, 263))

    def test_scenario_12_ssi_eligible_but_not_receiving(self):
        """SSI disqualifies on receipt only. A dependency on SSI *eligibility* would deny
        RCA to every applicant awaiting a determination, which 45 CFR 400.51(b)(1)(ii)
        forbids."""
        self.assertEqual(run(members=[make_member()]), (True, 168))

    def test_scenario_13_ssi_tile_without_amount_in_a_one_member_household(self):
        """The other side of the boundary: with one member the tile identifies them."""
        eligible, _ = run(members=[make_member()], ssi_tile=True)
        self.assertFalse(eligible)

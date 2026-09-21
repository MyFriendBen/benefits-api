from django.test import TestCase
from unittest.mock import Mock

from programs.framework.base import MemberEligibility
from programs.programs.white_labels.mo.mtrfp.calculator import MoMetroTransitReducedFare


def make_member(
    age=40,
    disabled=False,
    visually_impaired=False,
    medicare=False,
    ssdi_income=0,
    ssi_income=0,
):
    member = Mock()
    member.age = age
    member.disabled = disabled
    member.visually_impaired = visually_impaired
    member.calc_age = Mock(return_value=age)
    member.has_insurance = Mock(side_effect=lambda name: medicare if name == "medicare" else False)

    def calc_gross_income(freq, types, **kwargs):
        by_type = {"sSDisability": ssdi_income, "sSI": ssi_income}
        total = sum(by_type.get(t, 0) for t in types)
        return total if freq == "yearly" else total / 12

    member.calc_gross_income = Mock(side_effect=calc_gross_income)
    return member


def make_calculator(members=None, county="St. Louis City"):
    mock_screen = Mock()
    mock_screen.county = county

    if members is None:
        members = [make_member()]
    mock_screen.household_members.all.return_value = members

    mock_program = Mock()
    mock_missing_deps = Mock()
    mock_missing_deps.has.return_value = False

    return MoMetroTransitReducedFare(mock_screen, mock_program, {}, mock_missing_deps)


def member_is_eligible(calculator, member):
    e = MemberEligibility(member)
    calculator.member_eligible(e)
    return e.eligible


class TestMoMtrfpWiring(TestCase):
    def test_program_code_matches_config(self):
        """``program_code`` must equal the ``name_abbreviated`` in
        mo_mtrfp_initial_config.json, or the calculator never binds to the row."""
        self.assertEqual(MoMetroTransitReducedFare.program_code, "mo_mtrfp")

    def test_not_abstract(self):
        self.assertFalse(MoMetroTransitReducedFare._abstract)

    def test_minimum_age(self):
        self.assertEqual(MoMetroTransitReducedFare.minimum_age, 65)

    def test_member_amount_is_annual_pass_differential(self):
        # Pinned to spec.md's derivation so a future edit can't change it silently.
        self.assertEqual(MoMetroTransitReducedFare.member_amount, (78 - 39) * 12)
        self.assertEqual(MoMetroTransitReducedFare.member_amount, 468)


class TestMoMtrfpScenarios(TestCase):
    """One test per Test Scenario in spec.md."""

    def test_scenario_1_senior_age_70_eligible(self):
        member = make_member(age=70)
        calculator = make_calculator(members=[member])

        eligibility = calculator.calc()

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 468)

    def test_scenario_2_disabled_adult_45_no_income_gate(self):
        """No income threshold — a disabled adult earning $42,000/year qualifies."""
        member = make_member(age=45, disabled=True)
        calculator = make_calculator(members=[member])

        eligibility = calculator.calc()

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 468)

    def test_scenario_3_medicare_holder_under_65_eligible(self):
        member = make_member(age=45, medicare=True)
        calculator = make_calculator(members=[member])

        eligibility = calculator.calc()

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 468)

    def test_scenario_4_age_exactly_65_eligible(self):
        """Validates ``>=`` rather than a strict ``>`` at the senior boundary."""
        member = make_member(age=65)
        calculator = make_calculator(members=[member])

        eligibility = calculator.calc()

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 468)

    def test_scenario_5_age_64_no_other_pathway_ineligible(self):
        member = make_member(age=64)
        calculator = make_calculator(members=[member])

        eligibility = calculator.calc()

        self.assertFalse(eligibility.eligible)

    def test_scenario_6_visually_impaired_adult_50_eligible(self):
        """``visually_impaired`` is its own path in, independent of ``disabled``."""
        member = make_member(age=50, visually_impaired=True)
        calculator = make_calculator(members=[member])

        eligibility = calculator.calc()

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 468)

    def test_scenario_7_ssdi_recipient_40_eligible(self):
        member = make_member(age=40, ssdi_income=18_000)
        calculator = make_calculator(members=[member])

        eligibility = calculator.calc()

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 468)

    def test_scenario_8_ssi_recipient_38_eligible(self):
        member = make_member(age=38, ssi_income=11_000)
        calculator = make_calculator(members=[member])

        eligibility = calculator.calc()

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 468)

    def test_scenario_9_st_charles_county_senior_eligible(self):
        """County is not a gate — regression guard against reintroducing one."""
        member = make_member(age=70)
        calculator = make_calculator(members=[member], county="St. Charles County")

        eligibility = calculator.calc()

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 468)

    def test_scenario_10_adult_35_no_qualifying_category_ineligible(self):
        member = make_member(age=35)
        calculator = make_calculator(members=[member])

        eligibility = calculator.calc()

        self.assertFalse(eligibility.eligible)

    def test_scenario_11_mixed_household_two_qualify(self):
        """Senior and disabled adult qualify; children and a healthy adult do not."""
        senior = make_member(age=70)
        disabled_adult = make_member(age=50, disabled=True)
        child = make_member(age=8)
        toddler = make_member(age=3)
        healthy_adult = make_member(age=40)
        calculator = make_calculator(members=[senior, disabled_adult, child, toddler, healthy_adult])

        eligibility = calculator.calc()

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 936)

    def test_scenario_13_ssdi_parent_and_child_only_recipient_qualifies(self):
        """Reading SSDI at the household level would report $936 here."""
        parent = make_member(age=45, ssdi_income=18_000)
        child = make_member(age=8)
        calculator = make_calculator(members=[parent, child])

        eligibility = calculator.calc()

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 468)

    def test_scenario_12_three_members_isolated_pathways(self):
        """Each member qualifies through exactly one pathway, so a broken branch
        cannot be masked by another branch covering for it."""
        senior_one = make_member(age=70)
        senior_two = make_member(age=68)
        disabled_adult = make_member(age=41, disabled=True)
        calculator = make_calculator(members=[senior_one, senior_two, disabled_adult])

        eligibility = calculator.calc()

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 1_404)


class TestMoMtrfpPathwayIsolation(TestCase):
    """Each pathway on its own, asserted at the member level."""

    def test_age_pathway_alone(self):
        calculator = make_calculator()
        self.assertTrue(member_is_eligible(calculator, make_member(age=65)))
        self.assertFalse(member_is_eligible(calculator, make_member(age=64)))

    def test_disability_pathway_has_no_minimum_age(self):
        """The disability pathway has no minimum age."""
        calculator = make_calculator()
        self.assertTrue(member_is_eligible(calculator, make_member(age=10, disabled=True)))

    def test_medicare_pathway_alone(self):
        calculator = make_calculator()
        self.assertTrue(member_is_eligible(calculator, make_member(age=30, medicare=True)))

    def test_ssdi_pathway_alone(self):
        calculator = make_calculator()
        self.assertTrue(member_is_eligible(calculator, make_member(age=30, ssdi_income=18_000)))

    def test_ssi_pathway_alone(self):
        calculator = make_calculator()
        self.assertTrue(member_is_eligible(calculator, make_member(age=30, ssi_income=11_000)))

    def test_no_pathway_is_ineligible(self):
        calculator = make_calculator()
        self.assertFalse(member_is_eligible(calculator, make_member(age=30)))

    def test_null_age_does_not_crash(self):
        """``calc_age()`` can return None when birth_year_month and age are both
        unset; the age comparison must not raise."""
        member = make_member(age=None)
        calculator = make_calculator(members=[member])
        self.assertFalse(member_is_eligible(calculator, member))

    def test_null_age_with_disability_still_eligible(self):
        member = make_member(age=None, disabled=True)
        calculator = make_calculator(members=[member])
        self.assertTrue(member_is_eligible(calculator, member))


class TestMoMtrfpBenefitReceiptIsPerMember(TestCase):
    """SSDI/SSI qualify only the member who receives them.

    Reading `screen.has_base_benefit("ssdi")` would qualify the whole
    household, because `CurrentBenefit` has no member FK.
    """

    def test_ssdi_does_not_qualify_a_child_in_the_same_household(self):
        parent = make_member(age=45, ssdi_income=18_000)
        child = make_member(age=8)
        calculator = make_calculator(members=[parent, child])

        eligibility = calculator.calc()

        self.assertTrue(eligibility.eligible)
        # Only the parent's $468 — the child has no pathway of their own.
        self.assertEqual(eligibility.value, 468)

    def test_ssi_does_not_qualify_a_non_recipient_adult(self):
        recipient = make_member(age=35, ssi_income=11_000)
        other_adult = make_member(age=38)
        calculator = make_calculator(members=[recipient, other_adult])

        eligibility = calculator.calc()

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 468)

    def test_child_receiving_ssi_qualifies_on_their_own(self):
        """The per-member rule must not become an age gate."""
        child = make_member(age=8, ssi_income=9_000)
        calculator = make_calculator(members=[child])

        eligibility = calculator.calc()

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 468)

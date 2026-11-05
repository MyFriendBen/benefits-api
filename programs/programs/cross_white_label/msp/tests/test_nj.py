"""
NJ Medicare Savings Programs (``NjMedicareSavings``): one test per Test Scenario in the NJ spec
(``programs/cross_white_label/msp/nj/msp_nj_spec.md`` in program-ops), run end to end through
real screener rows. The federal rules are tested against stand-in states in
``test_federal_base.py``.

The spec states the Part B premium to the cent ($202.90/month); values are annual and rounded
half-up to whole dollars, so these expect $2,435 a member.

Each test also asserts the group the member qualified through, so the SLMB/QI boundary at
120% of poverty (scenarios 5, 20 and 21) is covered even though SLMB and QI pay the same.
"""

from typing import Optional

from programs.framework.base import Eligibility
from programs.programs.cross_white_label.msp.federal_base import MspFederalBase
from programs.programs.cross_white_label.msp.nj import NjMedicareSavings
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from screener.models import HouseholdMember, Screen

PART_B = 2_435  # $202.90 × 12, rounded


class TestNjMedicareSavings(CustomCalculatorTestCase):
    calculator_class = NjMedicareSavings
    white_label_code = "nj"
    state_code = "NJ"
    fpl_year = "2026"
    default_zipcode = "08608"
    default_county = "Mercer County"

    def screen(self, size: int = 1, assets: int = 2_000) -> Screen:
        return self.make_screen(household_size=size, household_assets=assets)

    def person(
        self,
        screen: Screen,
        relationship: str = "headOfHousehold",
        age: int = 70,
        medicare: bool = True,
        medicaid: bool = False,
        social_security: float = 0,
        social_security_yearly: int = 0,
        wages: float = 0,
        disabled: bool = False,
    ) -> HouseholdMember:
        member = self.add_member(screen, relationship, age, disabled=disabled)
        if social_security:
            self.add_income(member, social_security, income_type="sSRetirement")
        if social_security_yearly:
            self.add_income(member, social_security_yearly, income_type="sSRetirement", frequency="yearly")
        if wages:
            self.add_income(member, wages, income_type="wages")
        if medicare or medicaid:
            self.add_insurance(member, none=False, medicare=medicare, medicaid=medicaid)
        return member

    def run_calc(self, screen: Screen) -> tuple[MspFederalBase, Eligibility]:
        calculator = self.make_calculator(screen)
        return calculator, calculator.calc()

    def assert_result(
        self, screen: Screen, routes: dict[HouseholdMember, Optional[str]], eligible_members: Optional[int] = None
    ) -> None:
        calculator, e = self.run_calc(screen)
        for member, route in routes.items():
            self.assertEqual(calculator.member_routes.get(member.id), route, member.relationship)

        count = sum(1 for route in routes.values() if route) if eligible_members is None else eligible_members
        self.assertEqual(e.eligible, count > 0)
        self.assertEqual(e.value, count * PART_B)

    def test_registration(self):
        self.assertEqual(NjMedicareSavings.program_code, "nj_medicare_savings")
        self.assertEqual(NjMedicareSavings.family_size_method, "individual_or_couple")
        self.assertFalse(NjMedicareSavings.evaluate_qdwi)

    def test_scenario_1_qmb_golden_path(self):
        screen = self.screen()
        self.assert_result(screen, {self.person(screen, social_security=1_000): "qmb"})

    def test_scenario_2_single_person_at_the_qmb_income_limit(self):
        screen = self.screen()
        self.assert_result(screen, {self.person(screen, social_security=1_350): "qmb"})

    def test_scenario_3_single_person_1_over_the_qmb_limit_lands_on_slmb(self):
        screen = self.screen()
        self.assert_result(screen, {self.person(screen, social_security=1_351): "slmb"})

    def test_scenario_4_single_person_just_under_slmbs_upper_bound(self):
        screen = self.screen()
        self.assert_result(screen, {self.person(screen, social_security=1_615): "slmb"})

    def test_scenario_5_single_person_at_120_percent_lands_on_qi(self):
        screen = self.screen()
        self.assert_result(screen, {self.person(screen, social_security=1_616): "qi"})

    def test_scenario_6_single_person_at_exactly_135_percent_under_qis_rounded_limit(self):
        screen = self.screen()
        self.assert_result(screen, {self.person(screen, social_security_yearly=21_786): "qi"})

    def test_scenario_7_single_person_at_qis_rounded_limit(self):
        screen = self.screen()
        self.assert_result(screen, {self.person(screen, social_security=1_816): None})

    def test_scenario_8_qi_band_applicant_who_has_medicaid(self):
        screen = self.screen()
        self.assert_result(screen, {self.person(screen, medicaid=True, social_security=1_700): None})

    def test_scenario_9_qmb_band_applicant_who_has_medicaid(self):
        screen = self.screen()
        self.assert_result(screen, {self.person(screen, medicaid=True, social_security=1_000): "qmb"})

    def test_scenario_10_single_person_at_the_resource_limit(self):
        screen = self.screen(assets=9_950)
        self.assert_result(screen, {self.person(screen, social_security=1_000): "qmb"})

    def test_scenario_11_single_person_1_over_the_resource_limit(self):
        screen = self.screen(assets=9_951)
        self.assert_result(screen, {self.person(screen, social_security=1_000): None})

    def couple(self, head_income: float, spouse_income: float, assets: int = 2_000) -> tuple[Screen, list]:
        screen = self.screen(size=2, assets=assets)
        members = [
            self.person(screen, social_security=head_income),
            self.person(screen, "spouse", social_security=spouse_income),
        ]
        return screen, members

    def test_scenario_12_couple_at_the_couple_resource_limit(self):
        screen, (head, spouse) = self.couple(850, 850, assets=14_910)
        self.assert_result(screen, {head: "qmb", spouse: "qmb"})

    def test_scenario_13_couple_1_over_the_couple_resource_limit(self):
        screen, (head, spouse) = self.couple(850, 850, assets=14_911)
        self.assert_result(screen, {head: None, spouse: None})

    def test_scenario_14_couple_at_the_two_person_qmb_income_limit(self):
        screen, (head, spouse) = self.couple(1_000, 824)
        self.assert_result(screen, {head: "qmb", spouse: "qmb"})

    def test_scenario_15_couple_1_over_the_two_person_qmb_limit_lands_on_slmb(self):
        screen, (head, spouse) = self.couple(1_000, 825)
        self.assert_result(screen, {head: "slmb", spouse: "slmb"})

    def test_scenario_16_older_adult_without_medicare(self):
        screen = self.screen()
        self.assert_result(screen, {self.person(screen, medicare=False, social_security=1_000): None})

    def test_scenario_17_working_medicare_enrollee_at_the_qmb_limit_on_earnings(self):
        screen = self.screen()
        self.assert_result(screen, {self.person(screen, age=66, wages=2_745): "qmb"})

    def test_scenario_18_qdwi_held(self):
        screen = self.screen(assets=1_000)
        member = self.person(screen, age=64, medicare=False, wages=2_000, disabled=True)
        self.assert_result(screen, {member: None})

    def test_scenario_19_an_slmb_spouse_and_a_disabled_working_spouse(self):
        screen = self.screen(size=2, assets=3_000)
        head = self.person(screen, social_security=900)
        spouse = self.person(screen, "spouse", age=62, medicare=False, wages=2_000, disabled=True)
        self.assert_result(screen, {head: "slmb", spouse: None})

    def test_scenario_20_couple_1_under_the_two_person_slmb_limit(self):
        screen, (head, spouse) = self.couple(1_300, 883)
        self.assert_result(screen, {head: "slmb", spouse: "slmb"})

    def test_scenario_21_couple_at_the_two_person_120_percent_line_lands_on_qi(self):
        screen, (head, spouse) = self.couple(1_300, 884)
        self.assert_result(screen, {head: "qi", spouse: "qi"})

    def test_scenario_22_couple_under_the_two_person_qi_limit(self):
        screen, (head, spouse) = self.couple(1_300, 1_154)
        self.assert_result(screen, {head: "qi", spouse: "qi"})

    def test_scenario_23_couple_over_the_two_person_qi_limit(self):
        screen, (head, spouse) = self.couple(1_300, 1_156)
        self.assert_result(screen, {head: None, spouse: None})

    def test_scenario_24_slmb_band_applicant_who_has_medicaid(self):
        screen = self.screen()
        self.assert_result(screen, {self.person(screen, medicaid=True, social_security=1_400): "slmb"})

    def test_scenario_25_slmb_band_applicant_without_medicare(self):
        screen = self.screen()
        self.assert_result(screen, {self.person(screen, medicare=False, social_security=1_400): None})

    def test_scenario_26_qi_band_applicant_without_medicare(self):
        screen = self.screen()
        self.assert_result(screen, {self.person(screen, medicare=False, social_security=1_700): None})

    def test_scenario_27_slmb_band_applicant_1_over_the_resource_limit(self):
        screen = self.screen(assets=9_951)
        self.assert_result(screen, {self.person(screen, social_security=1_400): None})

    def test_scenario_28_qi_band_applicant_1_over_the_resource_limit(self):
        screen = self.screen(assets=9_951)
        self.assert_result(screen, {self.person(screen, social_security=1_700): None})

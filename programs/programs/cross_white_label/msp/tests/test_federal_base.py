"""
Unit tests for the MFB Medicare Savings Programs base (``MspFederalBase``).

Exercised through test-only subclasses that set what a state sets. The base spec
(``programs/cross_white_label/msp/base/msp_base_spec.md`` in program-ops) has no scenarios of
its own, so each rule in its sections 3, 4 and 7 gets a test here; NJ's spec scenarios run end
to end in ``test_nj.py``.

The spec states the Part B premium to the cent ($202.90/month); values are annual and rounded
half-up to whole dollars, so one member is $2,435 a year.
"""

from decimal import Decimal
from typing import Optional

from programs.framework.base import Eligibility
from programs.programs.cross_white_label.msp.federal_base import MspFederalBase
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from programs.util import Dependencies, DependencyError
from screener.models import HouseholdMember, Screen

PART_B = 2_435  # $202.90 × 12, rounded
PART_A = 6_780  # $565 × 12


class StandInMsp(MspFederalBase):
    program_code = "test_msp"
    family_size_method = "individual_or_couple"


class ExtraHelpMsp(MspFederalBase):
    program_code = "test_msp_extra_help"
    family_size_method = "extra_help"


class QdwiMsp(MspFederalBase):
    program_code = "test_msp_qdwi"
    family_size_method = "individual_or_couple"
    evaluate_qdwi = True


class MspBaseTestCase(CustomCalculatorTestCase):
    calculator_class = StandInMsp
    fpl_year = "2026"

    def person(
        self,
        screen: Screen,
        relationship: str = "headOfHousehold",
        age: int = 70,
        medicare: bool = True,
        medicaid: bool = False,
        social_security: float = 0,
        wages: float = 0,
        **kwargs,
    ) -> HouseholdMember:
        member = self.add_member(screen, relationship, age, **kwargs)
        if social_security:
            self.add_income(member, social_security, income_type="sSRetirement")
        if wages:
            self.add_income(member, wages, income_type="wages")
        if medicare or medicaid:
            self.add_insurance(member, none=False, medicare=medicare, medicaid=medicaid)
        return member

    def run_calc(self, screen: Screen) -> tuple[MspFederalBase, Eligibility]:
        calculator = self.make_calculator(screen)
        return calculator, calculator.calc()

    def single(self, assets: int = 2_000, **kwargs) -> tuple[MspFederalBase, Eligibility, HouseholdMember]:
        screen = self.make_screen(household_assets=assets)
        member = self.person(screen, **kwargs)
        calculator, e = self.run_calc(screen)
        return calculator, e, member

    def disabled_worker(self, **kwargs) -> tuple[MspFederalBase, Eligibility, HouseholdMember]:
        kwargs.setdefault("age", 64)
        kwargs.setdefault("wages", 2_000)
        kwargs.setdefault("assets", 1_000)
        kwargs.setdefault("disabled", True)
        return self.single(medicare=False, **kwargs)

    def assert_route(self, calculator: MspFederalBase, member: HouseholdMember, route: Optional[str]) -> None:
        self.assertEqual(calculator.member_routes.get(member.id), route)


class TestRegistration(MspBaseTestCase):
    def test_base_is_abstract(self):
        self.assertTrue(MspFederalBase._abstract)
        self.assertFalse(StandInMsp._abstract)

    def test_qdwi_held_by_default(self):
        self.assertFalse(MspFederalBase.evaluate_qdwi)

    def test_constants(self):
        self.assertEqual(MspFederalBase.resource_limit, {False: 9_950, True: 14_910})
        self.assertEqual(MspFederalBase.qdwi_resource_limit, {False: 4_000, True: 6_000})
        self.assertEqual(MspFederalBase.part_b_premium, Decimal("202.90"))
        self.assertEqual(MspFederalBase.part_a_full_premium, Decimal(565))
        self.assertEqual((MspFederalBase.sga_monthly, MspFederalBase.sga_monthly_blind), (1_690, 2_830))


class TestIncomeLimits(MspBaseTestCase):
    """Each limit is the percentage of the monthly poverty line, rounded up to the dollar."""

    def limits(self, size: int) -> list[int]:
        calculator = self.make_calculator(self.make_screen())
        return [
            calculator.income_limit(p, size)
            for p in (StandInMsp.qmb_percent, StandInMsp.slmb_percent, StandInMsp.qi_percent, StandInMsp.qdwi_percent)
        ]

    def test_one_person(self):
        # 100%, 120% and 200% of $1,330 are whole; 135% is $1,795.50, rounded up.
        self.assertEqual(self.limits(1), [1_330, 1_596, 1_796, 2_660])

    def test_two_people(self):
        # $21,640 / 12 = $1,803.33: 100% → $1,804, 135% $2,434.50 → $2,435, 200% $3,606.67 → $3,607.
        self.assertEqual(self.limits(2), [1_804, 2_164, 2_435, 3_607])

    def test_matches_the_published_limits_less_the_20_dollar_disregard(self):
        # SSA POMS HI 00815.023 (2026): QMB $1,350/$1,824, SLMB $1,616/$2,184, QI $1,816/$2,455.
        self.assertEqual([x + 20 for x in self.limits(1)[:3]], [1_350, 1_616, 1_816])
        self.assertEqual([x + 20 for x in self.limits(2)[:3]], [1_824, 2_184, 2_455])


class TestCountableIncome(MspBaseTestCase):
    def countable(self, **incomes: float) -> Decimal:
        screen = self.make_screen()
        member = self.add_member(screen, "headOfHousehold", 70)
        for income_type, amount in incomes.items():
            self.add_income(member, amount, income_type=income_type)
        return self.make_calculator(screen).countable_income(member)

    def test_general_disregard_comes_off_unearned_income(self):
        self.assertEqual(self.countable(sSRetirement=1_000), Decimal(980))

    def test_earned_income_after_20_and_65_disregards_then_halved(self):
        self.assertEqual(self.countable(wages=2_745), Decimal(1_330))

    def test_unused_general_disregard_carries_to_earnings(self):
        # $10 unearned uses $10 of the $20; the other $10 comes off earnings.
        self.assertEqual(self.countable(sSRetirement=10, wages=1_075), Decimal(500))

    def test_no_general_disregard_against_ssi(self):
        self.assertEqual(self.countable(sSI=500), Decimal(500))

    def test_no_general_disregard_against_cash_assistance(self):
        self.assertEqual(self.countable(cashAssistance=300, cashAssistanceOther=100), Decimal(400))

    def test_investment_income_not_counted(self):
        self.assertEqual(self.countable(sSRetirement=1_000, investment=400), Decimal(980))

    def test_earnings_below_the_disregards_count_nothing(self):
        self.assertEqual(self.countable(wages=60), Decimal(0))

    def test_yearly_income_kept_exact(self):
        # $21,786 a year is exactly $1,815.50 a month.
        screen = self.make_screen()
        member = self.add_member(screen, "headOfHousehold", 70)
        self.add_income(member, 21_786, income_type="sSRetirement", frequency="yearly")
        self.assertEqual(self.make_calculator(screen).countable_income(member), Decimal("1795.50"))


class TestRoutes(MspBaseTestCase):
    def test_qmb_at_the_limit(self):
        calculator, e, member = self.single(social_security=1_350)
        self.assertTrue(e.eligible)
        self.assert_route(calculator, member, "qmb")

    def test_slmb_a_dollar_over_qmb(self):
        calculator, e, member = self.single(social_security=1_351)
        self.assert_route(calculator, member, "slmb")

    def test_slmb_just_under_120_percent(self):
        calculator, e, member = self.single(social_security=1_615)
        self.assert_route(calculator, member, "slmb")

    def test_qi_at_120_percent_since_slmb_top_is_strict(self):
        calculator, e, member = self.single(social_security=1_616)
        self.assert_route(calculator, member, "qi")

    def test_qi_under_the_rounded_135_percent_limit(self):
        calculator, e, member = self.single(social_security=1_815.50)
        self.assert_route(calculator, member, "qi")

    def test_nothing_at_the_rounded_qi_limit_since_qi_top_is_strict(self):
        calculator, e, member = self.single(social_security=1_816)
        self.assertFalse(e.eligible)
        self.assert_route(calculator, member, None)

    def test_medicare_required(self):
        calculator, e, member = self.single(social_security=1_000, medicare=False)
        self.assertFalse(e.eligible)

    def test_qi_excluded_by_medicaid(self):
        calculator, e, member = self.single(social_security=1_700, medicaid=True)
        self.assertFalse(e.eligible)

    def test_qmb_and_slmb_not_excluded_by_medicaid(self):
        for income, route in ((1_000, "qmb"), (1_400, "slmb")):
            with self.subTest(route=route):
                calculator, e, member = self.single(social_security=income, medicaid=True)
                self.assert_route(calculator, member, route)


class TestResources(MspBaseTestCase):
    def test_single_at_the_limit(self):
        self.assertTrue(self.single(assets=9_950, social_security=1_000)[1].eligible)

    def test_single_a_dollar_over(self):
        self.assertFalse(self.single(assets=9_951, social_security=1_000)[1].eligible)

    def test_resource_limit_applies_on_every_route(self):
        for income in (1_000, 1_400, 1_700):
            with self.subTest(income=income):
                self.assertFalse(self.single(assets=9_951, social_security=income)[1].eligible)

    def test_unknown_assets_read_as_none(self):
        screen = self.make_screen()
        screen.household_assets = None
        screen.save()
        self.person(screen, social_security=1_000)
        self.assertTrue(self.run_calc(screen)[1].eligible)

    def couple(self, assets: int, relationship: str = "spouse") -> Eligibility:
        screen = self.make_screen(household_size=2, household_assets=assets)
        self.person(screen, social_security=850)
        self.person(screen, relationship, social_security=850)
        return self.run_calc(screen)[1]

    def test_couple_at_the_couple_limit(self):
        e = self.couple(14_910)
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 2 * PART_B)

    def test_couple_a_dollar_over(self):
        self.assertFalse(self.couple(14_911).eligible)

    def test_domestic_partners_measured_against_the_single_limit(self):
        self.assertFalse(self.couple(10_000, relationship="domesticPartner").eligible)


class TestSpouse(MspBaseTestCase):
    def pair(self, first: str, second: str, income: float) -> tuple[MspFederalBase, Eligibility, list]:
        screen = self.make_screen(household_size=3)
        self.person(screen, "headOfHousehold", age=45, medicare=False)
        members = [
            self.person(screen, first, social_security=income),
            self.person(screen, second, social_security=income),
        ]
        calculator, e = self.run_calc(screen)
        return calculator, e, members

    def test_head_and_spouse_combined(self):
        screen = self.make_screen(household_size=2)
        head = self.person(screen, social_security=1_000)
        spouse = self.person(screen, "spouse", social_security=1_000)
        calculator = self.make_calculator(screen)
        self.assertEqual(calculator.countable_income(head), Decimal(1_980))
        self.assertEqual(calculator.family_size(spouse), 2)

    def test_two_parents_of_the_head_are_a_couple(self):
        # $1,000 each: $1,980 combined, over the two-person QMB limit of $1,804 → SLMB.
        calculator, e, members = self.pair("parent", "parent", 1_000)
        for member in members:
            self.assert_route(calculator, member, "slmb")

    def test_domestic_partner_is_not_a_spouse(self):
        screen = self.make_screen(household_size=2)
        head = self.person(screen, social_security=1_000)
        partner = self.person(screen, "domesticPartner", social_security=1_000)
        calculator = self.make_calculator(screen)
        self.assertIsNone(calculator.spouse_of(head))
        self.assertEqual(calculator.countable_income(partner), Decimal(980))

    def test_unrelated_members_are_not_a_couple(self):
        calculator, e, members = self.pair("sisterOrBrother", "sisterOrBrother", 1_000)
        for member in members:
            self.assert_route(calculator, member, "qmb")


class TestFamilySize(MspBaseTestCase):
    calculator_class = ExtraHelpMsp

    def household(self) -> tuple[Screen, HouseholdMember, HouseholdMember]:
        screen = self.make_screen(household_size=3)
        head = self.person(screen, social_security=1_500)
        child = self.person(screen, "child", age=10, medicare=False)
        grandparent = self.person(screen, "grandParent", social_security=1_500)
        return screen, head, grandparent

    def test_extra_help_counts_the_heads_dependents(self):
        screen, head, _ = self.household()
        self.assertEqual(self.make_calculator(screen).family_size(head), 2)

    def test_extra_help_counts_none_for_another_applicant(self):
        screen, _, grandparent = self.household()
        self.assertEqual(self.make_calculator(screen).family_size(grandparent), 1)

    def test_dependents_lift_the_limit(self):
        # $1,480 countable: over one person's $1,330, under two people's $1,804.
        screen, head, grandparent = self.household()
        calculator, e = self.run_calc(screen)
        self.assert_route(calculator, head, "qmb")
        self.assert_route(calculator, grandparent, "slmb")

    def test_individual_or_couple_ignores_dependents(self):
        screen, head, _ = self.household()
        self.assertEqual(StandInMsp(screen, self.program, {}, Dependencies()).family_size(head), 1)


class TestQdwiHeld(MspBaseTestCase):
    def test_not_evaluated_by_default(self):
        calculator, e, member = self.disabled_worker()
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)


class TestQdwiEvaluated(MspBaseTestCase):
    """The rules a state turning QDWI on gets."""

    calculator_class = QdwiMsp
    program_code = "test_msp_qdwi"

    def test_eligible_disabled_worker(self):
        calculator, e, member = self.disabled_worker()
        self.assertTrue(e.eligible)
        self.assert_route(calculator, member, "qdwi")
        self.assertEqual(e.value, PART_A)

    def test_must_be_under_65(self):
        self.assertFalse(self.disabled_worker(age=65)[1].eligible)

    def test_must_be_disabled(self):
        self.assertFalse(self.disabled_worker(disabled=False)[1].eligible)

    def test_earnings_must_exceed_sga(self):
        self.assertFalse(self.disabled_worker(wages=1_690)[1].eligible)

    def test_blind_sga_is_higher(self):
        self.assertFalse(self.disabled_worker(wages=2_000, visually_impaired=True)[1].eligible)

    def test_no_ssdi(self):
        screen = self.make_screen(household_assets=1_000)
        member = self.person(screen, age=64, medicare=False, wages=2_000, disabled=True)
        self.add_income(member, 100, income_type="sSDisability")
        self.assertFalse(self.run_calc(screen)[1].eligible)

    def test_income_at_or_below_200_percent(self):
        # $5,405 wages: ($5,405 − $85) ÷ 2 = $2,660, exactly 200% — POMS's published QDWI figure.
        self.assertTrue(self.disabled_worker(wages=5_405)[1].eligible)
        self.assertFalse(self.disabled_worker(wages=5_407)[1].eligible)

    def test_qdwi_resource_limit(self):
        self.assertTrue(self.disabled_worker(assets=4_000)[1].eligible)
        self.assertFalse(self.disabled_worker(assets=4_001)[1].eligible)

    def test_excluded_by_medicaid(self):
        self.assertFalse(self.disabled_worker(medicaid=True)[1].eligible)

    def test_medicare_takes_the_other_routes(self):
        calculator, e, member = self.single(age=64, disabled=True, wages=2_000, assets=1_000)
        self.assert_route(calculator, member, "qmb")


class TestValue(MspBaseTestCase):
    def test_part_b_premium_per_eligible_member(self):
        screen = self.make_screen(household_size=2)
        self.person(screen, social_security=900)
        self.person(screen, "spouse", age=62, medicare=False, wages=2_000, disabled=True)
        e = self.run_calc(screen)[1]
        self.assertEqual(e.value, PART_B)


class TestDependencies(MspBaseTestCase):
    def test_dropped_when_a_declared_field_is_missing(self):
        screen = self.make_screen()
        self.person(screen, social_security=1_000)
        for field in StandInMsp.dependencies:
            with self.subTest(field=field), self.assertRaises(DependencyError):
                self.calculate(screen, missing=(field,))

    def test_declares_the_fields_it_reads(self):
        self.assertEqual(
            set(StandInMsp.dependencies),
            {"household_assets", "relationship", "insurance", "income_type", "income_amount", "income_frequency"},
        )

"""
NJ SNAP (``NjSnap``): NJ's values, and one test per Test Scenario in the NJ spec
(``programs/cross_white_label/snap/nj/snap_nj_spec.md`` in program-ops).

The spec states monthly dollars; the API reports annual, so each test asserts the monthly figure
times 12. Every scenario sits in ZIP 07102 (Essex County) or 08901 (Middlesex County), which no
rule reads.
"""

from decimal import Decimal

from programs.framework.base import Eligibility
from programs.programs.cross_white_label.snap import nj
from programs.programs.cross_white_label.snap.nj import NjSnap
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from programs.programs.testing_fixtures.households import add_income
from screener.models import Screen


class NjSnapTestCase(CustomCalculatorTestCase):
    calculator_class = NjSnap
    white_label_code = "nj"
    state_code = "NJ"
    default_zipcode = "07102"
    default_county = "Essex County"
    needs_program_row = False
    stores_age = False

    def household(self, *people: tuple, assets: int = 0, **expenses: int) -> Screen:
        """
        A screen from (relationship, age[, member kwargs]) tuples, the head first. Expenses are
        keyword arguments of monthly dollars: ``rent=1200``, ``childSupport=800``.
        """
        screen = self.make_screen(household_size=len(people), household_assets=assets)
        for relationship, age, *rest in people:
            self.add_member(screen, relationship, age, **(rest[0] if rest else {}))

        head = screen.household_members.get(relationship="headOfHousehold")
        for expense_type, amount in expenses.items():
            self.add_expense(head, amount, expense_type)

        return screen

    def calculator(self, screen: Screen) -> NjSnap:
        return self.make_calculator(screen)

    def assert_eligible(self, eligibility: Eligibility, monthly: int) -> None:
        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, monthly * 12)

    def assert_ineligible(self, eligibility: Eligibility) -> None:
        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.value, 0)


def wages(amount: int) -> dict:
    return {"monthly_income": amount}


def social_security(amount: int) -> dict:
    return {"monthly_income": amount, "income_type": "sSRetirement"}


class TestSpecScenarios(NjSnapTestCase):
    def test_1_family_of_three_through_the_185_percent_route(self):
        # 2,500 - 500 - 217 - excess shelter capped at 769 = 1,014; 808 - ceil(304.2) = 503.
        screen = self.household(
            ("headOfHousehold", 35, wages(2_500)),
            ("child", 8),
            ("child", 5),
            rent=1_200,
            heating=100,
        )

        self.assertEqual(self.calculator(screen).net_income, 1_014)
        self.assert_eligible(self.calculate(screen), 503)

    def test_2_single_adult_just_under_185_percent_gets_the_state_minimum(self):
        # Net 2,460 - 492 - 217 - 125 = 1,626; the federal 25 minimum is lifted to 95.
        screen = self.household(("headOfHousehold", 35, wages(2_460)), rent=1_000)

        self.assertEqual(self.calculator(screen).net_income, 1_626)
        self.assertEqual(self.calculator(screen).federal_allotment(), 25)
        self.assert_eligible(self.calculate(screen), 95)

    def test_3_single_adult_at_185_percent_is_turned_away(self):
        screen = self.household(("headOfHousehold", 35, wages(2_461)))

        self.assertFalse(self.calculator(screen).under_bbce_limit())
        self.assert_ineligible(self.calculate(screen))

    def test_4_child_support_paid_is_left_out_of_income(self):
        # Countable 2,500 - 800 = 1,700; net 1,700 - 500 - 217 = 983; 306 - 295 = 11, which the
        # one-person 25 minimum raises (the spec's scenario text skips that step); then 95.
        screen = self.household(("headOfHousehold", 35, wages(2_500)), childSupport=800)

        calculator = self.calculator(screen)
        self.assertEqual(calculator.countable_income, 1_700)
        self.assertTrue(calculator.under_bbce_limit())
        self.assertEqual(calculator.net_income, 983)
        self.assertEqual(calculator.federal_allotment(), 25)
        self.assert_eligible(self.calculate(screen), 95)

    def test_5_senior_couple_above_185_percent_qualifies_on_net_income_and_resources(self):
        # 3,500 - 217 - 265 - uncapped excess shelter 2,068 = 950; 562 - 285 = 277.
        screen = self.household(
            ("headOfHousehold", 67, social_security(3_500)),
            ("spouse", 66),
            assets=4_750,
            rent=2_600,
            heating=150,
            medical=300,
        )

        self.assertEqual(self.calculator(screen).net_income, 950)
        self.assert_eligible(self.calculate(screen), 277)

    def test_6_senior_couple_one_dollar_over_the_net_income_limit(self):
        screen = self.household(
            ("headOfHousehold", 67, social_security(3_500)),
            ("spouse", 66),
            rent=1_745,
            heating=150,
            medical=300,
        )

        self.assertEqual(self.calculator(screen).net_income, 1_805)
        self.assert_ineligible(self.calculate(screen))

    def test_7_senior_couple_one_dollar_over_the_resource_limit(self):
        screen = self.household(
            ("headOfHousehold", 67, social_security(3_500)),
            ("spouse", 66),
            assets=4_751,
            rent=2_600,
            heating=150,
            medical=300,
        )

        self.assert_ineligible(self.calculate(screen))

    def test_8_parent_above_185_percent_qualifies_because_a_child_gets_ssi(self):
        # Net 4,400 - 680 - 217 = 3,503: the federal 25 minimum, lifted to 95.
        screen = self.household(
            ("headOfHousehold", 40, wages(3_400)),
            ("child", 10, {"disabled": True, "monthly_income": 1_000, "income_type": "sSI"}),
            rent=1_500,
        )

        self.assertFalse(self.calculator(screen).under_bbce_limit())
        self.assert_eligible(self.calculate(screen), 95)

    def test_9_family_of_three_under_185_percent_whose_benefit_is_zero(self):
        # Net 4,200 - 840 - 217 = 3,143; 30% rounds up to 943, over the 808 maximum.
        screen = self.household(("headOfHousehold", 35, wages(4_200)), ("child", 8), ("child", 5))

        calculator = self.calculator(screen)
        self.assertTrue(calculator.under_bbce_limit())
        self.assertEqual(calculator.allotment(), 0)
        self.assert_ineligible(self.calculate(screen))

    def test_10_family_of_three_with_a_small_federal_benefit_gets_the_state_minimum(self):
        # Net 3,500 - 700 - 217 = 2,583; federal 808 - 775 = 33, lifted to 95.
        screen = self.household(("headOfHousehold", 35, wages(3_500)), ("child", 8), ("child", 5))

        self.assertEqual(self.calculator(screen).federal_allotment(), 33)
        self.assert_eligible(self.calculate(screen), 95)

    def test_11_full_time_student_aged_49_with_no_exception_is_turned_away(self):
        screen = self.household(
            (
                "headOfHousehold",
                49,
                {
                    **wages(1_000),
                    "student": True,
                    "student_full_time": True,
                    "student_works_20_plus_hrs": False,
                    "student_has_work_study": False,
                    "student_job_training_program": False,
                },
            ),
            rent=600,
        )

        self.assert_ineligible(self.calculate(screen))

    def test_12_full_time_student_working_20_hours_qualifies(self):
        # Net 1,000 - 200 - 217 - excess shelter 308.5 rounded to 309 = 274; 306 - 83 = 223.
        screen = self.household(
            (
                "headOfHousehold",
                20,
                {**wages(1_000), "student": True, "student_full_time": True, "student_works_20_plus_hrs": True},
            ),
            rent=600,
        )

        self.assertEqual(self.calculator(screen).net_income, 274)
        self.assert_eligible(self.calculate(screen), 223)

    def test_13_household_of_nine_in_middlesex_county(self):
        # Net 3,000 - 600 - 308 = 2,092; maximum 2,066 - ceil(627.6) = 1,438.
        screen = self.household(
            ("headOfHousehold", 40, wages(3_000)),
            ("spouse", 38),
            *[("child", age) for age in (16, 14, 12, 10, 8, 5, 2)],
        )
        screen.zipcode, screen.county = "08901", "Middlesex County"
        screen.save()

        self.assertEqual(self.calculator(screen).net_income, 2_092)
        self.assert_eligible(self.calculate(screen), 1_438)

    def test_14_senior_couple_exactly_at_the_net_income_limit(self):
        # Net 3,500 - 217 - 265 - 1,214 = 1,804; federal 562 - 542 = 20, raised to 25, then to 95.
        screen = self.household(
            ("headOfHousehold", 67, social_security(3_500)),
            ("spouse", 66),
            rent=1_746,
            heating=150,
            medical=300,
        )

        self.assertEqual(self.calculator(screen).net_income, 1_804)
        self.assert_eligible(self.calculate(screen), 95)

    def test_15_single_adult_aged_60_above_185_percent_qualifies_on_net_income(self):
        # Net 2,600 - 217 - 265 - 1,718 = 400; 306 - 120 = 186.
        screen = self.household(
            ("headOfHousehold", 60, social_security(2_600)),
            rent=1_800,
            heating=100,
            medical=300,
        )

        self.assertEqual(self.calculator(screen).net_income, 400)
        self.assert_eligible(self.calculate(screen), 186)

    def test_16_single_adult_aged_59_above_185_percent_is_turned_away(self):
        screen = self.household(
            ("headOfHousehold", 59, social_security(2_600)),
            rent=1_800,
            heating=100,
            medical=300,
        )

        self.assert_ineligible(self.calculate(screen))

    def test_17_full_time_student_aged_50_qualifies_with_no_other_exception(self):
        screen = self.household(
            (
                "headOfHousehold",
                50,
                {**wages(1_000), "student": True, "student_full_time": True, "student_works_20_plus_hrs": False},
            ),
            rent=600,
        )

        self.assert_eligible(self.calculate(screen), 223)


class TestBroadBasedCategoricalEligibility(NjSnapTestCase):
    def test_limits_by_household_size(self):
        self.assertEqual(
            [nj.bbce_gross_limit(n) for n in range(1, 9)],
            [2_461, 3_337, 4_212, 5_088, 5_964, 6_839, 7_715, 8_591],
        )

    def test_limit_adds_876_per_member_above_eight(self):
        self.assertEqual(nj.bbce_gross_limit(9), 8_591 + 876)
        self.assertEqual(nj.bbce_gross_limit(10), 8_591 + 2 * 876)

    def test_one_dollar_under_the_limit_passes_and_the_limit_does_not(self):
        under = self.household(("headOfHousehold", 35, wages(2_460)))
        at = self.household(("headOfHousehold", 35, wages(2_461)))

        self.assertTrue(self.calculator(under).under_bbce_limit())
        self.assertFalse(self.calculator(at).under_bbce_limit())

    def test_no_resource_test_applies(self):
        screen = self.household(("headOfHousehold", 35, wages(1_000)), assets=250_000)

        self.assert_eligible(self.calculate(screen), 131)

    def test_the_net_income_test_is_not_applied(self):
        # Gross 2,000 is under 185%, but unearned income with no deductions leaves net over the
        # limit of 1,330 for one person: only the 185% route lets it through.
        screen = self.household(("headOfHousehold", 35, {"monthly_income": 2_000, "income_type": "unemployment"}))

        self.assertGreater(self.calculator(screen).net_income, 1_330)
        self.assert_eligible(self.calculate(screen), 95)

    def test_household_of_three_still_needs_an_allotment_above_zero(self):
        screen = self.household(("headOfHousehold", 35, wages(4_200)), ("child", 8), ("child", 5))

        self.assertTrue(self.calculator(screen).under_bbce_limit())
        self.assert_ineligible(self.calculate(screen))

    def test_household_of_two_needs_no_allotment_check(self):
        screen = self.household(("headOfHousehold", 35, wages(3_300)), ("child", 8))

        self.assert_eligible(self.calculate(screen), 95)

    def test_a_student_left_out_does_not_count_toward_size_or_income(self):
        screen = self.household(
            ("headOfHousehold", 40, wages(2_400)),
            ("sisterOrBrother", 22, {**wages(5_000), "student": True, "student_full_time": True}),
        )

        calculator = self.calculator(screen)
        self.assertEqual(calculator.household_size, 1)
        self.assertTrue(calculator.under_bbce_limit())

    def test_ssi_receipt_still_passes_from_the_federal_route(self):
        screen = self.household(("headOfHousehold", 35, {"monthly_income": 5_000, "income_type": "sSI"}))

        self.assert_eligible(self.calculate(screen), 95)


class TestUtilityAllowance(NjSnapTestCase):
    def costs(self, **expenses: int) -> Decimal:
        screen = self.household(("headOfHousehold", 35), **expenses)

        return self.calculator(screen).utility_costs()

    def test_heating_gets_the_977_allowance_whatever_the_bill(self):
        self.assertEqual(self.costs(heating=1), 977)
        self.assertEqual(self.costs(heating=500), 977)

    def test_cooling_gets_the_977_allowance(self):
        self.assertEqual(self.costs(cooling=40), 977)

    def test_heating_and_cooling_together_get_one_allowance(self):
        self.assertEqual(self.costs(heating=100, cooling=100), 977)

    def test_other_bills_are_not_added_to_the_allowance(self):
        self.assertEqual(self.costs(heating=100, telephone=50, otherUtilities=60), 977)

    def test_without_heating_or_cooling_reported_telephone_and_other_utilities_count(self):
        self.assertEqual(self.costs(telephone=50, otherUtilities=60), 110)

    def test_internet_is_not_a_utility(self):
        self.assertEqual(self.costs(internet=100), 0)

    def test_no_utility_expenses_count_for_nothing(self):
        self.assertEqual(self.costs(), 0)


class TestRounding(NjSnapTestCase):
    def test_amounts_round_half_up_to_the_dollar(self):
        calculator = self.calculator(self.household(("headOfHousehold", 35)))

        self.assertEqual(
            [calculator.round_amount(Decimal(a)) for a in ("308.49", "308.50", "308.51", "0.49", "0.5")],
            [308, 309, 309, 0, 1],
        )

    def test_each_income_stream_is_rounded_before_it_is_summed(self):
        # 12,006 a year is 1,000.50 a month, rounded to 1,001; 12,005 is 1,000.42, rounded to 1,000.
        screen = self.household(("headOfHousehold", 35))
        head = screen.household_members.get(relationship="headOfHousehold")
        self.add_income(head, 12_006, frequency="yearly")
        self.add_income(head, 12_005, frequency="yearly")

        self.assertEqual(self.calculator(screen).rounded_income(["all"]), 2_001)

    def test_the_excess_shelter_deduction_is_rounded(self):
        # Scenario 12's household: the 308.5 excess rounds up to 309, so net is 274, not 274.5.
        screen = self.household(("headOfHousehold", 35, wages(1_000)), rent=600)

        self.assertEqual(self.calculator(screen).net_income, 274)

    def test_the_gross_income_tests_use_the_amounts_as_entered(self):
        screen = self.household(("headOfHousehold", 35))
        self.add_income(screen.household_members.get(relationship="headOfHousehold"), 29_532, frequency="yearly")

        # 2,461 a month exactly: 29,532 / 12.
        self.assertEqual(self.calculator(screen).countable_income, Decimal("2461"))


class TestStateMinimum(NjSnapTestCase):
    def test_a_federal_allotment_from_1_to_94_is_raised_to_95(self):
        calculator = self.calculator(self.household(("headOfHousehold", 35)))

        self.assertEqual([calculator.state_allotment(a) for a in (1, 33, 94)], [95, 95, 95])

    def test_95_and_above_is_unchanged(self):
        calculator = self.calculator(self.household(("headOfHousehold", 35)))

        self.assertEqual([calculator.state_allotment(a) for a in (95, 96, 306)], [95, 96, 306])

    def test_no_federal_benefit_gets_no_supplement(self):
        calculator = self.calculator(self.household(("headOfHousehold", 35)))

        self.assertEqual(calculator.state_allotment(0), 0)

    def test_the_supplement_is_part_of_the_value(self):
        screen = self.household(("headOfHousehold", 35, wages(2_460)), rent=1_000)

        self.assertEqual(self.calculate(screen).value, 95 * 12)


class TestRegistration(NjSnapTestCase):
    def test_program_code_matches_the_record(self):
        self.assertEqual(NjSnap.program_code, "nj_snap")

    def test_inherits_the_federal_dependencies(self):
        self.assertIn("household_assets", NjSnap.dependencies)
        self.assertIn("expense_type", NjSnap.dependencies)


class TestRegressions(NjSnapTestCase):
    def test_a_weekly_amount_on_a_half_dollar_rounds_up(self):
        # 250 a week is exactly 1,087.50 a month; NJ rounds half up to 1,088.
        screen = self.household(("headOfHousehold", 40))
        add_income(screen.household_members.get(), 250, "wages", "weekly")

        self.assertEqual(self.calculator(screen).rounded_income(["all"]), Decimal("1088"))

    def test_biweekly_and_hourly_amounts_on_a_half_dollar_round_up(self):
        # 500 biweekly is 1,087.50 a month; 5 an hour for 50 hours is 250 a week, also 1,087.50.
        screen = self.household(("headOfHousehold", 40))
        member = screen.household_members.get()
        add_income(member, 500, "wages", "biweekly")
        self.assertEqual(self.calculator(screen).rounded_income(["all"]), Decimal("1088"))

        screen = self.household(("headOfHousehold", 40))
        stream = add_income(screen.household_members.get(), 5, "wages", "hourly")
        stream.hours_worked = 50
        stream.save()
        self.assertEqual(self.calculator(screen).rounded_income(["all"]), Decimal("1088"))

    def test_a_student_reporting_ssi_or_ssdi_is_treated_as_disabled_and_not_left_out(self):
        for income_type in ("sSI", "sSDisability"):
            with self.subTest(income_type=income_type):
                screen = self.household(
                    ("headOfHousehold", 40, wages(5_000)),
                    ("sisterOrBrother", 22, {"student": True, "student_full_time": True}),
                )
                add_income(screen.household_members.get(relationship="sisterOrBrother"), 900, income_type, "monthly")

                calculator = self.calculator(screen)
                self.assertEqual(calculator.ineligible_students, [])
                self.assertEqual(calculator.household_size, 2)
                self.assertTrue(calculator.has_elderly_or_disabled_member)

    def test_a_lone_student_reporting_ssi_is_not_rejected_as_an_empty_household(self):
        screen = self.household(("headOfHousehold", 22, {"student": True, "student_full_time": True}))
        add_income(screen.household_members.get(), 900, "sSI", "monthly")

        self.assertEqual(self.calculator(screen).household_size, 1)
        self.assertTrue(self.calculate(screen).eligible)

    def test_a_student_with_no_disability_flag_or_disability_income_is_still_left_out(self):
        screen = self.household(
            ("headOfHousehold", 40, wages(2_400)),
            ("sisterOrBrother", 22, {**wages(900), "student": True, "student_full_time": True}),
        )

        self.assertEqual(self.calculator(screen).household_size, 1)

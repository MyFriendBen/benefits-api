"""Federal SSI scenarios, one per spec section 8, plus the structural checks.

Every dollar figure is the 2026 federal benefit rate and exclusions, keyed by the program's
year. The spec states each payment per month; the calculator carries the annual figure every
program value does, so each assertion is the spec's monthly payment times twelve.

Section 4's `citizenship_or_qualified_alien` has no scenario: it is `Enforced by: program-record`
(`legal_status_required`), which the calculator never reads. `residence_us` is enforced by
the white label.
"""

from typing import Optional
from unittest.mock import patch

from programs.framework.base import Eligibility
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from programs.programs.white_labels.federal.ssi.calculator import SSI_YEARS, FederalSsi
from screener.models import HouseholdMember, Screen

BENEFIT_YEAR = 2026
INDIVIDUAL_FBR = 994
COUPLE_FBR = 1_491


def annual(monthly: float) -> int:
    return round(monthly * 12)


class FederalSsiTestCase(CustomCalculatorTestCase):
    calculator_class = FederalSsi
    white_label_code = "federal"
    state_code = ""
    fpl_year = str(BENEFIT_YEAR)
    # The calculator reads age only through `calc_age()`.
    stores_age = False

    def member(
        self,
        screen: Screen,
        relationship: str,
        age: int,
        income: Optional[dict[str, int]] = None,
        **kwargs,
    ) -> HouseholdMember:
        """A member of `age` today, with monthly income by type. Condition flags default to
        False, as the screener sends them; pass `disabled=True` and so on to set one."""
        member = self.add_member(screen, relationship, age=age, **kwargs)
        for income_type, amount in (income or {}).items():
            self.add_income(member, amount, income_type, "monthly")

        return member

    def assert_eligible(self, e: Eligibility, monthly: float) -> None:
        """The household qualifies and its value is `monthly` for the year."""
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, annual(monthly))

    def assert_ineligible(self, e: Eligibility) -> None:
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)

    def assert_member(self, e: Eligibility, member: HouseholdMember, monthly: Optional[float]) -> None:
        """`member` is paid `monthly` a month, or is not eligible when `monthly` is None."""
        verdict = next(m for m in e.eligible_members if m.member.id == member.id)
        if monthly is None:
            self.assertFalse(verdict.eligible)
            self.assertEqual(verdict.value, 0)
        else:
            self.assertTrue(verdict.eligible)
            self.assertEqual(verdict.value, annual(monthly))


class TestRegistration(FederalSsiTestCase):
    def test_program_code_is_the_prefixed_federal_name(self):
        """The registry resolves a calculator by matching `program_code` to
        `Program.name_abbreviated`, so the federal row's prefixed name has to be here."""
        self.assertEqual(FederalSsi.program_code, "federal_ssi")

    def test_a_year_with_no_parameters_uses_the_latest_and_reports_it(self):
        """A January rollover the table wasn't updated for must not raise: an exception
        from a displayed program fails the whole results page, in every white label."""
        screen = self.make_screen(household_size=1)
        self.member(screen, "headOfHousehold", 70, income={"sSRetirement": 500})
        calculator = self.make_calculator(screen)

        self.program.year.period = str(max(SSI_YEARS) + 1)
        try:
            with patch("programs.programs.white_labels.federal.ssi.calculator.capture_message") as report:
                e = calculator.calc()
        finally:
            self.program.year.period = self.fpl_year

        self.assert_eligible(e, 514)
        report.assert_called_once()
        self.assertIn(str(max(SSI_YEARS) + 1), report.call_args.args[0])

    def test_the_screening_year_is_used_when_the_program_has_no_year(self):
        screen = self.make_screen(household_size=1)
        self.member(screen, "headOfHousehold", 70)
        calculator = self.make_calculator(screen)

        with patch.object(type(self.program), "year", None):
            self.assertEqual(calculator.benefit_year, screen.get_reference_date().year)

    def test_an_age_only_household_reads_missing_answers_as_no(self):
        """Screens that collect no condition answers (`None` flags) still get the aged
        route; a `None` disability is not a disability."""
        screen = self.make_screen(household_size=2, household_assets=0)
        aged = self.member(
            screen,
            "headOfHousehold",
            70,
            disabled=None,
            visually_impaired=None,
            long_term_disability=None,
            student=None,
        )
        younger = self.member(
            screen, "child", 40, disabled=None, visually_impaired=None, long_term_disability=None, student=None
        )

        e = self.calculate(screen)

        self.assert_member(e, aged, INDIVIDUAL_FBR)
        self.assert_member(e, younger, None)

    def test_the_resource_test_needs_household_assets(self):
        """Assets are the only resource input, so a screen without them cannot be answered."""
        self.assertIn("household_assets", FederalSsi.dependencies)
        screen = self.make_screen(household_size=1)
        self.member(screen, "headOfHousehold", 70)

        self.assertFalse(self.make_calculator(screen, missing=("household_assets",)).can_calc())


class TestScenarios(FederalSsiTestCase):
    def test_scenario_01_older_adult_living_alone_on_social_security(self):
        screen = self.make_screen(household_size=1, household_assets=1_000)
        self.member(screen, "headOfHousehold", 70, income={"sSRetirement": 500})

        self.assert_eligible(self.calculate(screen), 514)

    def test_scenario_02_person_who_has_just_turned_65(self):
        screen = self.make_screen(household_size=1, household_assets=0)
        self.member(screen, "headOfHousehold", 65)

        self.assert_eligible(self.calculate(screen), INDIVIDUAL_FBR)

    def test_scenario_03_64_year_old_with_no_disability_or_vision_impairment(self):
        screen = self.make_screen(household_size=1, household_assets=0)
        self.member(screen, "headOfHousehold", 64, disabled=False, visually_impaired=False, long_term_disability=False)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_04_blind_adult_under_65(self):
        screen = self.make_screen(household_size=1, household_assets=0)
        self.member(screen, "headOfHousehold", 40, visually_impaired=True, disabled=False)

        self.assert_eligible(self.calculate(screen), INDIVIDUAL_FBR)

    def test_scenario_05_disabled_adult_who_has_just_turned_18(self):
        screen = self.make_screen(household_size=1, household_assets=0)
        self.member(screen, "headOfHousehold", 18, disabled=True)

        self.assert_eligible(self.calculate(screen), INDIVIDUAL_FBR)

    def test_scenario_06_adult_reporting_only_a_long_term_disability(self):
        screen = self.make_screen(household_size=1, household_assets=0)
        self.member(screen, "headOfHousehold", 45, long_term_disability=True, disabled=False)

        self.assert_eligible(self.calculate(screen), INDIVIDUAL_FBR)

    def test_scenario_07_disabled_child_with_one_working_parent_savings_at_the_limit(self):
        screen = self.make_screen(household_size=2, household_assets=4_000)
        parent = self.member(screen, "headOfHousehold", 40, income={"wages": 3_000})
        child = self.member(screen, "child", 17, disabled=True)

        e = self.calculate(screen)

        self.assert_eligible(e, 550.50)
        self.assert_member(e, child, 550.50)
        self.assert_member(e, parent, None)

    def test_scenario_08_disabled_child_with_savings_one_dollar_over_the_limit(self):
        screen = self.make_screen(household_size=2, household_assets=4_001)
        self.member(screen, "headOfHousehold", 40, income={"wages": 3_000})
        self.member(screen, "child", 17, disabled=True)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_09_disabled_worker_earning_just_over_1690(self):
        screen = self.make_screen(household_size=1, household_assets=0)
        self.member(screen, "headOfHousehold", 35, disabled=True, income={"wages": 1_691})

        self.assert_eligible(self.calculate(screen), 191)

    def test_scenario_10_disabled_worker_over_the_income_limit_on_earnings_alone(self):
        screen = self.make_screen(household_size=1, household_assets=0)
        self.member(screen, "headOfHousehold", 35, disabled=True, income={"wages": 2_500})

        self.assert_eligible(self.calculate(screen), INDIVIDUAL_FBR)

    def test_scenario_11_blind_worker_over_the_income_limit_on_earnings_alone(self):
        screen = self.make_screen(household_size=1, household_assets=0)
        self.member(screen, "headOfHousehold", 35, visually_impaired=True, disabled=False, income={"wages": 2_500})

        self.assert_eligible(self.calculate(screen), INDIVIDUAL_FBR)

    def test_scenario_12_older_adult_whose_social_security_sits_just_under_the_limit(self):
        screen = self.make_screen(household_size=1, household_assets=0)
        self.member(screen, "headOfHousehold", 70, income={"sSRetirement": 1_073})

        self.assert_eligible(self.calculate(screen), 1)

    def test_scenario_13_older_adult_one_dollar_over_the_limit(self):
        screen = self.make_screen(household_size=1, household_assets=0)
        self.member(screen, "headOfHousehold", 70, income={"sSRetirement": 1_074})

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_14_older_adult_whose_wages_sit_just_under_the_limit(self):
        screen = self.make_screen(household_size=1, household_assets=0)
        self.member(screen, "headOfHousehold", 70, income={"wages": 2_102})

        self.assert_eligible(self.calculate(screen), 0.50)

    def test_scenario_15_older_adult_whose_wages_are_one_dollar_over(self):
        screen = self.make_screen(household_size=1, household_assets=0)
        self.member(screen, "headOfHousehold", 70, income={"wages": 2_103})

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_16_older_adult_on_tanf(self):
        screen = self.make_screen(household_size=1, household_assets=0)
        self.member(screen, "headOfHousehold", 70, income={"cashAssistance": 1_060})

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_17_older_adult_on_other_cash_assistance(self):
        screen = self.make_screen(household_size=1, household_assets=0)
        self.member(screen, "headOfHousehold", 70, income={"cashAssistanceOther": 1_200})

        self.assert_eligible(self.calculate(screen), INDIVIDUAL_FBR)

    def test_scenario_18_disabled_student_with_part_time_wages(self):
        screen = self.make_screen(household_size=1, household_assets=0)
        self.member(screen, "headOfHousehold", 20, disabled=True, student=True, income={"wages": 2_000})

        self.assert_eligible(self.calculate(screen), INDIVIDUAL_FBR)

    def test_scenario_19_older_couple_just_under_the_couple_limit(self):
        screen = self.make_screen(household_size=2, household_assets=0)
        head = self.member(screen, "headOfHousehold", 70, income={"sSRetirement": 785})
        spouse = self.member(screen, "spouse", 68, income={"sSRetirement": 785})

        e = self.calculate(screen)

        self.assert_eligible(e, 1)
        self.assert_member(e, head, 0.50)
        self.assert_member(e, spouse, 0.50)

    def test_scenario_20_older_couple_one_dollar_over(self):
        screen = self.make_screen(household_size=2, household_assets=0)
        self.member(screen, "headOfHousehold", 70, income={"sSRetirement": 786})
        self.member(screen, "spouse", 68, income={"sSRetirement": 785})

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_21_older_couple_with_savings_at_the_couple_limit(self):
        screen = self.make_screen(household_size=2, household_assets=3_000)
        head = self.member(screen, "headOfHousehold", 70)
        spouse = self.member(screen, "spouse", 68)

        e = self.calculate(screen)

        self.assert_eligible(e, COUPLE_FBR)
        self.assert_member(e, head, 745.50)
        self.assert_member(e, spouse, 745.50)

    def test_scenario_22_older_adult_with_savings_at_the_limit(self):
        screen = self.make_screen(household_size=1, household_assets=2_000)
        self.member(screen, "headOfHousehold", 70)

        self.assert_eligible(self.calculate(screen), INDIVIDUAL_FBR)

    def test_scenario_23_older_adult_with_savings_one_dollar_over(self):
        screen = self.make_screen(household_size=1, household_assets=2_001)
        self.member(screen, "headOfHousehold", 70)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_24_older_adult_with_a_spouse_who_doesnt_qualify_and_earns_a_little(self):
        screen = self.make_screen(household_size=2, household_assets=0)
        head = self.member(screen, "headOfHousehold", 70, income={"sSRetirement": 500})
        spouse = self.member(screen, "spouse", 50, disabled=False, income={"wages": 400})

        e = self.calculate(screen)

        self.assert_eligible(e, 514)
        self.assert_member(e, head, 514)
        self.assert_member(e, spouse, None)

    def test_scenario_25_older_adult_with_a_spouse_who_doesnt_qualify_and_earns_more(self):
        screen = self.make_screen(household_size=2, household_assets=0)
        head = self.member(screen, "headOfHousehold", 70, income={"sSRetirement": 500})
        self.member(screen, "spouse", 50, disabled=False, income={"wages": 1_600})

        e = self.calculate(screen)

        self.assert_eligible(e, 243.50)
        self.assert_member(e, head, 243.50)

    def test_scenario_26_older_adult_living_with_a_grown_childs_household(self):
        screen = self.make_screen(household_size=2, household_assets=50_000)
        head = self.member(screen, "headOfHousehold", 70, income={"sSRetirement": 500})
        grown_child = self.member(screen, "child", 40, income={"wages": 4_000})

        e = self.calculate(screen)

        self.assert_eligible(e, 514)
        self.assert_member(e, head, 514)
        self.assert_member(e, grown_child, None)

    def test_scenario_27_child_without_a_disability(self):
        screen = self.make_screen(household_size=2, household_assets=0)
        self.member(screen, "headOfHousehold", 40)
        self.member(screen, "child", 10, disabled=False, visually_impaired=False, long_term_disability=False)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_28_disabled_16_year_old_with_a_part_time_job_not_marked_as_a_student(self):
        screen = self.make_screen(household_size=2, household_assets=0)
        self.member(screen, "headOfHousehold", 40)
        self.member(screen, "child", 16, disabled=True, student=False, income={"wages": 600})

        self.assert_eligible(self.calculate(screen), INDIVIDUAL_FBR)

    def test_scenario_29_disabled_18_year_old_with_a_part_time_job_not_marked_as_a_student(self):
        screen = self.make_screen(household_size=2, household_assets=0)
        self.member(screen, "headOfHousehold", 45)
        self.member(screen, "child", 18, disabled=True, student=False, income={"wages": 600})

        self.assert_eligible(self.calculate(screen), 736.50)

    def test_scenario_30_disabled_stepchild_with_a_parent_and_stepparent_savings_at_the_limit(self):
        screen = self.make_screen(household_size=3, household_assets=5_000)
        self.member(screen, "headOfHousehold", 40)
        self.member(screen, "spouse", 38)
        self.member(screen, "stepChild", 12, disabled=True)

        self.assert_eligible(self.calculate(screen), INDIVIDUAL_FBR)

    def test_scenario_31_disabled_stepchild_with_savings_one_dollar_over_the_two_parent_limit(self):
        screen = self.make_screen(household_size=3, household_assets=5_001)
        self.member(screen, "headOfHousehold", 40)
        self.member(screen, "spouse", 38)
        self.member(screen, "stepChild", 12, disabled=True)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_32_disabled_stepchild_living_with_a_stepparent_alone(self):
        screen = self.make_screen(household_size=2, household_assets=10_000)
        self.member(screen, "headOfHousehold", 40, income={"wages": 5_000})
        self.member(screen, "stepChild", 12, disabled=True)

        self.assert_eligible(self.calculate(screen), INDIVIDUAL_FBR)

    def test_scenario_33_disabled_foster_child(self):
        screen = self.make_screen(household_size=2, household_assets=0)
        self.member(screen, "headOfHousehold", 40, income={"wages": 5_000})
        self.member(screen, "fosterChild", 10, disabled=True)

        self.assert_eligible(self.calculate(screen), INDIVIDUAL_FBR)

    def test_scenario_34_older_adult_with_a_domestic_partner_who_earns_more(self):
        screen = self.make_screen(household_size=2, household_assets=0)
        self.member(screen, "headOfHousehold", 70, income={"sSRetirement": 500})
        self.member(screen, "domesticPartner", 50, disabled=False, income={"wages": 1_600})

        self.assert_eligible(self.calculate(screen), 514)

    def test_scenario_35_disabled_child_whose_parent_reports_ssi_and_stays_eligible_with_a_working_spouse(self):
        screen = self.make_screen(household_size=3, household_assets=0)
        head = self.member(screen, "headOfHousehold", 40, disabled=True, income={"sSI": 400})
        spouse = self.member(screen, "spouse", 40, disabled=False, income={"wages": 2_700})
        child = self.member(screen, "child", 10, disabled=True)

        e = self.calculate(screen)

        self.assert_member(e, child, INDIVIDUAL_FBR)
        self.assert_member(e, head, 183.50)
        self.assert_member(e, spouse, None)
        self.assert_eligible(e, INDIVIDUAL_FBR + 183.50)

    def test_scenario_36_disabled_child_whose_only_parent_reports_ssi_savings_over_the_one_parent_limit(self):
        screen = self.make_screen(household_size=2, household_assets=4_500)
        head = self.member(screen, "headOfHousehold", 40, disabled=True, income={"sSI": 994})
        child = self.member(screen, "child", 12, disabled=True)

        e = self.calculate(screen)

        self.assert_member(e, child, INDIVIDUAL_FBR)
        self.assert_member(e, head, INDIVIDUAL_FBR)
        self.assert_eligible(e, 2 * INDIVIDUAL_FBR)

    def test_scenario_37_disabled_child_with_two_parents_neither_on_ssi_one_working(self):
        screen = self.make_screen(household_size=3, household_assets=0)
        self.member(screen, "headOfHousehold", 40, income={"wages": 4_000})
        self.member(screen, "spouse", 40)
        child = self.member(screen, "child", 10, disabled=True)

        e = self.calculate(screen)

        self.assert_eligible(e, 547.50)
        self.assert_member(e, child, 547.50)

    def test_scenario_38_disabled_child_whose_parent_reports_ssi_other_parents_savings_over_the_limit(self):
        screen = self.make_screen(household_size=3, household_assets=6_000)
        head = self.member(screen, "headOfHousehold", 40, disabled=True, income={"sSI": 400})
        self.member(screen, "spouse", 40, disabled=False, income={"wages": 1_000})
        child = self.member(screen, "child", 10, disabled=True)

        e = self.calculate(screen)

        self.assert_member(e, child, INDIVIDUAL_FBR)
        self.assert_member(e, head, INDIVIDUAL_FBR)
        self.assert_eligible(e, 2 * INDIVIDUAL_FBR)

    def test_scenario_39_disabled_child_whose_parent_reports_ssi_but_would_not_stay_eligible(self):
        screen = self.make_screen(household_size=3, household_assets=0)
        head = self.member(screen, "headOfHousehold", 40, disabled=True, income={"sSI": 400})
        self.member(screen, "spouse", 40, disabled=False, income={"wages": 4_000})
        child = self.member(screen, "child", 10, disabled=True)

        e = self.calculate(screen)

        self.assert_member(e, child, 547.50)
        self.assert_member(e, head, None)
        self.assert_eligible(e, 547.50)

    def test_scenario_40_disabled_worker_who_has_just_turned_65_over_the_limit_on_earnings_not_on_ssi(self):
        screen = self.make_screen(household_size=1, household_assets=0)
        self.member(screen, "headOfHousehold", 65, disabled=True, income={"wages": 2_500})

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_41_disabled_66_year_old_already_on_ssi_over_the_limit_on_earnings(self):
        screen = self.make_screen(household_size=1, household_assets=0)
        self.member(screen, "headOfHousehold", 66, disabled=True, income={"sSI": 200, "wages": 2_500})

        self.assert_eligible(self.calculate(screen), INDIVIDUAL_FBR)

    def test_scenario_42_disabled_child_whose_parents_only_income_is_other_cash_assistance(self):
        screen = self.make_screen(household_size=2, household_assets=0)
        parent = self.member(screen, "headOfHousehold", 40, income={"cashAssistanceOther": 3_500})
        child = self.member(screen, "child", 10, disabled=True)

        e = self.calculate(screen)

        self.assert_eligible(e, INDIVIDUAL_FBR)
        self.assert_member(e, child, INDIVIDUAL_FBR)
        self.assert_member(e, parent, None)

    def test_scenario_43_older_adult_whose_ineligible_spouses_only_income_is_other_cash_assistance(self):
        screen = self.make_screen(household_size=2, household_assets=0)
        head = self.member(screen, "headOfHousehold", 70, income={"sSRetirement": 500})
        spouse = self.member(screen, "spouse", 50, disabled=False, income={"cashAssistanceOther": 3_500})

        e = self.calculate(screen)

        self.assert_eligible(e, 514)
        self.assert_member(e, head, 514)
        self.assert_member(e, spouse, None)

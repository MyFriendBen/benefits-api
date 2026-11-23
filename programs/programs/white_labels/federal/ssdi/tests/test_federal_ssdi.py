"""Federal SSDI scenarios, one per spec §8, plus the checks the scenarios can't express.

The clock is pinned so the full retirement age scenarios land on the birth months the spec
names: at October 2026, age 66 years 6 months is a 1960 birth and 66 years 11 months is
November 1959.

§4's `legal_status` has no scenario here: it is `Enforced by: program-record`
(`legal_status_required`), which the calculator never reads. `survivor_age_50_to_60` has none
either: every household that passes the surviving spouse route also passes the worker route at
the same amount, so no household can tell the two apart.
"""

from datetime import date

from programs.framework.base import Eligibility, ProgramCalculator
from programs.models import Program
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from programs.programs.white_labels.federal.ssdi.calculator import FederalSsdi
from screener.models import CurrentBenefit, HouseholdMember, Screen

WORKER = 1_497 * 12
CHILD = 748 * 12

# The two checkboxes that together meet the disability test.
DISABLED = {"disabled": True, "long_term_disability": True}


class FederalSsdiTestCase(CustomCalculatorTestCase):
    calculator_class = FederalSsdi
    white_label_code = "federal"
    state_code = ""
    reference_date = date(2026, 10, 15)
    # The calculator reads age only through `calc_age()` and `birth_year_month`.
    stores_age = False

    def member_value(self, e: Eligibility, member: HouseholdMember) -> int:
        for member_eligibility in e.eligible_members:
            if member_eligibility.member.id == member.id:
                return member_eligibility.value if member_eligibility.eligible else 0
        raise AssertionError(f"member {member.id} was not evaluated")

    def hold_current_benefit(self, screen: Screen, program: Program) -> None:
        CurrentBenefit.objects.create(screen=screen, program=program)
        screen.invalidate_current_benefits_cache()


class TestFederalSsdiRegistration(FederalSsdiTestCase):
    def test_is_subclass_of_program_calculator(self) -> None:
        self.assertTrue(issubclass(FederalSsdi, ProgramCalculator))

    def test_program_code_is_the_prefixed_federal_name(self) -> None:
        """The registry resolves a calculator by matching `program_code` to
        `Program.name_abbreviated`, so the federal row's prefixed name has to be here."""
        self.assertEqual(FederalSsdi.program_code, "federal_ssdi")


class TestScenario01DisabledWorkerUnderTheLimit(FederalSsdiTestCase):
    """Scenario 1: `disabling_condition`, `earnings_below_sga`, `below_full_retirement_age`,
    `member_role` — the golden path for the worker route."""

    def test_eligible_for_the_worker_amount(self) -> None:
        screen = self.make_screen()
        head = self.add_member(screen, age=45, monthly_income=1_000, **DISABLED)

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(self.member_value(e, head), WORKER)
        self.assertEqual(e.value, WORKER)


class TestScenario02NoDisabilityAndNoVisionImpairment(FederalSsdiTestCase):
    """Scenario 2: `disabling_condition`, `statutory_blindness` — fails both ways in."""

    def test_ineligible(self) -> None:
        screen = self.make_screen()
        self.add_member(screen, age=45)

        e = self.calculate(screen)

        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)


class TestScenario03BlindnessWithoutADisability(FederalSsdiTestCase):
    """Scenario 3: `statutory_blindness` — qualifies on its own."""

    def test_eligible_for_the_worker_amount(self) -> None:
        screen = self.make_screen()
        self.add_member(screen, age=45, monthly_income=1_000, visually_impaired=True)

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, WORKER)


class TestScenario04EarningsAtTheLimit(FederalSsdiTestCase):
    """Scenario 4: `earnings_below_sga` — at the $1,690 limit."""

    def test_eligible(self) -> None:
        screen = self.make_screen()
        self.add_member(screen, age=45, monthly_income=1_690, **DISABLED)

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, WORKER)


class TestScenario05EarningsOneDollarOverTheLimit(FederalSsdiTestCase):
    """Scenario 5: `earnings_below_sga` — one step past the $1,690 limit."""

    def test_ineligible(self) -> None:
        screen = self.make_screen()
        self.add_member(screen, age=45, monthly_income=1_691, **DISABLED)

        self.assertFalse(self.calculate(screen).eligible)


class TestScenario06BlindPersonAtTheHigherLimit(FederalSsdiTestCase):
    """Scenario 6: `earnings_below_sga` — at the $2,830 limit for a reported visual impairment."""

    def test_eligible(self) -> None:
        screen = self.make_screen()
        self.add_member(screen, age=45, monthly_income=2_830, visually_impaired=True)

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, WORKER)


class TestScenario07BlindPersonOneDollarOverTheHigherLimit(FederalSsdiTestCase):
    """Scenario 7: `earnings_below_sga` — one step past the $2,830 limit."""

    def test_ineligible(self) -> None:
        screen = self.make_screen()
        self.add_member(screen, age=45, monthly_income=2_831, visually_impaired=True)

        self.assertFalse(self.calculate(screen).eligible)


class TestScenario08NotBlindEarningTheHigherLimit(FederalSsdiTestCase):
    """Scenario 8: `earnings_below_sga` — the higher limit does not reach a person who is not blind."""

    def test_ineligible(self) -> None:
        screen = self.make_screen()
        self.add_member(screen, age=45, monthly_income=2_830, **DISABLED)

        self.assertFalse(self.calculate(screen).eligible)


class TestScenario09BelowAFullRetirementAgeOf67(FederalSsdiTestCase):
    """Scenario 9: `below_full_retirement_age` — 66 years 6 months, born in 1960."""

    def test_eligible(self) -> None:
        screen = self.make_screen()
        head = self.add_member(screen, age=66.5, monthly_income=1_000, **DISABLED)
        self.assertEqual(head.birth_year_month, date(1960, 4, 1))

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, WORKER)


class TestScenario10PastAFullRetirementAgeOf66And10Months(FederalSsdiTestCase):
    """Scenario 10: `below_full_retirement_age` — 66 years 11 months, born November 1959."""

    def test_ineligible(self) -> None:
        screen = self.make_screen()
        head = self.add_member(screen, age=66 + 11 / 12, monthly_income=1_000, **DISABLED)
        self.assertEqual(head.birth_year_month, date(1959, 11, 1))

        self.assertFalse(self.calculate(screen).eligible)


class TestScenario11ChildOfAParentReceivingSsdi(FederalSsdiTestCase):
    """Scenario 11: `insured_parent_entitled`, `child_relationship`, `child_dependency`,
    `child_unmarried`, `child_under_18`, `member_role` — the golden path for the child route."""

    def test_child_gets_half_the_worker_amount_and_the_parent_nothing(self) -> None:
        screen = self.make_screen(household_size=2)
        parent = self.add_member(screen, age=40, monthly_income=1_497, income_type="sSDisability")
        child = self.add_member(screen, "child", age=10)

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(self.member_value(e, child), CHILD)
        self.assertEqual(self.member_value(e, parent), 0)
        self.assertEqual(e.value, CHILD)


class TestScenario12ChildOfAParentReceivingRetirement(FederalSsdiTestCase):
    """Scenario 12: `insured_parent_entitled` — the parent receives retirement benefits."""

    def test_child_gets_half_the_worker_amount(self) -> None:
        screen = self.make_screen(household_size=2)
        parent = self.add_member(screen, age=70, monthly_income=1_000, income_type="sSRetirement")
        child = self.add_member(screen, "child", age=10)

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(self.member_value(e, child), CHILD)
        self.assertEqual(self.member_value(e, parent), 0)


class TestScenario13ChildOfAParentWithNoSocialSecurityIncome(FederalSsdiTestCase):
    """Scenario 13: `insured_parent_entitled` — no parent receives a benefit."""

    def test_ineligible(self) -> None:
        screen = self.make_screen(household_size=2)
        self.add_member(screen, age=40)
        self.add_member(screen, "child", age=10)

        self.assertFalse(self.calculate(screen).eligible)


class TestScenario14MemberWhoIsNotTheParentsChild(FederalSsdiTestCase):
    """Scenario 14: `child_relationship`, `child_dependency` — a relationship other than child,
    stepchild or grandchild."""

    def test_ineligible(self) -> None:
        screen = self.make_screen(household_size=2)
        self.add_member(screen, age=40, monthly_income=1_497, income_type="sSDisability")
        self.add_member(screen, "relatedOther", age=10)

        self.assertFalse(self.calculate(screen).eligible)


class TestScenario15ChildAged17(FederalSsdiTestCase):
    """Scenario 15: `child_under_18` — the last age that qualifies."""

    def test_eligible(self) -> None:
        screen = self.make_screen(household_size=2)
        self.add_member(screen, age=40, monthly_income=1_497, income_type="sSDisability")
        child = self.add_member(screen, "child", age=17)

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(self.member_value(e, child), CHILD)


class TestScenario16ChildAged18NotAStudent(FederalSsdiTestCase):
    """Scenario 16: `child_under_18`, `child_student_under_19`, `adult_child_disabled_before_22`
    — one step past the age limit with neither other way in."""

    def test_ineligible(self) -> None:
        screen = self.make_screen(household_size=2)
        self.add_member(screen, age=40, monthly_income=1_497, income_type="sSDisability")
        self.add_member(screen, "child", age=18)

        self.assertFalse(self.calculate(screen).eligible)


class TestScenario17ChildAged18FullTimeStudent(FederalSsdiTestCase):
    """Scenario 17: `child_student_under_19` — a full-time student who is 18."""

    def test_eligible(self) -> None:
        screen = self.make_screen(household_size=2)
        self.add_member(screen, age=40, monthly_income=1_497, income_type="sSDisability")
        child = self.add_member(screen, "child", age=18, student=True, student_full_time=True)

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(self.member_value(e, child), CHILD)


class TestScenario18ChildAged19FullTimeStudent(FederalSsdiTestCase):
    """Scenario 18: `child_student_under_19` — one step past the student age limit."""

    def test_ineligible(self) -> None:
        screen = self.make_screen(household_size=2)
        self.add_member(screen, age=40, monthly_income=1_497, income_type="sSDisability")
        self.add_member(screen, "child", age=19, student=True, student_full_time=True)

        self.assertFalse(self.calculate(screen).eligible)


class TestScenario19AdultChildWithNoDisability(FederalSsdiTestCase):
    """Scenario 19: `adult_child_disabled_before_22` — an adult who is not a student and reports
    no disability."""

    def test_ineligible(self) -> None:
        screen = self.make_screen(household_size=2)
        self.add_member(screen, age=55, monthly_income=1_497, income_type="sSDisability")
        self.add_member(screen, "child", age=25)

        self.assertFalse(self.calculate(screen).eligible)


class TestScenario20AdultChildWithADisabilityOverTheLimit(FederalSsdiTestCase):
    """Scenario 20: `adult_child_disabled_before_22`, `earnings_below_sga` — the adult child
    path carries its own earnings test."""

    def test_ineligible(self) -> None:
        screen = self.make_screen(household_size=2)
        self.add_member(screen, age=55, monthly_income=1_497, income_type="sSDisability")
        self.add_member(screen, "child", age=25, monthly_income=1_691, **DISABLED)

        self.assertFalse(self.calculate(screen).eligible)


class TestScenario21DisabledWorkerAlreadyReceivingSsdi(FederalSsdiTestCase):
    """Scenario 21: `not_receiving_ssdi` — SSDI income means the person already receives it."""

    def test_ineligible(self) -> None:
        screen = self.make_screen()
        self.add_member(screen, age=45, monthly_income=1_497, income_type="sSDisability", **DISABLED)

        self.assertFalse(self.calculate(screen).eligible)


class TestScenario22SpouseAlreadyReceivingSsdi(FederalSsdiTestCase):
    """Scenario 22: `not_receiving_ssdi` — only the person receiving SSDI is excluded."""

    def test_head_is_eligible_and_the_spouse_is_not(self) -> None:
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, age=45, monthly_income=1_000, **DISABLED)
        spouse = self.add_member(screen, "spouse", age=47, monthly_income=1_497, income_type="sSDisability", **DISABLED)

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(self.member_value(e, head), WORKER)
        self.assertEqual(self.member_value(e, spouse), 0)
        self.assertEqual(e.value, WORKER)


class TestScenario23HouseholdReportsSsdiAsACurrentBenefit(FederalSsdiTestCase):
    """Scenario 23: `not_receiving_ssdi` — asserts the approximation `ssdi_holder_in_household`:
    a current benefit names no member, so the whole household is excluded."""

    def test_ineligible(self) -> None:
        self.program.base_program = "ssdi"
        self.program.save()
        screen = self.make_screen()
        self.add_member(screen, age=45, monthly_income=1_000, **DISABLED)
        self.hold_current_benefit(screen, self.program)

        self.assertFalse(self.calculate(screen).eligible)


class TestScenario24LongTermConditionWithoutBeingUnableToWork(FederalSsdiTestCase):
    """Scenario 24: `disabling_condition` — the 12-month condition alone."""

    def test_ineligible(self) -> None:
        screen = self.make_screen()
        self.add_member(screen, age=45, monthly_income=1_000, long_term_disability=True)

        self.assertFalse(self.calculate(screen).eligible)


class TestScenario25UnableToWorkWithoutALongTermCondition(FederalSsdiTestCase):
    """Scenario 25: `disabling_condition` — being unable to work alone."""

    def test_ineligible(self) -> None:
        screen = self.make_screen()
        self.add_member(screen, age=45, monthly_income=1_000, disabled=True)

        self.assertFalse(self.calculate(screen).eligible)


class TestScenario26DisabledPersonAged55OverTheLimit(FederalSsdiTestCase):
    """Scenario 26: `earnings_below_sga` — the surviving spouse route carries the earnings test,
    so a disabled person aged 50 to 60 over the limit fails every route."""

    def test_ineligible(self) -> None:
        screen = self.make_screen()
        self.add_member(screen, age=55, monthly_income=1_691, **DISABLED)

        self.assertFalse(self.calculate(screen).eligible)


class TestScenario27Disabled17YearOldWithNoEarnings(FederalSsdiTestCase):
    """Scenario 27: `minor_has_earnings` — under 18 with no earnings is not taken to have work
    credits; asserts the approximation `minor_past_earnings`."""

    def test_ineligible(self) -> None:
        screen = self.make_screen(household_size=2)
        self.add_member(screen, age=40)
        self.add_member(screen, "child", age=17, **DISABLED)

        self.assertFalse(self.calculate(screen).eligible)


class TestScenario28Disabled18YearOldWithNoEarnings(FederalSsdiTestCase):
    """Scenario 28: `minor_has_earnings` — at 18 the earnings condition no longer applies."""

    def test_eligible_for_the_worker_amount(self) -> None:
        screen = self.make_screen(household_size=2)
        self.add_member(screen, age=40)
        adult_child = self.add_member(screen, "child", age=18, **DISABLED)

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(self.member_value(e, adult_child), WORKER)


class TestScenario29Disabled17YearOldWithEarnings(FederalSsdiTestCase):
    """Scenario 29: `minor_has_earnings` — under 18 and working is taken to have work credits."""

    def test_eligible_for_the_worker_amount(self) -> None:
        screen = self.make_screen(household_size=2)
        self.add_member(screen, age=40)
        teen = self.add_member(screen, "child", age=17, monthly_income=800, **DISABLED)

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(self.member_value(e, teen), WORKER)


class TestDeactivatedStateRowStillExcludes(FederalSsdiTestCase):
    """A screen saved before the move still holds a deactivated state SSDI row, under another
    name. The household is excluded by the `ssdi` group, not by this program's name."""

    def test_held_state_row_excludes_the_household(self) -> None:
        state_row = Program.objects.new_program("federal", "ssdi")
        state_row.base_program = "ssdi"
        state_row.active = False
        state_row.save()
        screen = self.make_screen()
        self.add_member(screen, age=45, monthly_income=1_000, **DISABLED)
        self.hold_current_benefit(screen, state_row)

        self.assertFalse(self.calculate(screen).eligible)


class TestFullRetirementAgeTable(FederalSsdiTestCase):
    """20 CFR 404.409(a), with a birth month standing in for the birth date."""

    def test_rows(self) -> None:
        cases = {
            date(1937, 6, 1): 65 * 12,
            date(1940, 6, 1): 65 * 12 + 6,
            date(1950, 6, 1): 66 * 12,
            date(1957, 6, 1): 66 * 12 + 6,
            date(1959, 6, 1): 66 * 12 + 10,
            date(1960, 6, 1): 67 * 12,
        }
        for birth_year_month, months in cases.items():
            with self.subTest(birth_year_month=birth_year_month):
                self.assertEqual(FederalSsdi.full_retirement_age_months(birth_year_month), months)

    def test_a_january_birth_takes_the_previous_years_row(self) -> None:
        """The table's rows start on the 2nd of January; the 1st of January belongs to the row
        before. A birth month is taken as its 1st."""
        self.assertEqual(FederalSsdi.full_retirement_age_months(date(1960, 1, 1)), 66 * 12 + 10)
        self.assertEqual(FederalSsdi.full_retirement_age_months(date(1955, 1, 1)), 66 * 12)


class TestNoBirthMonth(CustomCalculatorTestCase):
    """The tax-credit apps send an age and no birth month, so full retirement age falls back to
    the stored age against 67."""

    calculator_class = FederalSsdi
    white_label_code = "federal"
    state_code = ""

    def add_member_without_birth_month(self, screen: Screen, age: int) -> HouseholdMember:
        member = self.add_member(screen, age=age, monthly_income=1_000, **DISABLED)
        member.birth_year_month = None
        member.save()
        return member

    def test_66_is_below_full_retirement_age(self) -> None:
        screen = self.make_screen()
        self.add_member_without_birth_month(screen, 66)

        self.assertTrue(self.calculate(screen).eligible)

    def test_67_is_not(self) -> None:
        screen = self.make_screen()
        self.add_member_without_birth_month(screen, 67)

        self.assertFalse(self.calculate(screen).eligible)

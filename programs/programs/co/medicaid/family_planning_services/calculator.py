from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility
from programs.programs.helpers import medicaid_eligible
import programs.programs.messages as messages


class FamilyPlanningServices(ProgramCalculator):
    member_amount = 404
    min_age = 12
    fpl_percent = 2.65
    dependencies = ["age", "insurance", "income_frequency", "income_amount", "household_size"]

    def household_eligible(self, e: Eligibility) -> None:
        if self.program.year is None:
            e.condition(False)
            return
        # Does not have insurance
        has_no_insurance = False
        for member in self.screen.household_members.all():
            has_no_insurance = member.insurance.has_insurance_types(("none",)) or has_no_insurance
        e.condition(has_no_insurance, messages.has_no_insurance())

        # Not Medicaid eligible
        e.condition(not medicaid_eligible(self.data), messages.must_not_have_benefit("Medicaid"))

        # Income
        fpl = self.program.year
        income_limit = int(
            FamilyPlanningServices.fpl_percent * fpl.get_limit(self.screen.household_size + len(e.eligible_members))
        )
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"], exclude=["cashAssistance"]))

        e.condition(gross_income < income_limit, messages.income(gross_income, income_limit))

    def member_eligible(self, e: MemberEligibility) -> None:
        member = e.member

        # not pregnant
        e.condition(not member.pregnant)

        # age
        e.condition(member.age >= FamilyPlanningServices.min_age)

        # head or spouse
        e.condition(member.is_head() or member.is_spouse())

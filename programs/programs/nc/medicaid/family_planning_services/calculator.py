from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility
from programs.programs.helpers import medicaid_eligible
import programs.programs.messages as messages


class NCFamilyPlanningServices(ProgramCalculator):
    member_amount = 404
    min_age = 12
    fpl_percent = 1.95
    medicaid_fpl_limit = 1.38
    dependencies = ["age", "insurance", "income_frequency", "income_amount", "household_size"]
    ineligible_insurance_types = ["medicaid", "emergency_medicaid", "family_planning"]

    def household_eligible(self, e: Eligibility):

        fpl = self.program.year

        # Calculate the income limit for Family Planning Medicaid based on household size
        income_limit = int(NCFamilyPlanningServices.fpl_percent * fpl.get_limit(self.screen.household_size))

        # Calculate the household's gross yearly income, excluding cash assistance
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"], exclude=["cashAssistance"]))

        # Check if gross income is below the Family Planning Medicaid income limit
        e.condition(gross_income < income_limit, messages.income(gross_income, income_limit))

        # Exclude if eligible for full Medicaid at this income level
        income_limit_for_full_medicaid = int(
            NCFamilyPlanningServices.medicaid_fpl_limit * fpl.get_limit(self.screen.household_size)
        )
        if gross_income < income_limit_for_full_medicaid:
            e.condition(not medicaid_eligible(self.data), messages.must_not_have_benefit("Medicaid"))

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # Member must not be pregnant
        e.condition(not member.pregnant)

        # Member must not have these types of insurance.
        e.condition(not member.insurance.has_insurance_types(NCFamilyPlanningServices.ineligible_insurance_types))

        # Member must be head of household or spouse
        e.condition(member.is_head() or member.is_spouse())

        # Member must meet minimum age requirement
        e.condition(member.age >= NCFamilyPlanningServices.min_age)

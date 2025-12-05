from programs.programs.calc import ProgramCalculator, Eligibility, MemberEligibility
from programs.programs.mixins import IlTransportationMixin


class IlCommoditySupplementalFoodProgram(ProgramCalculator):
    dependencies = ["age", "county", "income"]
    eligible_counties = []
    minimum_age = 60
    fpl_percent = 1.50

    def household_eligible(self, e: Eligibility):
        e.condition(not self.screen.has_benefit("il_commodity_supplemental_food_program"))

        # 1. Eligible County
        eligible_county = self.screen.county in self.eligible_counties

        # 2. HH Income Eligibility
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))
        income_limit = int(self.fpl_percent * self.program.year.get_limit(self.screen.household_size))
        income_eligible = gross_income <= income_limit

        e.condition(eligible_county and income_eligible)

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # 3. Age eligibility
        age_eligible = member.age >= self.minimum_age
        e.condition(age_eligible)

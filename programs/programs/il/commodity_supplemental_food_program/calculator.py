from programs.programs.calc import ProgramCalculator, Eligibility, MemberEligibility
from programs.programs.mixins import IlTransportationMixin


class IlCommoditySupplementalFoodProgram(ProgramCalculator):
    dependencies = ["age", "county", "income_amount", "income_frequency", "household_size"]
    eligible_counties = [
        "Alexander",
        "Clinton",
        "Cook",
        "Edwards",
        "Franklin",
        "Hamilton",
        "Hardin",
        "Jackson",
        "Jersey",
        "Johnson",
        "Madison",
        "Massac",
        "Perry",
        "Pope",
        "Pulaski",
        "Randolph",
        "Richland",
        "Saline",
        "St. Clair",
        "Union",
        "Wabash",
        "Washington",
        "White",
        "Williamson",
    ]
    minimum_age = 60
    fpl_percent = 1.50

    def household_eligible(self, e: Eligibility):
        e.condition(not self.screen.has_benefit("il_csfp"))

        # 1. eligible county
        e.condition(self.screen.county in self.eligible_counties)

        # 2. income eligible
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))
        income_limit = int(self.fpl_percent * self.program.year.get_limit(self.screen.household_size))
        e.condition(gross_income <= income_limit)

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # 3. age eligible
        e.condition(member.age >= self.minimum_age)

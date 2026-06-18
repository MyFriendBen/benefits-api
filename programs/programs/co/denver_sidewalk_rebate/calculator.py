from integrations.services.income_limits import ami
from programs.co_county_zips import counties_from_screen
from programs.programs.calc import Eligibility, ProgramCalculator, MemberEligibility
import programs.programs.messages as messages


class DenverSidewalkRebate(ProgramCalculator):
    county = "Denver County"
    ami_percent = "60%"
    presumptive_eligibility = ["snap", "tanf", "cccap"]
    amount = 150
    dependencies = ["household_size", "income_amount", "income_frequency", "zipcode"]

    def household_eligible(self, e: Eligibility):
        # denver county condition
        counties = counties_from_screen(self.screen)
        e.condition(DenverSidewalkRebate.county in counties, messages.location())

        # income condition
        income_limit = ami.get_screen_ami(self.screen, self.ami_percent, self.program.year.period)

        income = int(self.screen.calc_gross_income("yearly", ["all"]))
        income_eligible = income <= income_limit

        # categorical eligibility
        categorical_eligible = False
        for program in DenverSidewalkRebate.presumptive_eligibility:
            if self.screen.has_benefit(program):
                categorical_eligible = True
                break

        for member in self.screen.household_members.all():
            if member.has_insurance("co_medicaid"):
                categorical_eligible = True
                break

        e.condition(categorical_eligible or income_eligible, messages.income(income, income_limit))

        # mortgage expense
        e.condition(self.screen.has_expense(["mortgage"]))

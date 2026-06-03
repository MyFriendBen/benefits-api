from integrations.services.income_limits import ami
from programs.co_county_zips import counties_from_screen
from programs.programs.calc import ProgramCalculator, Eligibility
import programs.programs.messages as messages


class DenverTrashRebate(ProgramCalculator):
    amount = 252
    ami_percent = "60%"
    county = "Denver County"
    expenses = ["rent", "mortgage"]
    dependencies = ["zipcode", "income_amount", "income_frequency", "household_size"]
    presumptive_eligibility = ["snap", "tanf", "cccap"]

    def household_eligible(self, e: Eligibility):
        # county
        counties = counties_from_screen(self.screen)
        e.condition(DenverTrashRebate.county in counties, messages.location())

        # income
        income_limit = ami.get_screen_ami(self.screen, self.ami_percent, self.program.year.period)
        income = self.screen.calc_gross_income("yearly", ["all"])
        income_eligible = income <= income_limit

        # categorical eligibility
        categorical_eligible = False
        for program in DenverTrashRebate.presumptive_eligibility:
            if self.screen.has_benefit(program):
                categorical_eligible = True
                break

        for member in self.screen.household_members.all():
            if member.has_insurance("co_medicaid"):
                categorical_eligible = True
                break

        e.condition(categorical_eligible or income_eligible, messages.income(income, income_limit))

        # has rent or mortgage expense
        has_rent_or_mortgage = self.screen.has_expense(DenverTrashRebate.expenses)
        e.condition(has_rent_or_mortgage)

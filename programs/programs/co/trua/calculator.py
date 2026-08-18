from integrations.services.income_limits import ami
from programs.framework.base import Eligibility, ProgramCalculator
import programs.framework.eligibility_messages as messages
from programs.co_county_zips import counties_from_screen


class Trua(ProgramCalculator):
    program_code = "trua"
    county = "Denver County"
    ami_percent = "80%"
    amount = 6_500
    dependencies = ["income_amount", "income_frequency", "household_size", "county"]

    def household_eligible(self, e: Eligibility):
        # income
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))
        income_limit = ami.get_screen_ami(self.screen, self.ami_percent, self.program.year.period, limit_type="il")
        e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))

        # location
        counties = counties_from_screen(self.screen)
        e.condition(Trua.county in counties, messages.location())

        # rent or mortgage expense
        has_rent_or_mortgage = self.screen.has_expense(["rent"])
        e.condition(has_rent_or_mortgage)

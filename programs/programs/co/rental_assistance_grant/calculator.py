from programs.programs.calc import ProgramCalculator, Eligibility
import programs.programs.messages as messages
from programs.co_county_zips import counties_from_screen
from integrations.services.sheets import GoogleSheetsCache
import math


class RAGCache(GoogleSheetsCache):
    default = {}
    sheet_id = "1DntpIXZfUY2yTy1_rAhaGLUH4PUAfpTSAn-j2tf2tts"
    range_name = "'2023 80% AMI'!A2:I65"

    def update(self):
        data = super().update()

        return {d[0].strip() + " County": [int(v.replace(",", "")) for v in d[1:]] for d in data}


class RentalAssistanceGrant(ProgramCalculator):
    amount = 10_000
    dependencies = ["income_amount", "income_frequency", "household_size", "zipcode"]
    income_limits = RAGCache()

    def household_eligible(self, e: Eligibility):
        # income
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))

        limits = self.income_limits.fetch()

        counties = counties_from_screen(self.screen)
        county_name = counties[0]

        for county in counties:
            if county in limits:
                county_name = county
                break

        if county_name in limits:
            income_limit = limits[county_name][self.screen.household_size - 1]
        else:
            income_limit = -math.inf

        e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))

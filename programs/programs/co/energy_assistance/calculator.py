from integrations.services.income_limits import smi
from integrations.services.sheets.sheets import GoogleSheetsCache
from programs.programs.calc import ProgramCalculator, Eligibility
import programs.programs.messages as messages
from programs.co_county_zips import counties_from_screen
import math


class LeapValueCache(GoogleSheetsCache):
    expire_time = 60 * 60 * 24
    default = []
    sheet_id = "1W8WbJsb5Mgb4CUkte2SCuDnqigqkmaO3LC0KSfhEdGg"
    range_name = "'FFY 2025'!A2:G65"

    def update(self):
        data = super().update()

        return [[self._transform_name(row[0]), self._transform_value(row[6])] for row in data if row != []]

    def _transform_name(self, raw_name: str) -> str:
        return raw_name.strip().replace("Application County: ", "") + " County"

    def _transform_value(self, raw_value: str) -> int:
        return int(float(raw_value.replace("$", "")))


class EnergyAssistance(ProgramCalculator):
    county_values = LeapValueCache()
    smi_percent = 0.6
    expenses = ["rent", "mortgage"]
    dependencies = ["income_frequency", "income_amount", "county", "household_size"]

    def household_eligible(self, e: Eligibility):
        # income
        frequency = "yearly"
        income_types = ["all"]
        income_limit = smi.get_screen_smi(self.screen, self.program.year.period) * self.smi_percent
        leap_income = self.screen.calc_gross_income(frequency, income_types)

        e.condition(leap_income <= income_limit, messages.income(leap_income, income_limit))

        # has rent or mortgage expense
        e.condition(self._has_expense())

        # does not already have LEAP
        e.condition(not self.screen.has_benefit("leap"))

    def _has_expense(self):
        return self.screen.has_expense(EnergyAssistance.expenses)

    def household_value(self):
        data = self.county_values.fetch()

        # if there is no county, then we want to estimate based off of zipcode
        counties = counties_from_screen(self.screen)

        values = []
        for row in data:
            county = row[0]
            if county in counties:
                values.append(row[1])

        value = 362
        lowest = math.inf

        # get lowest value from zipcodes
        for possible_value in values:
            if possible_value < lowest:
                value = possible_value
                lowest = possible_value

        return value

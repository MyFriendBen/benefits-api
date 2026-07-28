from integrations.services.income_limits import smi
from integrations.services.sheets.cache import GoogleSheetsCache
from programs.programs.calc import ProgramCalculator, Eligibility
import programs.programs.messages as messages
from programs.co_county_zips import counties_from_screen
import math


class LeapValueCache(GoogleSheetsCache):
    CACHE_KEY = "leap_value_data"
    sheet_id = "1W8WbJsb5Mgb4CUkte2SCuDnqigqkmaO3LC0KSfhEdGg"
    range_name = "'FFY 2025'!A2:G65"

    def _empty_fallback(self):
        # household_value() iterates this as a list of [county, value] pairs,
        # not a dict, so the fallback must match that shape.
        return []

    def _process(self, raw_data):
        result = []
        for row in raw_data:
            if row == []:
                continue
            try:
                result.append([self._transform_name(row[0]), self._transform_value(row[6])])
            except (IndexError, ValueError, AttributeError):
                continue  # Skip short/malformed rows
        return result

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

    def _has_expense(self):
        return self.screen.has_expense(EnergyAssistance.expenses)

    def household_value(self):
        data = self.county_values.get_data()

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

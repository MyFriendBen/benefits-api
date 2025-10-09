from integrations.services.sheets import GoogleSheetsCache
from programs.co_county_zips import counties_from_screen
from programs.programs.calc import Eligibility, ProgramCalculator
from programs.programs.co.income_limits_cache.income_limits_cache import IncomeLimitsCache
import programs.programs.messages as messages


class WeatherizationAssistance(ProgramCalculator):
    presumptive_eligibility = ("andcs", "ssi", "snap", "leap", "tanf")
    amount = 350
    dependencies = ["household_size", "income_amount", "income_frequency", "county"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.income_limits = IncomeLimitsCache()

    def household_eligible(self, e: Eligibility):
        # income condition
        counties = counties_from_screen(self.screen)
        income_limits = []
        for county in counties:
            income_limits.append(self.income_limits.fetch()[county][self.screen.household_size - 1])
        income_limit = min(income_limits)

        income = int(self.screen.calc_gross_income("yearly", ["all"]))
        income_eligible = income <= income_limit

        # categorical eligibility
        categorical_eligible = False
        for program in WeatherizationAssistance.presumptive_eligibility:
            if self.screen.has_benefit(program):
                categorical_eligible = True
                break
        e.condition(income_eligible or categorical_eligible, messages.income(income, income_limit))

        # rent or mortgage expense
        e.condition(self._has_expense())

        # utility providers
        e.condition(self._has_utility_provider())

    def _has_expense(self):
        return self.screen.has_expense(["rent", "mortgage"])

    def _has_utility_provider(self):
        return True

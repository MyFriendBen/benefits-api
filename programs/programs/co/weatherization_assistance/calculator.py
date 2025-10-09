from programs.programs.calc import Eligibility, ProgramCalculator
from programs.programs.co.income_limits_cache.income_limits_cache import IncomeLimitsCache
import programs.programs.messages as messages
from programs.programs.co.energy_programs_shared.income_validation import validate_income_limits


class WeatherizationAssistance(ProgramCalculator):
    presumptive_eligibility = ("andcs", "ssi", "snap", "leap", "tanf")
    amount = 350
    dependencies = ["household_size", "income_amount", "income_frequency", "county"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.income_limits = IncomeLimitsCache()

    def household_eligible(self, e: Eligibility):
        # income condition
        income_eligible, income, income_limit = validate_income_limits(self.screen, e, self.income_limits)

        if income_limit is None:
            # Income validation failed completely, validation function already set condition
            return

        # categorical eligibility
        categorical_eligible = False
        for program in WeatherizationAssistance.presumptive_eligibility:
            if self.screen.has_benefit(program):
                categorical_eligible = True
                break

        # Override the income eligibility condition with combined result
        e.condition(income_eligible or categorical_eligible, messages.income(income, income_limit))

        # rent or mortgage expense
        e.condition(self._has_expense())

        # utility providers
        e.condition(self._has_utility_provider())

    def _has_expense(self):
        return self.screen.has_expense(["rent", "mortgage"])

    def _has_utility_provider(self):
        return True

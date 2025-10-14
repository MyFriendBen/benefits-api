from programs.programs.calc import Eligibility, ProgramCalculator
from programs.programs.co.energy_programs_shared.income_limits_cache import IncomeLimitsCache
import programs.programs.messages as messages
from programs.programs.co.energy_programs_shared.income_validation import get_income_limit, _get_county_name
from typing import ClassVar


class WeatherizationAssistance(ProgramCalculator):
    presumptive_eligibility = ("andcs", "ssi", "snap", "leap", "tanf")
    amount = 350
    dependencies: ClassVar[list[str]] = ["household_size", "income_amount", "income_frequency", "county"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.income_limits = IncomeLimitsCache()

    def household_eligible(self, e: Eligibility):
        # Check categorical eligibility first
        categorical_eligible = False
        categorical_eligible = any(
            self.screen.has_benefit(program) for program in WeatherizationAssistance.presumptive_eligibility
        )

        # Get income limit (data retrieval only - NO conditions set)
        income_limit, error_detail = get_income_limit(self.screen, self.income_limits)

        # Handle case where income limit data is missing
        if income_limit is None:
            # Log to Sentry regardless of categorical eligibility
            county = _get_county_name(self.screen)
            size_index = self.screen.household_size - 1
            # Call income_limit_unknown to log to Sentry (discards the message tuple)
            error_message = messages.income_limit_unknown(error_detail, county, size_index)

            # If categorically eligible, pass anyway (no income check needed)
            if categorical_eligible:
                e.condition(True)
            else:
                # Not categorically eligible and no income data - fail with message
                e.condition(False, error_message)
                return
        else:
            # We have income limit data - check income
            user_income = int(self.screen.calc_gross_income("yearly", ["all"]))
            income_eligible = user_income <= income_limit

            # Pass if EITHER income eligible OR categorically eligible
            e.condition(income_eligible or categorical_eligible, messages.income(user_income, income_limit))

        # rent or mortgage expense
        e.condition(self._has_expense())

        # utility providers
        e.condition(self._has_utility_provider())

    def _has_expense(self):
        return self.screen.has_expense(["rent", "mortgage"])

    def _has_utility_provider(self):
        return True

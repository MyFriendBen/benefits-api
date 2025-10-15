from programs.programs.calc import Eligibility, ProgramCalculator
import programs.programs.messages as messages
from programs.programs.co.energy_programs_shared.income_validation import get_income_limit
from typing import ClassVar


class WeatherizationAssistance(ProgramCalculator):
    presumptive_eligibility = ("andcs", "ssi", "snap", "leap", "tanf")
    amount = 350
    dependencies: ClassVar[list[str]] = ["household_size", "income_amount", "income_frequency", "county"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def household_eligible(self, e: Eligibility):
        # Check presumptive eligibility first
        presumed_eligibility = any(
            self.screen.has_benefit(program) for program in WeatherizationAssistance.presumptive_eligibility
        )

        # Must have EITHER income eligible OR presumed eligibility
        if presumed_eligibility:
            e.condition(presumed_eligibility, messages.presumed_eligibility)
        else: 
            # check income limit
            income_limit = get_income_limit(self.screen)
            if income_limit: 
                user_income = int(self.screen.calc_gross_income("yearly", ["all"]))
                income_eligible = user_income <= income_limit
                e.condition(income_eligible, messages.income(user_income, income_limit))
            else: 
                # no income limit data
                e.condition(False, messages.income_limit_unknown())

        # rent or mortgage expense
        e.condition(self._has_expense())

        # utility providers
        e.condition(self._has_utility_provider())

    def _has_expense(self):
        return self.screen.has_expense(["rent", "mortgage"])

    def _has_utility_provider(self):
        return True

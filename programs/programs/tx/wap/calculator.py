from programs.programs.calc import ProgramCalculator, Eligibility
import programs.programs.messages as messages
from typing import ClassVar


class TxWap(ProgramCalculator):
    fpl_percent = 2
    amount = 372
    # NOTE: LIHEAP should also qualify for categorical eligibility, but is not currently available for TX
    categorically_eligible = ["ssi", "tanf", "snap"]
    dependencies: ClassVar[list[str]] = [
        "household_size",
        "income_amount",
        "income_frequency",
    ]

    def household_eligible(self, e: Eligibility):
        categorically_eligible = any(
            self.screen.has_benefit(program) for program in self.categorically_eligible
        )

        if categorically_eligible:
            e.condition(True, messages.presumed_eligibility())
        else:
            gross_income = self.screen.calc_gross_income("yearly", ["all"])
            income_limit = int(self.fpl_percent * self.program.year.get_limit(self.screen.household_size))
            e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))

from programs.programs.calc import ProgramCalculator, Eligibility
import programs.programs.messages as messages
from typing import ClassVar


class TxWap(ProgramCalculator):
    fpl_percent = 2
    amount = 372
    dependencies: ClassVar[list[str]] = [
        "household_size",
        "income_amount",
        "income_frequency",
    ]

    def household_eligible(self, e: Eligibility):
        # Categorical eligibility: SSI, TANF, or SNAP bypass the income test
        categorical_eligible = (
            self.screen.has_benefit("ssi")
            or self.screen.has_benefit("tanf")
            or self.screen.has_benefit("snap")
        )

        if categorical_eligible:
            e.condition(True, messages.presumed_eligibility())
        else:
            gross_income = self.screen.calc_gross_income("yearly", ["all"])
            income_limit = int(self.fpl_percent * self.program.year.get_limit(self.screen.household_size))
            e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))

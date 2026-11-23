from programs.framework.base import ProgramCalculator, Eligibility
import programs.framework.eligibility_messages as messages
from typing import ClassVar
from programs.programs.shared.income import fpl_income_limit


class TxWap(ProgramCalculator):
    program_code = "tx_wap"
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
        categorically_eligible = self.screen.has_benefit_from_list(self.categorically_eligible)

        if categorically_eligible:
            e.condition(True, messages.presumed_eligibility())
        else:
            gross_income = self.screen.calc_gross_income("yearly", ["all"])
            income_limit = fpl_income_limit(self.program.year, self.screen.household_size, self.fpl_percent)
            e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))

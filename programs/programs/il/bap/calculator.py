from programs.programs.calc import ProgramCalculator, Eligibility
from programs.programs.mixins import IlTransportationMixin
import programs.programs.messages as messages


class IlBenefitAccess(IlTransportationMixin, ProgramCalculator):
    dependencies = [
        "age",
        "household_size",
        "income_amount",
        "income_frequency",
        "visually_impaired",
        "disabled",
    ]
    income_limit_by_household_size = {
        1: 33_562,
        2: 44_533,
        3: 55_500,
    }

    def household_eligible(self, e: Eligibility):
        e.condition(not self.screen.has_benefit("il_bap"))

        household_size = self.screen.household_size
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))

        income_limit = self.income_limit_by_household_size[min(household_size, 3)]
        income_eligible = gross_income <= income_limit

        e.condition((household_size <= 3) and income_eligible)

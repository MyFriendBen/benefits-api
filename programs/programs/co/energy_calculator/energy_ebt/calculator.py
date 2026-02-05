from programs.programs.calc import Eligibility, ProgramCalculator


class EnergyCalculatorEnergyEbt(ProgramCalculator):
    amount = 21
    max_fpl = 2
    dependencies = ["income_frequency", "income_amount", "household_size"]

    def household_eligible(self, e: Eligibility):
        # income
        income = self.screen.calc_gross_income("yearly", ["all"])
        income_limit = self.program.year.as_dict()[self.screen.household_size] * self.max_fpl
        e.condition(income <= income_limit)

        # no LEAP
        can_get_leap = self.screen.has_leap or self.data["cesn_leap"].eligible
        e.condition(not can_get_leap)

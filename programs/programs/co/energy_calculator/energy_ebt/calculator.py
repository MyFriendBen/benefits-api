from programs.programs.calc import Eligibility, ProgramCalculator


class EnergyCalculatorEnergyEbt(ProgramCalculator):
    amount = 21
    max_fpl = 2
    dependencies = ["income_frequency", "income_amount", "household_size"]

    def household_eligible(self, e: Eligibility) -> None:
        if self.program.year is None:
            return
        # income
        income = self.screen.calc_gross_income("yearly", ["all"])
        income_limit = self.program.year.as_dict()[self.screen.household_size] * self.max_fpl
        e.condition(income <= income_limit)

        # no LEAP
        cesn_leap = self.data.get("cesn_leap")
        already_has_leap = self.screen.has_benefit("cesn_leap")
        can_get_leap = already_has_leap or (cesn_leap is not None and cesn_leap.eligible)
        e.condition(not can_get_leap)

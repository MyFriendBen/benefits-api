from programs.framework.base import Eligibility, ProgramCalculator
from programs.programs.cross_white_label.liheap.cesn import EnergyCalculatorEnergyAssistance


class EnergyCalculatorEnergyEbt(ProgramCalculator):
    program_code = "cesn_energy_ebt"
    amount = 21
    max_fpl = 2
    # Includes cesn_leap's dependencies because the LEAP exclusion below reads its result.
    # Without them this program can be calculable on a screen where cesn_leap is not — LEAP
    # needs `county` and this does not — and the gate would then raise on a household this
    # program could otherwise have answered for. Declaring the upstream's fields makes the
    # two drop out together.
    dependencies = [
        "income_frequency",
        "income_amount",
        "household_size",
        *EnergyCalculatorEnergyAssistance.dependencies,
    ]

    def household_eligible(self, e: Eligibility):
        # income
        income = self.screen.calc_gross_income("yearly", ["all"])
        income_limit = self.program.year.as_dict()[self.screen.household_size] * self.max_fpl
        e.condition(income <= income_limit)

        # no LEAP
        already_has_leap = self.screen.has_benefit("cesn_leap")
        can_get_leap = already_has_leap or self.program_eligible("cesn_leap")
        e.condition(not can_get_leap)

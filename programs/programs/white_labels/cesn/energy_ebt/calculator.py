from programs.framework.base import Eligibility, ProgramCalculator


class EnergyCalculatorEnergyEbt(ProgramCalculator):
    program_code = "cesn_energy_ebt"
    amount = 21
    max_fpl = 2
    # An exclusion, so absence must not read as "no LEAP" — hence the strict accessor. LEAP
    # is custom and force-calculated, so the gate survives its row being deactivated, and
    # `all_dependencies` pulls in LEAP's screener fields (this program does not need
    # `county` on its own) so the two still drop out together on an incomplete screen.
    gates_on = ("cesn_leap",)
    dependencies = ["income_frequency", "income_amount", "household_size"]

    def household_eligible(self, e: Eligibility):
        # income
        income = self.screen.calc_gross_income("yearly", ["all"])
        income_limit = self.program.year.as_dict()[self.screen.household_size] * self.max_fpl
        e.condition(income <= income_limit)

        # no LEAP
        already_has_leap = self.screen.has_benefit("cesn_leap")
        can_get_leap = already_has_leap or self.program_eligible("cesn_leap")
        e.condition(not can_get_leap)

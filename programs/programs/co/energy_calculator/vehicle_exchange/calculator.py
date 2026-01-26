from integrations.services.income_limits import ami
from programs.programs.calc import Eligibility, MemberEligibility, ProgramCalculator

"""
As of January 21, 2026, the EnergyCalculatorVehicleExchange program has been set to inactive in CESN
since we switched to retrieving the details via the Rewiring America API.
"""


class EnergyCalculatorVehicleExchange(ProgramCalculator):
    amount = 4_000
    min_age = 18
    ami_percent = "80%"
    presumptive_eligibility = ["co_care", "cowap", "rtdlive", "section_8", "ssdi", "wic", "leap", "snap", "ssi"]
    calculated_presumptive_eligibility = ["co_energy_calculator_care", "co_energy_calculator_cowap"]
    dependencies = ["age", "income_frequency", "income_amount", "energy_calculator"]

    def household_eligible(self, e: Eligibility):
        # presumptive eligibility
        has_benefit = False
        for benefit in self.presumptive_eligibility:
            if self.screen.has_benefit(benefit):
                has_benefit = True

        for program in self.calculated_presumptive_eligibility:
            if self.data[program].eligible:
                has_benefit = True

        # income
        income_limit = ami.get_screen_ami(self.screen, self.ami_percent, self.program.year.period)
        income = self.screen.calc_gross_income("yearly", ["all"])
        income_eligble = income <= income_limit

        e.condition(income_eligble or has_benefit)

        # has old car
        e.condition(self.screen.energy_calculator.has_old_car)

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # age
        e.condition(member.age >= self.min_age)

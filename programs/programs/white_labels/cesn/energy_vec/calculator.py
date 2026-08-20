from integrations.services.income_limits import ami
from programs.framework.base import Eligibility, MemberEligibility, ProgramCalculator

"""
As of January 21, 2026, the EnergyCalculatorVehicleExchange program has been set to inactive in CESN
since we switched to retrieving the details via the Rewiring America API.
"""


class EnergyCalculatorVehicleExchange(ProgramCalculator):
    program_code = "cesn_energy_vec"
    amount = 4_000
    min_age = 18
    ami_percent = "80%"
    # Exact CESN names alongside base_program groups; has_benefit_from_list resolves
    # either. WAP is absent because it's read as calculated eligibility below.
    presumptive_eligibility = [
        "cesn_care",
        "cesn_rtdlive",
        "cesn_section_8",
        "liheap",
        "ssdi",
        "wic",
        "snap",
        "ssi",
    ]
    calculated_presumptive_eligibility = ["cesn_care", "cesn_cowap"]
    dependencies = ["age", "income_frequency", "income_amount", "energy_calculator"]

    def household_eligible(self, e: Eligibility):
        # presumptive eligibility
        has_benefit = self.screen.has_benefit_from_list(self.presumptive_eligibility)

        has_benefit = has_benefit or self.any_program_eligible(self.calculated_presumptive_eligibility)

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

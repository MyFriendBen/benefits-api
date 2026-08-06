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
    # CESN program (see cesn_calculators), so CESN's own names are what the join table can
    # hold — the previous CO names (co_care, cowap, rtdlive, leap) match nothing on a CESN
    # screen. has_benefit_from_list takes each entry as either an exact name or a
    # base_program group, so both kinds can sit in one list.
    #
    # cesn_care / cesn_rtdlive / cesn_section_8 are reportable (show_in_has_benefits_step).
    # liheap / wap are the base_program groups for cesn_leap / cesn_cowap, which are not
    # reportable — CESN's category_benefits offers "leap" and "cowap", names that match no
    # CESN program and are dropped on write, so those two legs stay False until that config
    # gap is fixed (tracked separately).
    presumptive_eligibility = [
        "cesn_care",
        "cesn_rtdlive",
        "cesn_section_8",
        "liheap",
        "wap",
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

        for program in self.calculated_presumptive_eligibility:
            entry = self.data.get(program)
            if entry is not None and entry.eligible:
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

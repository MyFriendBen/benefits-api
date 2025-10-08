# from programs.co_county_zips import counties_from_screen
from programs.programs.co.energy_calculator.energy_assistance.calculator import EnergyCalculatorEnergyAssistance
from programs.programs.calc import Eligibility, ProgramCalculator


class EnergyCalculatorProject_COPE(ProgramCalculator):
    
    # presumptive_eligibility = ["leap"]
    presumptive_eligibility = ["co_energy_calculator_leap"]
    
    electricity_providers = ["co-colorado-springs-utilities"]
    gas_providers = ["co-colorado-springs-utilities"]
    def household_eligible(self, e: Eligibility):
        

        # eligible for LEAP
        leap_eligible = self.data["co_energy_calculator_leap"].eligible
        e.condition(leap_eligible)

        e.condition(self.screen.energy_calculator.has_utility_provider(self.electricity_providers + self.gas_providers))

        # other conditions
        return super().household_eligible(e)
    

    # amount = 1
    # county = "Denver County"
    # fpl_percent = 4
    # dependencies = ["energy_calculator", "household_size", "income_amount", "income_frequency", "zipcode"]
    # def household_eligible(self, e: Eligibility):
    #     # eligible for LEAP
    #     leap_eligible = self.data["co_energy_calculator_leap"].eligible
    #     e.condition(leap_eligible)

    #     # heating is not working
    #     needs_heating = self.screen.energy_calculator.needs_hvac
    #     e.condition(needs_heating)

    #     # no renters without expenses
    #     e.condition(has_renter_expenses(self.screen))
    # location
        # counties = counties_from_screen(self.screen)
        # e.condition(self.county in counties)

        # income
        # limit = self.program.year.as_dict()[self.screen.household_size] * self.fpl_percent
        # income = self.screen.calc_gross_income("yearly", ["all"])
        # e.condition(income <= limit)

        #  has_another_program = False
        # for program in self.presumptive_eligibility:
        #     eligible = self.data[program].eligible
        #     if eligible:
        #         has_another_program = True
        # e.condition(has_another_program)

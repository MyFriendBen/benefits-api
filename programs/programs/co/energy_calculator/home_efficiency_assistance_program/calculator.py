import programs.programs.messages as messages
from integrations.services.income_limits import smi
from programs.programs.calc import Eligibility, ProgramCalculator


class EnergyCalculatorHomeEfficiencyAssistance(ProgramCalculator):
    """
    Home Efficiency Assistance Program (HEAP) calculator for Colorado Springs Utilities.

    This program provides weatherization and energy efficiency improvements to eligible households
    in the Colorado Springs Utilities service area.

    Eligibility criteria:
    - Must not already have CESN HEAP benefits
    - Either:
        a) Presumptive eligibility through LEAP participation, OR
        b) Meet all of the following:
            - Customer of Colorado Springs Utilities (gas or electric)
            - Homeowner
            - Income at or below 60% of State Median Income (SMI)
    """

    amount = 1  # Benefit amount not calculated; eligibility determination only
    dependencies = [
        "household_size",
        "income_amount",
        "income_frequency",
        "county",
        "energy_calculator",
    ]
    presumptive_eligibility = [
        "leap",
    ]
    utility_providers = [
        "co-colorado-springs-utilities",
        "co-colorado-springs-utilities-gas",
    ]
    smi_percent = 0.6

    def household_eligible(self, e: Eligibility):

        # check if has any of the presumptive eligibility programs
        presumed_eligible = any(self.screen.has_benefit(program) for program in self.presumptive_eligibility)

        if presumed_eligible:
            # if presumptive eligibility, done
            e.condition(presumed_eligible, messages.presumed_eligibility())
        else:
            # otherwise, must meet all 3 conditions
            energy_calculator_screen = self.screen.energy_calculator
            has_relevant_provider = energy_calculator_screen.has_utility_provider(self.utility_providers)
            e.condition(
                has_relevant_provider,
                messages.has_utility_provider(self.utility_providers),
            )

            e.condition(energy_calculator_screen.is_home_owner, messages.is_home_owner())

            income_limit = smi.get_screen_smi(self.screen, self.program.year.period) * self.smi_percent
            income = int(self.screen.calc_gross_income("yearly", ["all"]))
            income_eligible = income <= income_limit
            e.condition(income_eligible, messages.income(income, income_limit))

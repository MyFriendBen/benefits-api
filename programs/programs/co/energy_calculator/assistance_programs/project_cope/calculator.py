from programs.programs.calc import Eligibility, ProgramCalculator
from programs.programs.co.energy_calculator.util import has_renter_expenses


class EnergyCalculatorProjectCOPE(ProgramCalculator):
    amount = 1
    dependencies = ["energy_calculator"]
    electricity_providers = ["co-colorado-springs-utilities"]
    gas_providers = ["co-colorado-springs-utilities"]

    def household_eligible(self, e: Eligibility):
        # utility provider check
        # e.condition(self.screen.energy_calculator.has_utility_provider(self.electricity_providers + self.gas_providers))
        print(self.screen.energy_calculator.has_utility_provider(self.electricity_providers))
        e.condition(self.screen.energy_calculator.has_utility_provider(self.electricity_providers))
        print(e.condition(self.screen.energy_calculator.has_utility_provider(self.electricity_providers)))
        print(e.condition(
             self.screen.energy_calculator.electricity_is_disconnected
        #     or self.screen.energy_calculator.has_past_due_energy_bills
        ))
        print(self.screen.energy_calculator.electricity_is_disconnected)
        # past due or disconnected
        # e.condition(
        #     self.screen.energy_calculator.electricity_is_disconnected
        #     or self.screen.energy_calculator.has_past_due_energy_bills
        # )

        # no renters without expenses
        # e.condition(has_renter_expenses(self.screen))

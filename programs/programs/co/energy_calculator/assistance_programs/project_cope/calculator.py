from programs.programs.calc import Eligibility, ProgramCalculator


class EnergyCalculatorProjectCOPE(ProgramCalculator):
    amount = 1
    dependencies = ["energy_calculator"]
    utility_providers = ["co-colorado-springs-utilities", "co-colorado-springs-utilities-gas"]

    def household_eligible(self, e: Eligibility):

        # utility provider checks (electric or gas)
        e.condition(self.screen.energy_calculator.has_utility_provider(self.utility_providers))

        # past due or disconnected
        e.condition(
            self.screen.energy_calculator.electricity_is_disconnected
            or self.screen.energy_calculator.has_past_due_energy_bills
        )

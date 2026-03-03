from programs.programs.calc import Eligibility, ProgramCalculator


class LarimerCountyConservationCorps(ProgramCalculator):
    amount = 1
    dependencies = ["energy_calculator"]
    utility_providers = [
        "co-fort-collins-utilities",
        "co-loveland-water-and-power",
    ]

    def household_eligible(self, e: Eligibility):
        # must be a Fort Collins Utilities or Loveland Utilities customer
        e.condition(self.screen.energy_calculator.has_utility_provider(self.utility_providers))

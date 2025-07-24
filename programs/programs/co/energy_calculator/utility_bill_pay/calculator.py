from programs.programs.calc import Eligibility
from programs.programs.co.energy_calculator.util import has_renter_expenses
from programs.programs.co.utility_bill_pay.calculator import UtilityBillPay


class EnergyCalculatorUtilityBillPay(UtilityBillPay):
    dependencies = [*UtilityBillPay.dependencies, "energy_calculator"]
    electricity_providers = ["co-xcel-energy", "co-black-hills-energy"]
    gas_providers = [
        "co-atmos-energy",
        "co-black-hills-energy-gas",
        "co-colorado-natural-gas",
        "co-xcel-energy-gas",
    ]

    def household_eligible(self, e: Eligibility):
        # energy provider
        e.condition(self.screen.energy_calculator.has_utility_provider(self.electricity_providers + self.gas_providers))

        # other conditions
        return super().household_eligible(e)

    def _has_expense(self):
        # no renters without expenses
        return has_renter_expenses(self.screen)

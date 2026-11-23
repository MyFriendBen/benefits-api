from programs.framework.base import Eligibility, ProgramCalculator
from programs.programs.white_labels.cesn.util import has_renter_expenses


class EnergyCalculatorEnergyOutreachCrisisIntervention(ProgramCalculator):
    program_code = "cesn_eoccip"
    # A custom calculator, so it is force-calculated: this gate cannot be starved by LEAP's
    # Program row going inactive or being removed for a referrer. Kept as a dependency
    # rather than restated inline because CESN's LEAP overrides `_has_expense` to True,
    # leaving a 60% SMI test that would have to be duplicated here to inline it.
    gates_on = ("cesn_leap",)
    amount = 1
    dependencies = ["energy_calculator"]

    def household_eligible(self, e: Eligibility):
        # eligible for LEAP
        e.condition(self.program_eligible("cesn_leap"))

        # heating is not working
        needs_heating = self.screen.energy_calculator.needs_hvac
        e.condition(needs_heating)

        # no renters without expenses
        e.condition(has_renter_expenses(self.screen))

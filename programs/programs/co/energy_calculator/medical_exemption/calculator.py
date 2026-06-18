from programs.programs.calc import Eligibility, MemberEligibility, ProgramCalculator


class EnergyCalculatorMedicalExemption(ProgramCalculator):
    amount = 1
    max_fpl = 4
    providers = ["co-xcel-energy"]
    dependencies = ["income_frequency", "income_amount", "household_size", "energy_calculator"]

    def household_eligible(self, e: Eligibility) -> None:
        if self.program.year is None:
            return
        # income
        income = self.screen.calc_gross_income("yearly", ["all"])
        income_limit = self.program.year.as_dict()[self.screen.household_size] * self.max_fpl
        e.condition(income <= income_limit)

        # has exel
        e.condition(self.screen.energy_calculator.has_electricity_provider(self.providers))

    def member_eligible(self, e: MemberEligibility) -> None:
        # has medical equipment
        e.condition(e.member.energy_calculator.medical_equipment)

from programs.programs.calc import Eligibility, MemberEligibility, ProgramCalculator


class EnergyCalculatorMedicalCertification(ProgramCalculator):
    amount = 1
    providers = ["co-xcel-energy"]
    dependencies = ["income_frequency", "income_amount", "household_size", "energy_calculator"]

    def household_eligible(self, e: Eligibility) -> None:
        # has exel
        e.condition(self.screen.energy_calculator.has_electricity_provider(self.providers))

    def member_eligible(self, e: MemberEligibility) -> None:
        # has medical equipment
        e.condition(e.member.energy_calculator.medical_equipment)

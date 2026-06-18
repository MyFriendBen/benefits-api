from programs.programs.calc import MemberEligibility
from programs.programs.co.property_credit_rebate.calculator import PropertyCreditRebate
from screener.models import HouseholdMember


class EnergyCalculatorPropertyCreditRebate(PropertyCreditRebate):
    surviving_spouse_age = 58
    dependencies = [*PropertyCreditRebate.dependencies, "energy_calculator"]

    def _has_expense(self) -> bool:
        return True

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # not a dependent
        e.condition(not member.is_dependent())

        # other conditions
        return super().member_eligible(e)

    def _member_is_disabled(self, member: HouseholdMember):
        has_disability = member.has_disability()
        disability_age_eligible = (member.age or 0) > self.disabled_min_age
        receives_ssi = member.energy_calculator.receives_ssi

        return has_disability and disability_age_eligible and receives_ssi

    def _is_surviving_spouse(self, member: HouseholdMember):
        return member.energy_calculator.surviving_spouse and (member.age or 0) >= self.surviving_spouse_age

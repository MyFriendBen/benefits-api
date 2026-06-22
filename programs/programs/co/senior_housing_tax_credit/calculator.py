from programs.programs.calc import Eligibility, MemberEligibility, ProgramCalculator
import math


class SeniorHousingIncomeTaxCredit(ProgramCalculator):
    amount = 800
    income_reduction = 25000
    reduction_interval = 500
    single_filer_credit_reduction = 8
    joint_filer_credit_reduction = 4
    age_eligible = 65

    dependencies = [
        "income_amount",
        "income_frequency",
        "income_type",
        "age",
    ]

    def household_eligible(self, e: Eligibility) -> None:
        has_rent_or_mortgage_or_property_tax = self.screen.has_expense(["rent", "mortgage", "propertyTax"])
        e.condition(has_rent_or_mortgage_or_property_tax)

    def member_eligible(self, e: MemberEligibility) -> None:
        member = e.member

        if member.age is None:
            return

        # head or spouse
        e.condition(member.is_head() or member.is_spouse())
        e.condition(member.age >= self.age_eligible)

    def household_value(self):
        reduction_per_interval = (
            self.joint_filer_credit_reduction if self.screen.is_joint() else self.single_filer_credit_reduction
        )

        # income
        total_income = self.screen.calc_gross_income("yearly", ["all"])
        excess_income = max(total_income - self.income_reduction, 0)
        intervals = math.ceil(excess_income / self.reduction_interval)
        return self.amount - reduction_per_interval * intervals

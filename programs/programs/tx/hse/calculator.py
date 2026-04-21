from programs.programs.calc import ProgramCalculator, Eligibility
from typing import ClassVar


class TxHse(ProgramCalculator):
    amount = 400
    senior_disabled_amount = 600
    senior_age = 65
    dependencies: ClassVar[list[str]] = ["age"]

    def household_eligible(self, e: Eligibility):
        e.condition(self.screen.has_expense(["mortgage"]))

    def household_value(self) -> int:
        for member in self.screen.household_members.all():
            if member.age is not None and member.age >= self.senior_age:
                return self.senior_disabled_amount
            if member.has_disability():
                return self.senior_disabled_amount
        return self.amount

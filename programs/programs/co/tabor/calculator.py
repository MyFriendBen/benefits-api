from programs.programs.calc import MemberEligibility, ProgramCalculator
from screener.models import HouseholdMember
import math


class Tabor(ProgramCalculator):
    min_age = 18
    member_amount = 800
    income_limits = {
        53_000: 177,
        105_000: 240,
        166_000: 277,
        233_000: 323,
        302_000: 350,
        math.inf: 565,
    }
    dependencies = ["age"]

    def member_eligible(self, e: MemberEligibility) -> None:
        member = e.member

        # age
        if member.age is None:
            return
        e.condition(member.age >= Tabor.min_age)

    def member_value(self, member: HouseholdMember) -> int:
        income = member.calc_gross_income("yearly", ["all"])

        # Add spouses income
        is_married = member.is_married()
        if is_married["is_married"]:
            spouse = is_married["married_to"]
            if isinstance(spouse, HouseholdMember):
                income += spouse.calc_gross_income("yearly", ["all"])

        for threshold, value in Tabor.income_limits.items():
            if income <= threshold:
                return value

        return 0  # just in case

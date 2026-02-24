from programs.programs.calc import MemberEligibility, ProgramCalculator
from screener.models import HouseholdMember


class UniversalPreschool(ProgramCalculator):
    qualifying_age = 3
    age = 4
    income_limit = 1
    foster_income_limit = 2.7
    amount_10_hr = 4_956
    amount_15_hr = 6_240
    amount_30_hr = 11_088
    dependencies = ["age", "income_amount", "income_frequency", "relationship", "household_size"]

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # qualifying condition
        qualifying_condition = self._has_qualifying_condition(member)

        # age
        min_age = UniversalPreschool.qualifying_age if qualifying_condition else UniversalPreschool.age
        e.condition(min_age <= member.age <= UniversalPreschool.age)

    def member_value(self, member: HouseholdMember):
        qualifying_condition = self._has_qualifying_condition(member)

        if not qualifying_condition:
            return UniversalPreschool.amount_15_hr

        if member.age == UniversalPreschool.age:
            return UniversalPreschool.amount_30_hr

        return UniversalPreschool.amount_10_hr

    def _has_qualifying_condition(self, member: HouseholdMember):
        fpl = self.program.year.as_dict()[self.screen.household_size]
        income = self.screen.calc_gross_income("yearly", ["all"])

        income_limit = int(UniversalPreschool.income_limit * fpl)

        if member.relationship == "fosterChild":
            income_limit = int(UniversalPreschool.foster_income_limit * fpl)

        return income <= income_limit

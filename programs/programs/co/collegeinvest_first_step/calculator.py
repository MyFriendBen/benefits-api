from programs.programs.calc import MemberEligibility, ProgramCalculator


class CoCollegeInvestFirstStep(ProgramCalculator):
    """
    Colorado CollegeInvest First Step.

    One-time $121 seed deposit into a 529 college savings account for each child
    born or adopted in Colorado, aged 0–7, born on or after January 1, 2020.

    No income limit. Data gaps: birth/adoption location (CO residency used as proxy)
    and the military exception (active military families with permanent CO residence
    qualify even if the child was born out of state) are not verifiable from screener
    data; both gaps are noted in the program description.
    """

    member_amount = 121
    max_age = 7
    min_birth_year = 2020
    child_relationships = ["child", "stepChild", "fosterChild", "grandChild"]
    dependencies = ["age", "relationship", "birth_year"]

    def member_eligible(self, e: MemberEligibility) -> None:
        member = e.member

        e.condition(member.relationship in self.child_relationships)
        e.condition(member.age is not None and member.age <= self.max_age)
        e.condition(member.birth_year is not None and member.birth_year >= self.min_birth_year)

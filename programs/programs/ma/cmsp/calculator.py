from programs.programs.calc import ProgramCalculator, MemberEligibility


class MaCmsp(ProgramCalculator):
    """
    Children's Medical Security Plan (CMSP) - Massachusetts

    Low-cost health coverage for uninsured children under age 19.
    No income limit. No citizenship requirement.

    Sources:
    - https://www.mass.gov/childrens-medical-security-plan
    """

    # $239/month matches MaMassHealth child coverage values (YOUNG_CHILD, OLDER_CHILD, INFANT)
    member_amount = 239
    dependencies = ["age", "health_insurance"]

    def member_eligible(self, e: MemberEligibility) -> None:
        member = e.member

        # Child must be under age 19
        e.condition(member.age < 19)

        # Child must be currently uninsured
        e.condition(member.insurance.none)

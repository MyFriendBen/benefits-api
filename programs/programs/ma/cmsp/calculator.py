from programs.programs.calc import ProgramCalculator, Eligibility, MemberEligibility


class MaCmsp(ProgramCalculator):
    """
    Children's Medical Security Plan (CMSP) - Massachusetts

    Low-cost health coverage for children under age 19 who are Massachusetts
    residents, currently uninsured, and do not qualify for other MassHealth plans.
    CMSP helps pay for regular checkups, sick visits, prescriptions, and some
    specialty care.

    Eligibility:
    1. Child must be under age 19
    2. Currently uninsured (no health insurance of any kind)
    3. Not already enrolled in CMSP

    No income limit — any income level qualifies.
    No citizenship requirement — undocumented children qualify.

    Note: low_confidence = True because the screener cannot determine whether a
    child truly fails to qualify for MassHealth Standard. We only check current
    insurance enrollment status. If MassHealth also appears in results, the user
    should apply for MassHealth first.

    Value: $239/month per eligible uninsured child (average MassHealth child
    coverage value estimate).

    Warning: There may be a waiting list to receive CMSP coverage.

    Sources:
    - https://www.mass.gov/childrens-medical-security-plan
    - https://www.mahealthconnector.org/
    """

    member_amount = 239  # $239/month per eligible uninsured child
    low_confidence = True
    dependencies = ["age", "health_insurance"]

    def household_eligible(self, e: Eligibility) -> None:
        # Exclude households already enrolled in CMSP
        e.condition(not self.screen.has_benefit("ma_cmsp"))

    def member_eligible(self, e: MemberEligibility) -> None:
        member = e.member

        # Child must be under age 19
        e.condition(member.age < 19)

        # Child must be currently uninsured
        e.condition(member.insurance.none)

"""Head Start Preschool — MFB federal base."""

from datetime import date
from typing import ClassVar

from programs.framework.base import MemberEligibility
from programs.programs.cross_white_label.head_start.eligibility import HeadStartEligibility
from screener.models import HouseholdMember


class MfbHeadStart(HeadStartEligibility, abstract=True):
    """
    Federal Head Start Preschool (45 CFR 1302.12), computed in our own code. It sits beside
    the PolicyEngine ``HeadStart`` in ``base.py``, which the states not yet moved still use.

    A child is eligible when they are of preschool age and one of these holds:

    - family income, less housing costs above 30% of it, is at or below the poverty line
    - the family receives or is eligible for TANF, SSI or SNAP
    - the child is in foster care

    Homelessness, the Migrant/Seasonal and Tribal routes, and the small-community rule have
    no screener field and are not evaluated. The 35% (under 130% FPL) and 10% over-income
    allowances are enrollment slots, not eligibility, so they are left out too. The income,
    public assistance and foster care rules are ``HeadStartEligibility``'s, shared with
    Early Head Start.

    Each state sets:

    - ``school_eligibility_cutoff_date``: (month, day) a child must turn 3 by to count as 3
    - ``compulsory_school_age``: the age a child must be under
    - ``weekly_price`` and ``program_weeks``: the value is their product per eligible child
    - ``gates_on_any``: its own SNAP/TANF/SSI program codes, read tolerantly through
      ``any_program_eligible``. Leave it empty where the state has none.
    """

    min_age = 3

    school_eligibility_cutoff_date: ClassVar[tuple[int, int]]
    compulsory_school_age: ClassVar[int]
    weekly_price: ClassVar[float]
    program_weeks: ClassVar[int]

    def member_eligible(self, e: MemberEligibility) -> None:
        member = e.member
        age = member.calc_age()
        if age is None:
            e.condition(False)
            return

        e.condition(self._is_three_by_cutoff(member, age) and age < self.compulsory_school_age)

    def _is_three_by_cutoff(self, member: HouseholdMember, age: int) -> bool:
        """
        3 today, or 3 on the next school cutoff date. Birth is dated to the first of the
        month, since the screener collects no day of birth.
        """
        if age >= self.min_age:
            return True

        if member.birth_year_month is None:
            return False

        return HouseholdMember.age_from_date(member.birth_year_month, self._next_cutoff()) >= self.min_age

    def _next_cutoff(self) -> date:
        today = self.screen.get_reference_date()
        month, day = self.school_eligibility_cutoff_date
        cutoff = date(today.year, month, day)
        if cutoff < today:
            cutoff = date(today.year + 1, month, day)

        return cutoff

    def member_value(self, member: HouseholdMember) -> int:
        return round(self.weekly_price * self.program_weeks)

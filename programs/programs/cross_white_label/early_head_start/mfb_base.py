"""Early Head Start — MFB federal base."""

from decimal import ROUND_HALF_UP, Decimal
from typing import ClassVar

from programs.framework.base import MemberEligibility
from programs.programs.cross_white_label.head_start.eligibility import HeadStartEligibility
from screener.models import HouseholdMember


class MfbEarlyHeadStart(HeadStartEligibility, abstract=True):
    """
    Federal Early Head Start (45 CFR 1302.12), computed in our own code. It sits beside the
    PolicyEngine ``EarlyHeadStart`` in ``base.py``, which the states not yet moved still use.

    A child under 3, or a pregnant woman, is eligible when one of these holds:

    - family income, less housing costs above 30% of it, is at or below the poverty line
    - the family receives or is eligible for TANF, SSI or SNAP
    - the child (not a pregnant woman) is in foster care

    Those three are ``HeadStartEligibility``'s, shared with Head Start Preschool. Age is
    judged by birth month, since the screener collects no day of birth, so a child counts as
    3 from the first of their birth month. Homelessness, the Migrant/Seasonal and Tribal
    routes, and the small-community rule have no screener field and are not evaluated. The
    35% (under 130% FPL) allowance is an enrollment slot, not eligibility, so it is left out.

    The value prices each enrollee at the state's weekly rate for full-time licensed center
    care at their age, over the weeks the program's 1,380 annual hours make. A pregnant
    woman is valued as one infant slot. Each value is rounded half-up to whole dollars.

    Each state sets:

    - ``weekly_prices``: ``(first month of age, weekly price)`` per rate band, youngest
      first; a state with one rate lists one band starting at 0
    - ``program_weeks``: weeks in the program year
    - ``gates_on_any``: its own SNAP/TANF/SSI program codes, or empty where it has none

    The spec is ``programs/cross_white_label/early_head_start/base/early_head_start_base_spec.md``
    in program-ops.
    """

    max_age = 3

    weekly_prices: ClassVar[tuple[tuple[int, Decimal], ...]]
    program_weeks: ClassVar[int]

    dependencies = [*HeadStartEligibility.dependencies, "pregnant"]

    def member_eligible(self, e: MemberEligibility) -> None:
        member = e.member
        e.condition(self._is_under_three(member) or member.pregnant is True)

    def _is_under_three(self, member: HouseholdMember) -> bool:
        age = member.calc_age()
        return age is not None and age < self.max_age

    def _in_foster_care(self, member: HouseholdMember) -> bool:
        """The foster care route is the child's alone, so it never reaches a pregnant woman."""
        return super()._in_foster_care(member) and self._is_under_three(member)

    def member_value(self, member: HouseholdMember) -> int:
        weekly_price = self._weekly_price(self._age_in_months(member) if self._is_under_three(member) else 0)
        annual = weekly_price * self.program_weeks

        return int(annual.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    def _weekly_price(self, months: int) -> Decimal:
        """The price of the last band starting at or below ``months``."""
        price = self.weekly_prices[0][1]
        for first_month, band_price in self.weekly_prices:
            if months >= first_month:
                price = band_price

        return price

    def _age_in_months(self, member: HouseholdMember) -> int:
        """
        Whole months since the birth month, counting the birth month as month 0. A member
        with no birth month falls back to the stored age at the start of that year of life.
        """
        birth_year_month = member.birth_year_month
        if birth_year_month is None:
            return (member.calc_age() or 0) * 12

        today = self.screen.get_reference_date()
        return (today.year - birth_year_month.year) * 12 + today.month - birth_year_month.month

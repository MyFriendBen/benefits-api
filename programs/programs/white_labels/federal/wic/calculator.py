from decimal import ROUND_HALF_UP, Decimal
from functools import cached_property
from typing import Iterable

import programs.framework.eligibility_messages as messages
from programs.framework.base import Eligibility, MemberEligibility, ProgramCalculator
from screener.models import HouseholdMember

#: FNS's FY 2025 average monthly food cost per participant, which FNS states is the monthly
#: benefit (spec section 7).
MONTHLY_VALUE = Decimal("64.89")

#: Insurance types that mean Medicaid. MA's screener offers only MassHealth, which also covers
#: CHIP; `ma_mass_health` reads it, so an MA household on CHIP passes as Medicaid.
MEDICAID_TYPES = ("medicaid", "ma_mass_health")


class FederalWic(ProgramCalculator):
    """
    Federal WIC, valued per participant. Rules and figures: program-ops
    `programs/white_labels/federal/wic/federal_wic_spec.md` (sections 3 to 8).

    A member qualifies as pregnant, an infant (under 1) or a child (1 to 4), and is income
    eligible when the household is at or under 185% of the poverty guideline, counting one
    more person per pregnant member, or adjunctively: the household reports SNAP or TANF,
    the member is on Medicaid, or a pregnant member or infant in the household is.

    Deviations: postpartum and breastfeeding women are never counted, since the screener
    can't tell either; the 48-state limit applies everywhere, since no white label serves
    Alaska or Hawaii; nutritional risk is assumed. Residency is the white label's and
    citizenship is the program's `legal_status_required`.
    """

    program_code = "federal_wic"

    fpl_percent = 185
    max_infant_age = 1
    max_child_age = 5
    member_amount = int((MONTHLY_VALUE * 12).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    # Not `pregnant`: the Get Ahead apps never send it, and a missing answer already reads as
    # not pregnant (`is True`), so requiring it would drop WIC from every one of their screens.
    dependencies = ["age", "household_size", "income_amount", "income_frequency"]

    def member_eligible(self, e: MemberEligibility) -> None:
        member = e.member
        e.condition(self._in_category(member))
        e.condition(self.income_eligible or self._adjunctive(member))

    def household_eligible(self, e: Eligibility) -> None:
        adjunctive_members = [m for m in e.eligible_members if m.eligible and self._on_medicaid_route(m.member)]
        if self.household_adjunctive or adjunctive_members:
            e.condition(True, messages.presumed_eligibility())
            return

        e.condition(self.income_eligible, messages.income(self.gross_income, self.income_limit))

    # Categories

    def _in_category(self, member: HouseholdMember) -> bool:
        if member.pregnant is True:
            return True

        age = member.calc_age()
        return age is not None and age < self.max_child_age

    # Income

    @cached_property
    def family_size(self) -> int:
        """`household_size` plus one unborn child per pregnant member."""
        pregnant = sum(1 for member in self._members if member.pregnant is True)
        return self.screen.household_size + pregnant

    @cached_property
    def income_limit(self) -> int:
        """185% of the poverty guideline, rounded up to the dollar as the WIC tables are."""
        poverty_line = self.program.year.get_limit(self.family_size)
        return -(-poverty_line * self.fpl_percent // 100)

    @cached_property
    def gross_income(self) -> int:
        return int(self.screen.calc_gross_income("yearly", ["all"]))

    @cached_property
    def income_eligible(self) -> bool:
        return self.gross_income <= self.income_limit

    # Adjunctive eligibility

    @cached_property
    def household_adjunctive(self) -> bool:
        """SNAP or TANF reaches every member of the household."""
        return self.screen.has_base_benefit("snap") or self.screen.has_base_benefit("tanf")

    @cached_property
    def family_medicaid(self) -> bool:
        """A pregnant member or an infant on Medicaid makes the whole family adjunctive."""
        return any(
            self._has_medicaid(member) and (member.pregnant is True or self._is_infant(member))
            for member in self._members
        )

    def _adjunctive(self, member: HouseholdMember) -> bool:
        return self.household_adjunctive or self._on_medicaid_route(member)

    def _on_medicaid_route(self, member: HouseholdMember) -> bool:
        return self._has_medicaid(member) or self.family_medicaid

    def _has_medicaid(self, member: HouseholdMember) -> bool:
        return member.has_insurance_types(MEDICAID_TYPES)

    def _is_infant(self, member: HouseholdMember) -> bool:
        age = member.calc_age()
        return age is not None and age < self.max_infant_age

    @cached_property
    def _members(self) -> Iterable[HouseholdMember]:
        return list(self.screen.household_members.all())

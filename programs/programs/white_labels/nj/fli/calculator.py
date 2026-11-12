from typing import Optional

from programs.framework.base import MemberEligibility
from programs.programs.white_labels.nj.paid_leave import NjPaidLeave
from screener.models import HouseholdMember


class NjFli(NjPaidLeave):
    """
    New Jersey Family Leave Insurance (FLI): partial pay for a worker taking leave to bond with
    a new child or care for a seriously ill family member. Someone already on unemployment gets
    the same leave as Family Leave During Unemployment (FLDU), capped at the FLDU weekly
    maximum.

    A member qualifies on either route (`NjPaidLeave`) with no SSDI income, when they are
    bonding with a household child under 1 or caring for another household member with a
    disability. Bonding reads relationships to the head: the head, spouse or domestic partner
    with a child, stepchild or foster child under 1, or the head's child with a grandchild
    under 1. The value is the weekly rate times the 2024 mean days paid per claim: 69 for
    bonding, 45 for family care.

    Spec: program-ops `programs/white_labels/nj/fli/nj_fli_spec.md`. Data gaps (spec §5): the
    employer's coverage, when work stopped, base-year wage history, adoption and foster
    placement dates, relationships other than to the head, a serious health condition, family
    outside the household, safe leave, concurrent benefits, and SSDI timing.
    """

    program_code = "nj_fli"

    bonding_avg_days = 69
    care_avg_days = 45

    bonding_parents = ("headOfHousehold", "spouse", "domesticPartner")
    bonding_children = ("child", "stepChild", "fosterChild")

    dependencies = [
        "age",
        "relationship",
        "disabled",
        "visually_impaired",
        "long_term_disability",
        "income_type",
        "income_amount",
        "income_frequency",
    ]

    def member_eligible(self, e: MemberEligibility) -> None:
        super().member_eligible(e)
        member = e.member

        e.condition(self.is_bonding(member) or self.is_caring(member))

    def member_value(self, member: HouseholdMember) -> int:
        days = self.bonding_avg_days if self.is_bonding(member) else self.care_avg_days
        return self.lump_sum(self.weekly_rate(member), days)

    def unemployment_max_weekly_rate(self) -> Optional[int]:
        return self.figures.fldu_max_weekly_rate

    def is_bonding(self, member: HouseholdMember) -> bool:
        if member.relationship in self.bonding_parents:
            return self._has_infant(self.bonding_children)
        if member.relationship == "child":
            return self._has_infant(("grandChild",))
        return False

    def is_caring(self, member: HouseholdMember) -> bool:
        return any(m.has_disability() for m in self._members() if m.id != member.id)

    def _has_infant(self, relationships: tuple[str, ...]) -> bool:
        return any(m.relationship in relationships and m.calc_age() == 0 for m in self._members())

    def _members(self) -> list[HouseholdMember]:
        return list(self.screen.household_members.all())

from typing import ClassVar

from programs.framework.base import MemberEligibility, ProgramCalculator
from screener.models import HouseholdMember

# A $90 standard work exemption applies once per earning member, then the remaining
# earnings are subject to a three-fourths disregard, so only a quarter of
# post-exemption earnings counts. See spec.md Benefit Value for the source.
WORK_EXEMPTION = 90
EARNED_DISREGARD = 0.75
COUNTABLE_EARNED_FRACTION = 1 - EARNED_DISREGARD

# The ORR eligibility period is 8 months for eligibility dates on or after 2026-01-01.
# RCA is paid monthly but MFB stores one lump-sum figure, so the stored value is the
# monthly award for the full period a household can still receive. The screener
# collects no ORR eligibility date, so this assumes the full period remains — see
# spec.md's eligibility-period data gap and Benefit Value for the source.
ELIGIBILITY_PERIOD_MONTHS = 8

# The RCA Maximum Payment, tabulated for sizes 1-5 only. Sizes above 5 add $113 per
# additional member. See spec.md Benefit Value for the source.
RCA_MAX_PAYMENT = {1: 537, 2: 726, 3: 915, 4: 1104, 5: 1217}
ADDITIONAL_MEMBER_AMOUNT = 113
LARGEST_TABULATED_SIZE = max(RCA_MAX_PAYMENT)

# An adult child (18+) of a parent in the case forms a separate, single-member RCA
# case. These four relationship values are MFB's mapping onto the household's
# `child`-type relationships, not an ORR enumeration — see spec.md's case-splitting
# rule.
CHILD_RELATIONSHIPS = frozenset({"child", "stepChild", "fosterChild", "grandChild"})

# A proxy for cash grants MFB cannot otherwise identify (e.g. the Program of Initial
# Resettlement) — excluded from unearned income, over-inclusively. See spec.md's
# income-source data gap.
EXCLUDED_UNEARNED_TYPES = ["cashAssistanceOther", "gifts"]

# The income options that carry a member's own reported SSI and TANF amounts — see
# spec.md's SSI/TANF removal rule. Note the `sSI` casing.
SSI_INCOME_TYPE = "sSI"
TANF_INCOME_TYPE = "cashAssistance"


def rca_max_payment(case_size: int) -> float:
    """The Missouri RCA Maximum Payment for a case of this size — both the income
    eligibility standard and the benefit base. Never subscript `RCA_MAX_PAYMENT`
    directly: it holds no entry above size 5."""
    if case_size in RCA_MAX_PAYMENT:
        return RCA_MAX_PAYMENT[case_size]

    return RCA_MAX_PAYMENT[LARGEST_TABULATED_SIZE] + ADDITIONAL_MEMBER_AMOUNT * (case_size - LARGEST_TABULATED_SIZE)


def _removed_from_case(member: HouseholdMember) -> bool:
    """A member with a reported SSI or TANF (`cashAssistance`) payment is removed
    from their own RCA case, taking their income with them. Reported receipt only
    — never eligibility for either program, and never a household-level TANF
    report."""
    reports_ssi = member.calc_gross_income("yearly", [SSI_INCOME_TYPE]) > 0
    reports_tanf = member.calc_gross_income("yearly", [TANF_INCOME_TYPE]) > 0
    return reports_ssi or reports_tanf


def _net_countable_income(member: HouseholdMember) -> float:
    """Benefit Value: `max(earned - 90, 0) * 0.25` per earning member, plus unearned
    income in full except the `EXCLUDED_UNEARNED_TYPES` exclusions. No disregard
    applies to unearned income. `calc_gross_income` already normalises non-monthly
    frequencies and casts to `float`, which is load-bearing for the cent-exact
    values spec.md commits to."""
    earned = member.calc_gross_income("monthly", ["earned"])
    countable_earned = max(earned - WORK_EXEMPTION, 0) * COUNTABLE_EARNED_FRACTION

    unearned = member.calc_gross_income("monthly", ["unearned"], exclude=EXCLUDED_UNEARNED_TYPES)

    return countable_earned + unearned


def _splits_into_own_case(member: HouseholdMember) -> bool:
    """An adult child (18+) forms their own single-member case, separate from the
    rest of the household. `calc_age()` returning `None` fails open — an
    unknown-age member stays in the primary case."""
    age = member.calc_age()
    return age is not None and age >= 18 and member.relationship in CHILD_RELATIONSHIPS


class MoRca(ProgramCalculator):
    """
    Missouri Refugee Cash Assistance (RCA) — monthly cash for refugees and other
    ORR-eligible newcomers, administered by the Missouri Office of Refugee
    Administration (MO-ORA) under the public/private model.

    Three rules are evaluated, all at case rather than household scope:

    - The household is first resolved into RCA cases: an adult child (18+) of a
      parent in the case forms their own single-member case, and everyone else
      stays in one shared case. This determines both the case size used for the
      income standard and how income is pooled.
    - Each case then loses any member with a reported SSI or TANF
      (`cashAssistance`) payment — reported receipt only, never eligibility for
      either program, and never a household-level TANF report.
    - Each case's remaining net countable income is compared, strictly, against
      the Missouri RCA Maximum Payment for its size (`rca_max_payment`).

    Household eligibility follows automatically from member marks: the base
    `ProgramCalculator.eligible()` requires at least one eligible member, which here
    is equivalent to at least one payable case, so `household_eligible` needs no
    override. The award itself lives entirely in `household_value` — `member_value`
    returns 0 — since a per-member award would multiply it by case size.

    ORR-eligible immigration status is carried by the program row's
    `legal_status_required` and is not evaluated here. The SSI-pending pathway
    needs no implementation: it is satisfied by construction, since the SSI/TANF
    removal rule above fires only on a *reported* SSI amount. The ORR eligibility
    window, the higher-education student exclusion, and TANF assistance-unit
    membership are data gaps handled inclusively — see spec.md.
    """

    program_code = "mo_rca"

    dependencies: ClassVar[list[str]] = ["income_type", "income_amount", "income_frequency"]

    def _case_members(self, member: HouseholdMember) -> list[HouseholdMember]:
        """The RCA case `member` belongs to, before the SSI/TANF removal rule takes
        anyone out — an adult child's own single-member case, or everyone else who
        doesn't split. Computed from `member`, not cached, so there is nothing to
        keep in sync and no reverse lookup from a prebuilt group back to a member."""
        if _splits_into_own_case(member):
            return [member]

        return [m for m in self.screen.household_members.all() if not _splits_into_own_case(m)]

    def _case_award(self, members: list[HouseholdMember]) -> float:
        """Monthly award for a case, or 0 if net income doesn't clear the standard
        (strict — equal to the standard is not eligible) or nobody remains in it."""
        remaining = [m for m in members if not _removed_from_case(m)]
        if not remaining:
            return 0

        net_income = sum(_net_countable_income(m) for m in remaining)
        standard = rca_max_payment(len(remaining))
        return standard - net_income if net_income < standard else 0

    def member_eligible(self, e: MemberEligibility):
        member = e.member
        if _removed_from_case(member):
            e.condition(False)
            return

        e.condition(self._case_award(self._case_members(member)) > 0)

    def household_value(self) -> float:
        """The sum, across payable cases, of the monthly award times the number of
        months of RCA eligibility a household can still receive (assumes the full
        period remains — see `ELIGIBILITY_PERIOD_MONTHS`). Committed to the cent —
        no intermediate rounding. Cases are deduped by member-id set, since every
        member of a shared case resolves to the same case independently."""
        seen_cases = set()
        total = 0.0

        for member in self.screen.household_members.all():
            members = self._case_members(member)
            case_key = frozenset(m.id for m in members)
            if case_key in seen_cases:
                continue

            seen_cases.add(case_key)
            total += self._case_award(members) * ELIGIBILITY_PERIOD_MONTHS

        return total

    def member_value(self, member: HouseholdMember) -> int:
        """The award is a per-case figure, not a per-member one; it is returned
        entirely from `household_value` so it is not counted once per case member."""
        return 0

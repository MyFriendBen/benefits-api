from typing import ClassVar, Optional

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
    report (spec.md's SSI-pending pathway; see Scenario 19)."""
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


class _Case:
    """One RCA assistance unit: `members` is the case as split by the adult-child
    rule, before the SSI/TANF removal rule takes out anyone reporting SSI or TANF.
    `remaining` — what is left after that removal — is what the case size, income,
    and standard are computed against."""

    def __init__(self, members: list[HouseholdMember]):
        self.members = members
        self.remaining = [member for member in members if not _removed_from_case(member)]
        self.size = len(self.remaining)
        self.net_income = sum(_net_countable_income(member) for member in self.remaining)
        self.standard = rca_max_payment(self.size) if self.size else 0
        # Strict: net income equal to the standard is ineligible — spec.md's income
        # comparison is "under", not "at or under".
        self.eligible = self.size > 0 and self.net_income < self.standard

    def contains(self, member: HouseholdMember) -> bool:
        """Matched by `id`, not Python identity: `member_eligible` receives instances
        from the framework's own `household_members.all()` call, a separate query from
        the one that built this case."""
        return any(case_member.id == member.id for case_member in self.members)


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

    def _cases(self) -> list[_Case]:
        if not hasattr(self, "_cases_cache"):
            primary_case_members = []
            split_cases = []

            for member in self.screen.household_members.all():
                if _splits_into_own_case(member):
                    split_cases.append(_Case([member]))
                else:
                    primary_case_members.append(member)

            cases = split_cases
            if primary_case_members:
                cases = [_Case(primary_case_members)] + split_cases

            self._cases_cache = cases

        return self._cases_cache

    def _case_for_member(self, member: HouseholdMember) -> Optional[_Case]:
        for case in self._cases():
            if case.contains(member):
                return case

        return None

    def member_eligible(self, e: MemberEligibility):
        case = self._case_for_member(e.member)
        e.condition(case is not None and case.eligible and not _removed_from_case(e.member))

    def household_value(self) -> float:
        """The sum, across payable cases, of the monthly award times the number of
        months of RCA eligibility a household can still receive (assumes the full
        period remains — see `ELIGIBILITY_PERIOD_MONTHS`). Committed to the cent —
        no intermediate rounding."""
        return sum(
            (case.standard - case.net_income) * ELIGIBILITY_PERIOD_MONTHS for case in self._cases() if case.eligible
        )

    def member_value(self, member: HouseholdMember) -> int:
        """The award is a per-case figure, not a per-member one; it is returned
        entirely from `household_value` so it is not counted once per case member."""
        return 0

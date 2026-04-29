from typing import ClassVar, Optional

from screener.models import HouseholdMember
from programs.programs.calc import Eligibility, MemberEligibility, ProgramCalculator


class WaSsi(ProgramCalculator):
    """
    Washington Supplemental Security Income (SSI).

    Federal cash assistance for people who are aged 65+, blind, or disabled
    with limited income and resources. Washington does not pay a state
    supplement for most recipients, so the screener uses the federal benefit
    rate directly (2026 SSA FBR: $994 individual / $1,491 couple).

    The calculator implements a screener-side approximation of SSA's
    FBR-minus-countable-income formula, including the $20 general + $65 earned
    + 1/2 remaining income exclusion stack and a simplified spousal /
    parental deeming model. Final adjudication (medical / vocational
    disability review, in-kind support and maintenance reductions, immigration
    sub-status verification) happens at SSA at the application stage.

    See `programs/programs/wa/ssi/spec.md` for the full eligibility criteria,
    PolicyEngine variable mapping, and the 15 reference test scenarios.
    """

    # 2026 SSA Federal Benefit Rates (post-COLA, monthly).
    fbr_individual_monthly = 994
    fbr_couple_monthly = 1_491

    # Resource limits — unchanged since 1989 (20 CFR § 416.1205).
    resource_limit_individual = 2_000
    resource_limit_couple = 3_000

    # Monthly income exclusions (20 CFR §§ 416.1112, 416.1124).
    general_income_exclusion_monthly = 20
    earned_income_exclusion_monthly = 65
    earned_income_share = 0.5

    # 2026 SGA thresholds (20 CFR §§ 416.971-416.974).
    sga_threshold_non_blind_monthly = 1_690
    sga_threshold_blind_monthly = 2_830

    aged_threshold = 65
    adult_age = 18

    dependencies: ClassVar[list[str]] = [
        "age",
        "income_amount",
        "income_frequency",
        "household_assets",
        "relationship",
        "household_size",
    ]

    def member_eligible(self, e: MemberEligibility) -> None:
        """
        Per-member categorical entry — aged 65+ OR has a disability/blindness
        signal. Adult non-blind disability claimants are also subject to the
        SGA earned-income cutoff.
        """
        member = e.member

        is_aged = member.age is not None and member.age >= self.aged_threshold
        is_blind = bool(member.visually_impaired)
        is_disabled = bool(member.disabled or member.long_term_disability or is_blind)
        e.condition(is_aged or is_disabled)

        if not e.eligible:
            return

        if not is_aged and not is_blind and member.age is not None and member.age >= self.adult_age:
            monthly_earned = member.calc_gross_income("monthly", ["earned"])
            e.condition(monthly_earned <= self.sga_threshold_non_blind_monthly)

    def household_eligible(self, e: Eligibility) -> None:
        """
        Household-level checks: resource limit, duplicate-enrollment filter,
        and the FBR-minus-countable-income test (with spousal / parental
        deeming when applicable).
        """
        if not e.eligible:
            return

        if self.screen.has_benefit("wa_ssi"):
            e.eligible = False
            return

        eligible_members = [me.member for me in e.eligible_members if me.eligible]
        e.condition(self.screen.household_assets <= self._resource_limit(eligible_members))
        if not e.eligible:
            return

        monthly_ssi = self._compute_monthly_ssi(eligible_members)
        if monthly_ssi <= 0:
            e.eligible = False
            return

        # Stash for member_value(): split the household monthly amount across
        # eligible members and annualize per the screener's `* 12` convention.
        self._monthly_ssi = monthly_ssi
        self._eligible_count = len(eligible_members)

    def member_value(self, member: HouseholdMember) -> int:
        if not getattr(self, "_eligible_count", 0):
            return 0
        per_member_monthly = self._monthly_ssi / self._eligible_count
        return int(per_member_monthly * 12)

    # ---------- internal helpers ----------

    def _get_spouse(self, head: HouseholdMember) -> Optional[HouseholdMember]:
        for member in self.screen.household_members.all():
            if member.id == head.id:
                continue
            if member.relationship in ("spouse", "domesticPartner"):
                return member
        return None

    def _resource_limit(self, eligible_members: list[HouseholdMember]) -> int:
        """
        Couple resource limit applies when both head and spouse are SSI-eligible
        or when an eligible head lives with an ineligible spouse (the
        spouse-deeming case under 20 CFR § 416.1205). All other configurations
        — including a child SSI applicant living with parents — use the
        individual limit.
        """
        head = self.screen.get_head()
        spouse = self._get_spouse(head)
        eligible_ids = {m.id for m in eligible_members}

        if spouse is not None and head.id in eligible_ids:
            return self.resource_limit_couple
        return self.resource_limit_individual

    def _compute_monthly_ssi(self, eligible_members: list[HouseholdMember]) -> float:
        """
        Resolve the household configuration (single, eligible couple, eligible
        head + ineligible spouse, child-only) and return the household's
        monthly SSI payment after exclusions and deeming.
        """
        if not eligible_members:
            return 0.0

        head = self.screen.get_head()
        spouse = self._get_spouse(head)
        eligible_ids = {m.id for m in eligible_members}

        head_eligible = head.id in eligible_ids
        spouse_eligible = spouse is not None and spouse.id in eligible_ids

        if head_eligible and spouse_eligible:
            return self._couple_ssi(head, spouse)

        if head_eligible and spouse is not None and not spouse_eligible:
            return self._spousal_deeming_ssi(head, spouse)

        if head_eligible:
            return self._individual_ssi(head)

        # Child-only applicant case: head and spouse are ineligible "parents",
        # apply parental deeming to the eligible child(ren).
        all_minors = all(m.age is not None and m.age < self.adult_age for m in eligible_members)
        if all_minors:
            return self._parental_deeming_ssi(eligible_members[0])

        # Fallback — eligible non-head adult (rare). Treat as individual.
        return self._individual_ssi(eligible_members[0])

    def _individual_ssi(self, member: HouseholdMember) -> float:
        countable = self._countable_income(
            member.calc_gross_income("monthly", ["earned"]),
            member.calc_gross_income("monthly", ["unearned"]),
        )
        return max(0.0, self.fbr_individual_monthly - countable)

    def _couple_ssi(self, head: HouseholdMember, spouse: HouseholdMember) -> float:
        earned = head.calc_gross_income("monthly", ["earned"]) + spouse.calc_gross_income("monthly", ["earned"])
        unearned = head.calc_gross_income("monthly", ["unearned"]) + spouse.calc_gross_income("monthly", ["unearned"])
        countable = self._countable_income(earned, unearned)
        return max(0.0, self.fbr_couple_monthly - countable)

    def _spousal_deeming_ssi(self, eligible_head: HouseholdMember, ineligible_spouse: HouseholdMember) -> float:
        """
        SSA spousal deeming (simplified — see 20 CFR §§ 416.1160, 416.1163):
        if the ineligible spouse's deemed-countable income exceeds the FBR
        differential ($497/mo), the benefit base switches to the couple FBR
        and the spouses' combined countable income is subtracted.
        """
        spouse_deemed = self._countable_income(
            ineligible_spouse.calc_gross_income("monthly", ["earned"]),
            ineligible_spouse.calc_gross_income("monthly", ["unearned"]),
        )
        fbr_differential = self.fbr_couple_monthly - self.fbr_individual_monthly

        if spouse_deemed > fbr_differential:
            combined = self._countable_income(
                eligible_head.calc_gross_income("monthly", ["earned"])
                + ineligible_spouse.calc_gross_income("monthly", ["earned"]),
                eligible_head.calc_gross_income("monthly", ["unearned"])
                + ineligible_spouse.calc_gross_income("monthly", ["unearned"]),
            )
            return max(0.0, self.fbr_couple_monthly - combined)

        return self._individual_ssi(eligible_head)

    def _parental_deeming_ssi(self, child: HouseholdMember) -> float:
        """
        Parental deeming for a child SSI applicant (20 CFR § 416.1165):
        parents' countable income, less an allocation of (couple_FBR / 2) per
        ineligible parent, is deemed to the child. Anything left over reduces
        the child's individual FBR.
        """
        head = self.screen.get_head()
        parents = [head]
        spouse = self._get_spouse(head)
        if spouse is not None:
            parents.append(spouse)

        parents_earned = sum(p.calc_gross_income("monthly", ["earned"]) for p in parents)
        parents_unearned = sum(p.calc_gross_income("monthly", ["unearned"]) for p in parents)
        parents_countable = self._countable_income(parents_earned, parents_unearned)

        parent_allocation = (self.fbr_couple_monthly / 2) * len(parents)
        net_deemed = max(0.0, parents_countable - parent_allocation)

        child_countable = self._countable_income(
            child.calc_gross_income("monthly", ["earned"]),
            child.calc_gross_income("monthly", ["unearned"]),
        )
        return max(0.0, self.fbr_individual_monthly - net_deemed - child_countable)

    def _countable_income(self, earned: float, unearned: float) -> float:
        """
        Apply SSA's monthly income exclusions in order:
          1. $20 general — applied to unearned first; remainder to earned
          2. $65 earned flat
          3. 1/2 of the remaining earned income is countable
        """
        general = self.general_income_exclusion_monthly
        if unearned >= general:
            unearned -= general
        else:
            remainder = general - unearned
            unearned = 0
            earned = max(0.0, earned - remainder)

        earned = max(0.0, earned - self.earned_income_exclusion_monthly)
        earned *= self.earned_income_share

        return earned + unearned

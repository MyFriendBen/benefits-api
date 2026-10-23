from dataclasses import dataclass
from functools import cached_property
from typing import Iterable, Optional

from sentry_sdk import capture_message

from programs.framework.base import Eligibility, MemberEligibility, ProgramCalculator
from screener.models import HouseholdMember


@dataclass(frozen=True)
class SsiYear:
    """One benefit year's figures. The student exclusion's yearly cap is not modelled: earlier
    months' earnings are unknown."""

    individual_fbr: int
    couple_fbr: int
    student_exclusion: int
    individual_resource_limit: int
    couple_resource_limit: int
    general_exclusion: int
    earned_exclusion: int
    #: The infrequent-income exclusion, applied only as a margin for someone otherwise just over
    #: the limit (spec `infrequent_income_exclusion`).
    infrequent_earned_margin: int
    infrequent_unearned_margin: int

    @property
    def ineligible_spouse_allowance(self) -> int:
        return self.couple_fbr - self.individual_fbr

    def resource_limit(self, people: int) -> int:
        return self.couple_resource_limit if people >= 2 else self.individual_resource_limit

    def fbr(self, people: int) -> int:
        return self.couple_fbr if people >= 2 else self.individual_fbr


# Spec section 7 (rates), 4.8 (income exclusions) and 4.9 (resource limits), by benefit year.
SSI_YEARS: dict[int, SsiYear] = {
    2026: SsiYear(
        individual_fbr=994,
        couple_fbr=1_491,
        student_exclusion=2_410,
        individual_resource_limit=2_000,
        couple_resource_limit=3_000,
        general_exclusion=20,
        earned_exclusion=65,
        infrequent_earned_margin=30,
        infrequent_unearned_margin=60,
    ),
}

SSI_INCOME_TYPE = "sSI"
TANF_INCOME_TYPE = "cashAssistance"
OTHER_CASH_INCOME_TYPE = "cashAssistanceOther"


@dataclass(frozen=True)
class MemberIncome:
    """A member's monthly income split the way SSI counts it; `sSI` itself is never income."""

    earned: float
    #: Unearned income other than SSI, `cashAssistance` (TANF) and `cashAssistanceOther`.
    unearned: float
    tanf: float
    other_cash: float
    earned_after_student_exclusion: float


@dataclass(frozen=True)
class CountingRules:
    """
    Which of the spec's inclusive approximations a countable-income pass applies. The plain
    rules come first; each relaxation is tried only when the stricter pass fails, so a
    household that qualifies outright is valued on its actual income and one that needs a
    relaxation gets an upper-bound payment.
    """

    infrequent_margin: bool = False
    drop_other_cash: bool = False
    #: Leave out the earnings of members whose work expenses could offset them.
    drop_earnings: bool = False


@dataclass(frozen=True)
class Verdict:
    eligible: bool
    #: The federal monthly payment; 0 when ineligible.
    monthly_payment: float = 0


class FederalSsi(ProgramCalculator):
    """
    Federal Supplemental Security Income, the federal payment before any State supplement,
    per member. Rules and figures: program-ops
    `programs/white_labels/federal/ssi/federal_ssi_spec.md` (sections 3 to 7).

    Screener mapping: blindness is `visually_impaired`; disability is `disabled` or
    `long_term_disability`; the head and the member recorded as `spouse` form the couple
    (a `domesticPartner` does not); a `child` under 18 is deemed to from the head and the
    head's spouse, a `stepChild` only while the head's spouse is present; everyone else is a
    unit of one. A parent who reports `sSI` income is treated as an SSI recipient. Condition
    flags left `None` read as no. Citizenship is the program's `legal_status_required`.

    Deviations: the work test is passed on an earnings-only failure, since the work expenses
    that would lower earnings are not collected; relaxations (infrequent-income margin, other
    cash assistance left out, a blind or disabled member's earnings left out) are tried in
    that order and the first that passes sets the payment, an upper bound; allocations for
    ineligible children are not modelled; the one household asset total never rules a member
    out when anyone outside their unit lives there. Residence, presence, institution stays,
    resource transfers, in-kind support and sponsor deeming are not evaluated.
    """

    program_code = "federal_ssi"

    aged_min_age = 65
    adult_age = 18
    student_exclusion_max_age = 21

    dependencies = ["age", "relationship", "household_assets", "income_type", "income_amount", "income_frequency"]

    def member_eligible(self, e: MemberEligibility) -> None:
        e.condition(self._verdict(e.member).eligible)

    def value(self, e: Eligibility) -> None:
        if not e.eligible:
            return

        for member_eligibility in e.eligible_members:
            if member_eligibility.eligible:
                monthly = self._verdict(member_eligibility.member).monthly_payment
                member_eligibility.value = round(monthly * 12)

    # Parameters

    @cached_property
    def benefit_year(self) -> int:
        """The program's configured year, or the screening year when none is set."""
        if self.program.year is not None:
            return int(self.program.year.period)

        return self.screen.get_reference_date().year

    @cached_property
    def params(self) -> SsiYear:
        """The benefit year's figures; a year the table lacks uses the latest and reports to
        Sentry rather than raising, since an exception here fails every white label's results."""
        year = self.benefit_year
        if year in SSI_YEARS:
            return SSI_YEARS[year]

        latest = max(SSI_YEARS)
        capture_message(f"No federal SSI parameters for {year}; using {latest}.", level="error")
        return SSI_YEARS[latest]

    # Household structure

    @cached_property
    def members(self) -> list[HouseholdMember]:
        return list(self.screen.household_members.all())

    @cached_property
    def head(self) -> Optional[HouseholdMember]:
        return next((m for m in self.members if m.relationship == "headOfHousehold"), None)

    @cached_property
    def spouse(self) -> Optional[HouseholdMember]:
        return next((m for m in self.members if m.relationship == "spouse"), None)

    def _partner(self, member: HouseholdMember) -> Optional[HouseholdMember]:
        """The other half of the head-and-spouse pair, when `member` is one of them."""
        if member.relationship == "headOfHousehold":
            return self.spouse
        if member.relationship == "spouse":
            return self.head
        return None

    def _age(self, member: HouseholdMember) -> int:
        age = member.calc_age()
        return age if age is not None else 0

    def _is_child(self, member: HouseholdMember) -> bool:
        return self._age(member) < self.adult_age

    def _parents_of(self, child: HouseholdMember) -> list[HouseholdMember]:
        """The parents who deem to `child` (spec sections 4.8 and 4.9); other relationships have none."""
        if not self._is_child(child):
            return []

        if child.relationship == "child":
            return [p for p in (self.head, self.spouse) if p is not None]
        if child.relationship == "stepChild" and self.head is not None and self.spouse is not None:
            return [self.head, self.spouse]

        return []

    def _deeming_children(self, parents: list[HouseholdMember]) -> list[HouseholdMember]:
        """The qualifying children who share the income deemed from `parents`."""
        return [m for m in self.members if self._parents_of(m) == parents and self._categorically_eligible(m)]

    # Categorical eligibility

    def _is_blind(self, member: HouseholdMember) -> bool:
        return bool(member.visually_impaired)

    def _is_disabled(self, member: HouseholdMember) -> bool:
        return bool(member.disabled or member.long_term_disability)

    def _is_aged(self, member: HouseholdMember) -> bool:
        return self._age(member) >= self.aged_min_age

    def _categorically_eligible(self, member: HouseholdMember) -> bool:
        return self._is_aged(member) or self._is_blind(member) or self._is_disabled(member)

    def _reports_ssi(self, member: HouseholdMember) -> bool:
        return member.calc_gross_income("monthly", [SSI_INCOME_TYPE]) > 0

    def _earnings_can_be_left_out(self, member: HouseholdMember) -> bool:
        """Whether an earnings-only failure is passed (spec `impairment_related_work_expenses`,
        `blind_work_expenses`, `work_expense_exclusion_after_65`)."""
        if not (self._is_blind(member) or self._is_disabled(member)):
            return False

        return not self._is_aged(member) or self._reports_ssi(member)

    # Income

    def _income(self, member: HouseholdMember) -> MemberIncome:
        earned = member.calc_gross_income("monthly", ["earned"])
        unearned = member.calc_gross_income(
            "monthly", ["unearned"], exclude=[SSI_INCOME_TYPE, TANF_INCOME_TYPE, OTHER_CASH_INCOME_TYPE]
        )
        tanf = member.calc_gross_income("monthly", [TANF_INCOME_TYPE])
        other_cash = member.calc_gross_income("monthly", [OTHER_CASH_INCOME_TYPE])

        earned_after_student_exclusion = earned
        if self._gets_student_exclusion(member):
            earned_after_student_exclusion = max(earned - self.params.student_exclusion, 0)

        return MemberIncome(earned, unearned, tanf, other_cash, earned_after_student_exclusion)

    def _gets_student_exclusion(self, member: HouseholdMember) -> bool:
        """Spec `student_regular_attendance`: `student` is the only attendance proxy."""
        age = self._age(member)
        return self._is_child(member) or (age <= self.student_exclusion_max_age and bool(member.student))

    def _countable_income(
        self,
        members: list[HouseholdMember],
        rules: CountingRules,
        applicants: Iterable[HouseholdMember] = (),
        deemed_unearned: float = 0,
    ) -> float:
        """Spec section 4.8 `income_limit` for `members` as one unit. `rules.drop_earnings` reaches
        only `applicants`' earnings, never a deemor's; `deemed_unearned` is unearned to the unit."""
        params = self.params
        applicant_ids = {m.id for m in applicants}

        earned = 0.0
        unearned = deemed_unearned
        tanf = 0.0
        for member in members:
            income = self._income(member)
            if not (rules.drop_earnings and member.id in applicant_ids and self._earnings_can_be_left_out(member)):
                earned += income.earned_after_student_exclusion
            unearned += income.unearned
            if not rules.drop_other_cash:
                unearned += income.other_cash
            tanf += income.tanf

        if rules.infrequent_margin:
            earned = max(earned - params.infrequent_earned_margin, 0)
            margin = params.infrequent_unearned_margin
            from_unearned = min(margin, unearned)
            unearned -= from_unearned
            tanf = max(tanf - (margin - from_unearned), 0)

        general_exclusion_left = max(params.general_exclusion - unearned, 0)
        countable_unearned = max(unearned - params.general_exclusion, 0) + tanf
        countable_earned = max(earned - general_exclusion_left - params.earned_exclusion, 0) / 2

        return countable_unearned + countable_earned

    def _deemed_to_child(self, child: HouseholdMember, rules: CountingRules) -> float:
        """Spec section 4.8 parent deeming, shared equally among the qualifying children."""
        parents = self._parents_of(child)
        if not parents:
            return 0

        ssi_parents = [p for p in parents if self._reports_ssi(p)]
        if len(ssi_parents) == len(parents):
            return 0

        countable = self._countable_income(parents, CountingRules(drop_other_cash=rules.drop_other_cash))
        if ssi_parents:
            excess = max(countable - self.params.couple_fbr, 0)
        else:
            excess = max(countable - self.params.fbr(len(parents)), 0)

        return excess / max(len(self._deeming_children(parents)), 1)

    # Resources

    def _resources_allow(self, member: HouseholdMember, unit: list[HouseholdMember], limit: int) -> bool:
        """Spec section 4.9 `resource_limit`; anyone outside `unit` in the household disables it."""
        unit_ids = {m.id for m in unit}
        if any(m.id not in unit_ids for m in self.members):
            return True

        return float(self.screen.household_assets or 0) <= limit

    # Verdicts

    @cached_property
    def _verdicts(self) -> dict[int, Verdict]:
        return {}

    def _verdict(self, member: HouseholdMember) -> Verdict:
        if member.id not in self._verdicts:
            self._verdicts[member.id] = self._decide(member)

        return self._verdicts[member.id]

    def _decide(self, member: HouseholdMember) -> Verdict:
        if not self._categorically_eligible(member):
            return Verdict(False)

        if self._parents_of(member):
            return self._child_verdict(member)

        partner = self._partner(member)
        if partner is not None:
            if self._categorically_eligible(partner):
                return self._eligible_couple_verdict(member, partner)
            return self._ineligible_spouse_verdict(member, partner)

        return self._individual_verdict(member)

    def _rule_passes(
        self, applicants: list[HouseholdMember], deemors: Iterable[HouseholdMember] = ()
    ) -> list[CountingRules]:
        """The counting passes, strictest first; a relaxation is listed only when it could change the
        answer. Other cash assistance is left out wherever it is counted toward the unit, a deemor's
        included; only an applicant's own earnings can be left out."""
        has_other_cash = any(self._income(m).other_cash > 0 for m in [*applicants, *deemors])
        has_droppable_earnings = any(
            self._earnings_can_be_left_out(m) and self._income(m).earned_after_student_exclusion > 0 for m in applicants
        )

        passes = []
        for drop_earnings in (False, True):
            if drop_earnings and not has_droppable_earnings:
                continue
            for drop_other_cash in (False, True):
                if drop_other_cash and not has_other_cash:
                    continue
                for margin in (False, True):
                    passes.append(CountingRules(margin, drop_other_cash, drop_earnings))

        return passes

    def _individual_verdict(self, member: HouseholdMember) -> Verdict:
        if not self._resources_allow(member, [member], self.params.individual_resource_limit):
            return Verdict(False)

        for rules in self._rule_passes([member]):
            countable = self._countable_income([member], rules, applicants=[member])
            if countable < self.params.individual_fbr:
                return Verdict(True, self.params.individual_fbr - countable)

        return Verdict(False)

    def _eligible_couple_verdict(self, member: HouseholdMember, partner: HouseholdMember) -> Verdict:
        """Spec section 7, eligible couple."""
        couple = [member, partner]
        if not self._resources_allow(member, couple, self.params.couple_resource_limit):
            return Verdict(False)

        for rules in self._rule_passes(couple):
            countable = self._countable_income(couple, rules, applicants=couple)
            if countable < self.params.couple_fbr:
                return Verdict(True, (self.params.couple_fbr - countable) / 2)

        return Verdict(False)

    def _ineligible_spouse_verdict(self, member: HouseholdMember, partner: HouseholdMember) -> Verdict:
        """Spec section 4.8 spouse deeming and section 7, spouse who does not qualify."""
        params = self.params
        if not self._resources_allow(member, [member, partner], params.couple_resource_limit):
            return Verdict(False)

        partner_income = self._income(partner)
        spouse_income = partner_income.earned + partner_income.unearned + partner_income.tanf

        for rules in self._rule_passes([member], deemors=[partner]):
            own = self._countable_income([member], rules, applicants=[member])
            if own >= params.individual_fbr:
                continue
            payment = params.individual_fbr - own

            counted_spouse_income = spouse_income + (0 if rules.drop_other_cash else partner_income.other_cash)
            if counted_spouse_income > params.ineligible_spouse_allowance:
                couple = self._countable_income([member, partner], rules, applicants=[member])
                if couple >= params.couple_fbr:
                    continue
                payment = min(payment, params.couple_fbr - couple)

            return Verdict(True, payment)

        return Verdict(False)

    def _child_verdict(self, child: HouseholdMember) -> Verdict:
        """Spec sections 4.8 and 4.9, child with a parent in the household."""
        params = self.params
        parents = self._parents_of(child)
        counted_parents = [p for p in parents if not self._reports_ssi(p)]
        limit = params.individual_resource_limit + (
            params.resource_limit(len(counted_parents)) if counted_parents else 0
        )
        if not self._resources_allow(child, [child, *counted_parents], limit):
            return Verdict(False)

        for rules in self._rule_passes([child], deemors=parents):
            deemed = self._deemed_to_child(child, rules)
            countable = self._countable_income([child], rules, applicants=[child], deemed_unearned=deemed)
            if countable < params.individual_fbr:
                return Verdict(True, params.individual_fbr - countable)

        return Verdict(False)

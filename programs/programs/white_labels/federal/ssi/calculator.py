from dataclasses import dataclass
from functools import cached_property
from typing import Iterable, Optional

from sentry_sdk import capture_message

from programs.framework.base import Eligibility, MemberEligibility, ProgramCalculator
from screener.models import HouseholdMember


@dataclass(frozen=True)
class SsiYear:
    """One benefit year's SSI figures: the rates, exclusions and limits of spec sections 4.8, 4.9 and 7."""

    #: Federal benefit rate for an eligible individual, which is also the income limit (spec section 7).
    individual_fbr: int
    #: Federal benefit rate for an eligible couple, and the couple's income limit.
    couple_fbr: int
    #: Earned income a student under 22 may exclude in a month (spec section 4.8, `income_limit`;
    #: the yearly cap is not applied, since earlier months' earnings are unknown).
    student_exclusion: int
    #: Countable resource limits, alone and with a spouse (spec section 4.9, `resource_limit`).
    individual_resource_limit: int = 2_000
    couple_resource_limit: int = 3_000
    #: The general exclusion: the first $20 of unearned income other than TANF is not counted.
    general_exclusion: int = 20
    #: The flat earned income exclusion; half of what remains after it is excluded too.
    earned_exclusion: int = 65
    #: Infrequent or irregular income not counted in a quarter, applied as a margin for someone
    #: otherwise just over the limit (spec section 5, `infrequent_income_exclusion`).
    infrequent_earned_margin: int = 30
    infrequent_unearned_margin: int = 60

    @property
    def ineligible_spouse_allowance(self) -> int:
        """Spouse income at or under this deems nothing: the couple rate less the individual rate."""
        return self.couple_fbr - self.individual_fbr

    def resource_limit(self, people: int) -> int:
        return self.couple_resource_limit if people >= 2 else self.individual_resource_limit

    def fbr(self, people: int) -> int:
        return self.couple_fbr if people >= 2 else self.individual_fbr


# 2026 figures: benefit rates from spec section 7, the student exclusion from spec section 4.8.
SSI_YEARS: dict[int, SsiYear] = {
    2026: SsiYear(individual_fbr=994, couple_fbr=1_491, student_exclusion=2_410),
}

SSI_INCOME_TYPE = "sSI"
TANF_INCOME_TYPE = "cashAssistance"
OTHER_CASH_INCOME_TYPE = "cashAssistanceOther"


@dataclass(frozen=True)
class MemberIncome:
    """A member's monthly income, split the way SSI counts it. SSI itself is never income."""

    earned: float
    #: Unearned income other than SSI, TANF and other cash assistance.
    unearned: float
    #: TANF (`cashAssistance`): counted in full, the $20 exclusion does not reach it.
    tanf: float
    #: Other cash assistance (`cashAssistanceOther`), which may be State aid SSI does not count.
    other_cash: float
    #: Earned income left after the student earned income exclusion.
    earned_after_student_exclusion: float


@dataclass(frozen=True)
class CountingRules:
    """
    Which approximations a countable-income pass applies. The plain rules come first; each
    relaxation is tried only when the stricter pass fails, so a household that qualifies
    outright is valued on its actual income.
    """

    #: Take the infrequent-income exclusion off before counting ($30 earned, $60 unearned).
    infrequent_margin: bool = False
    #: Leave other cash assistance out, as if it were State need-based aid.
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
    Federal Supplemental Security Income: the federal payment before any State supplement,
    computed per member.

    Rules and figures: program-ops `programs/white_labels/federal/ssi/federal_ssi_spec.md`.
    Routes are spec section 3; the criteria below are sections 4.1 to 4.5 (age, blindness,
    disability, work test), 4.8 (`income_limit`, including deeming), 4.9 (`resource_limit`)
    and 7 (the payment).

    A member qualifies by age (65 or older), blindness (`visually_impaired`) or disability
    (`disabled` or `long_term_disability`). SSA's own medical finding and the $1,690 work
    test can't be applied: the only inputs to the work test are earnings, and a failure
    on earnings alone is passed because disability-related work expenses, which the
    screener does not collect, would lower them. Citizenship is enforced by the program's
    `legal_status_required`.

    Income is counted monthly: unearned income other than SSI less $20 (TANF gets no $20),
    then earned income less whatever is left of the $20, less $65, halved. A member under
    18, or under 22 and a student, first excludes up to the student amount of earnings. A
    household is tested in SSI's units:

    - the head and their `spouse` who both qualify are an eligible couple: one income
      computation against the couple rate, the payment split equally;
    - a head or spouse whose partner does not qualify has the partner's income deemed:
      nothing when it is at or under the couple-minus-individual allowance,
      otherwise the pair is counted as a couple and the payment is the lesser of the
      individual and couple results;
    - a `child` under 18 has the head's and head's spouse's income deemed, a `stepChild`
      only while the head's spouse is in the household. A parent who
      reports SSI income is not an ineligible parent: the other parent's income is counted
      toward them as a spouse's, and only the couple's excess over the couple rate reaches
      the child. Deemed income is shared equally among the qualifying children;
    - everyone else, a `domesticPartner`'s partner included, is counted alone.

    Someone whose countable income is over the limit is passed if it is over by no more
    than the infrequent-income margin, or only because of other cash assistance, or, for
    someone blind or disabled who is under 65 or already reports SSI, only because of
    their own earnings. Each relaxation is tried in turn and the payment uses the first
    that passes, so it is an upper bound for those households.

    Resources are the one household total the screener collects. It is held to $2,000
    alone, $3,000 for the head and spouse, and for a child to that limit plus $2,000 for
    one parent or $3,000 for two, since parents' resources deem only above their own
    limit. A parent reporting SSI is not counted as a parent. When anyone outside the
    unit lives in the household, the total alone never rules the member out, because it
    cannot be told whose savings they are.

    Residence, presence in the U.S., institution stays, resource transfers, in-kind
    support and sponsor deeming have no screener field and are not evaluated.
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
        """
        The benefit year's figures. A year without any (a January rollover the table was
        not updated for) uses the latest year and is reported rather than raising: an
        exception from a displayed program fails the whole results page, and this program
        shows in every white label.
        """
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
        """
        The parents whose income and resources can deem to `child`: the head and the head's
        spouse for a `child`; for a `stepChild` the head is a stepparent, who counts only
        while the child's own parent (the head's spouse) is in the household. Any other
        relationship, foster and grandchildren included, has no parent in the household.
        """
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
        """
        Whether a failure on this member's earnings alone is passed (spec section 4.8,
        `impairment_related_work_expenses` and `blind_work_expenses`). Blind and disabled
        workers' work expenses lower counted earnings, and the screener does not collect
        them. Past 65 the exclusions continue only for someone who already received SSI as
        blind or disabled, read here as reporting SSI income.
        """
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
        """Under 18, or under 22 and a student (`student` asks about post-secondary study)."""
        age = self._age(member)
        return self._is_child(member) or (age <= self.student_exclusion_max_age and bool(member.student))

    def _countable_income(
        self,
        members: list[HouseholdMember],
        rules: CountingRules,
        applicants: Iterable[HouseholdMember] = (),
        deemed_unearned: float = 0,
    ) -> float:
        """
        Countable monthly income of `members` taken together (spec section 4.8, `income_limit`).

        `applicants` are the members whose own earnings `rules.drop_earnings` leaves out;
        a deemor's earnings always count. `deemed_unearned` is income already deemed to the
        unit, which is unearned income to it.
        """
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
        """
        Parents' income deemed to `child` as unearned income (spec section 4.8 deeming):
        their countable income less the benefit rate for one parent or a parent couple,
        shared equally among the qualifying children.

        A parent who reports SSI is deemed to first: with one such
        parent, the other's income counts toward them as a spouse's and only the couple's
        excess over the couple rate reaches the children. With both reporting SSI, or a lone
        parent reporting it, nothing is deemed.
        """
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
        """
        Whether the household's reported assets leave `member` eligible (spec section 4.9,
        `resource_limit`). Assets are one
        household figure, so when anyone outside the resource `unit` lives in the household
        they cannot be attributed and never rule the member out on their own.
        """
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

    def _rule_passes(self, members: list[HouseholdMember]) -> list[CountingRules]:
        """
        The counting passes to try, strictest first. A relaxation is listed only when it
        could change the answer: the margin always can, the others need other cash
        assistance or droppable earnings in the unit.
        """
        has_other_cash = any(self._income(m).other_cash > 0 for m in members)
        has_droppable_earnings = any(
            self._earnings_can_be_left_out(m) and self._income(m).earned_after_student_exclusion > 0 for m in members
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
        """Both spouses qualify: one couple computation, the payment split equally (spec section 7)."""
        couple = [member, partner]
        if not self._resources_allow(member, couple, self.params.couple_resource_limit):
            return Verdict(False)

        for rules in self._rule_passes(couple):
            countable = self._countable_income(couple, rules, applicants=couple)
            if countable < self.params.couple_fbr:
                return Verdict(True, (self.params.couple_fbr - countable) / 2)

        return Verdict(False)

    def _ineligible_spouse_verdict(self, member: HouseholdMember, partner: HouseholdMember) -> Verdict:
        """
        Deeming from a spouse who does not qualify (spec section 4.8 deeming). Spouse income at or
        under the allowance deems nothing. Above it the pair is counted as a couple, and the
        payment is the lesser of the individual and couple results (spec section 7): deeming
        can neither raise the payment nor qualify someone their own income does not.
        """
        params = self.params
        if not self._resources_allow(member, [member, partner], params.couple_resource_limit):
            return Verdict(False)

        partner_income = self._income(partner)
        spouse_income = (
            partner_income.earned + partner_income.unearned + partner_income.tanf + partner_income.other_cash
        )
        deeming_applies = spouse_income > params.ineligible_spouse_allowance

        for rules in self._rule_passes([member]):
            own = self._countable_income([member], rules, applicants=[member])
            if own >= params.individual_fbr:
                continue
            payment = params.individual_fbr - own

            if deeming_applies:
                couple = self._countable_income([member, partner], rules, applicants=[member])
                if couple >= params.couple_fbr:
                    continue
                payment = min(payment, params.couple_fbr - couple)

            return Verdict(True, payment)

        return Verdict(False)

    def _child_verdict(self, child: HouseholdMember) -> Verdict:
        """
        A child under 18 with a parent in the household (spec sections 4.8 and 4.9).
        """
        params = self.params
        parents = self._parents_of(child)
        counted_parents = [p for p in parents if not self._reports_ssi(p)]
        limit = params.individual_resource_limit + (
            params.resource_limit(len(counted_parents)) if counted_parents else 0
        )
        if not self._resources_allow(child, [child, *counted_parents], limit):
            return Verdict(False)

        for rules in self._rule_passes([child]):
            deemed = self._deemed_to_child(child, rules)
            countable = self._countable_income([child], rules, applicants=[child], deemed_unearned=deemed)
            if countable < params.individual_fbr:
                return Verdict(True, params.individual_fbr - countable)

        return Verdict(False)

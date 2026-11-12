"""NJ TANF — Work First New Jersey."""

from dataclasses import dataclass, field
from decimal import Decimal

import programs.framework.eligibility_messages as messages
from programs.framework.base import Eligibility
from programs.programs.cross_white_label.tanf.mfb_base import MONTHS_PER_YEAR, MfbTanf, money
from screener.models import HouseholdMember

# Relationships to the head that NJ places in the unit as a child, through age 18.
CHILD = "child"
STEP_CHILD = "stepChild"
# Relatives the screener can't place: counted as children through 18 as an approximation.
PROVISIONAL_RELATIVES = (
    "stepChild",
    "grandChild",
    "fosterChild",
    "sisterOrBrother",
    "stepSisterOrBrother",
    "relatedOther",
)
CHILD_RELATIONSHIPS = (CHILD, *PROVISIONAL_RELATIVES)


@dataclass
class AssistanceUnit:
    """The screener's proxy for NJ's assistance unit, and whose income counts for it."""

    members: list[HouseholdMember] = field(default_factory=list)
    children: list[HouseholdMember] = field(default_factory=list)
    # An SSI recipient outside the unit whose non-SSI income still counts (3.12(a)).
    ssi_outsiders: list[HouseholdMember] = field(default_factory=list)
    # Those whose reported child support counts as the children's.
    child_support_payees: list[HouseholdMember] = field(default_factory=list)

    @property
    def size(self) -> int:
        return len(self.members)


class NjTanf(MfbTanf):
    """
    Work First New Jersey (WFNJ/TANF), N.J.A.C. 10:90. Inherits the federal shape from
    ``MfbTanf``; NJ changes who counts and adds a second income test.

    The assistance unit is a proxy built from relationships to the head of household:

    - the head, a ``spouse`` and each ``child`` 18 or younger; a stepchild, grandchild, foster
      child, sibling, step-sibling or other relative 18 or younger is counted as a child too, as an
      approximation, since the screener can't tell how NJ would place them
    - where the head has no ``child`` or ``stepChild``, only those relatives: the child-only case,
      with the head and spouse and their income left out, but child support reported under the head
      counted as the children's
    - an SSI recipient is never in the unit. Their SSI is exempt, but the non-SSI income of an SSI
      head who is the parent of a ``child`` under 18 in the unit, or of an SSI spouse of a unit
      member, still counts, wages gross. A head whose only ``child`` receives SSI is a needy
      parent and is eligible alone, unless they too receive SSI with no non-SSI spouse

    A pregnant woman with no other children is served by General Assistance, not TANF.

    Two income tests, in monthly dollars:

    - Schedule I, for a new applicant: unearned income, child support received and earnings, all in
      full, less child support paid, at or below the Schedule I limit. A household reporting
      ``cashAssistance`` is treated as a current case and skips it
    - Schedule II: the same with 50% of the unit's earnings disregarded and child support received
      above the 100 dollar (one child) or 200 dollar (two or more) pass-through, less than the
      maximum benefit

    A child's earnings, the household's own WFNJ grant (``cashAssistance``) and SSI are exempt.
    Resources are limited to 2,000 dollars.

    The benefit is the maximum benefit less the Schedule II income, kept in cents and rounded to
    whole dollars once made annual.

    Approximations beyond the base's, all from the spec's data gaps: the 100% and 75% early
    earnings disregards are not applied; the non-needy stepparent, ineligible-immigrant parent and
    minor-parent deeming rules are not evaluated; spousal support paid and NJ's other exempt income
    are not collected; and a non-spouse parent of the child outside the proxy unit (a domestic
    partner, say) has no income counted.

    The spec is ``programs/cross_white_label/tanf/nj/tanf_nj_spec.md`` in program-ops.
    """

    program_code = "nj_tanf"

    serves_pregnant_individual = False
    resource_limit = 2_000

    # N.J.A.C. 10:90-3.3(b): Schedule I (initial eligibility) and Schedule II (maximum benefit).
    schedule_i = {1: 321, 2: 638, 3: 839, 4: 966, 5: 1_092, 6: 1_221, 7: 1_341, 8: 1_442}
    schedule_i_additional_person = 99
    schedule_ii = {1: 214, 2: 425, 3: 559, 4: 644, 5: 728, 6: 814, 7: 894, 8: 961}
    schedule_ii_additional_person = 66

    earned_income_disregard = Decimal("0.50")
    # 3.8(h): child support passed through to a unit with one child, or with two or more.
    one_child_pass_through = 100
    two_child_pass_through = 200

    dependencies = [
        *MfbTanf.dependencies,
        "expense_type",
        "expense_amount",
        "expense_frequency",
    ]

    def has_qualifying_family(self) -> bool:
        unit = self.assistance_unit()
        if unit.children:
            return True

        return self._has_needy_parent_of_ssi_child()

    def _has_needy_parent_of_ssi_child(self) -> bool:
        """2.7(a)1iii: a needy parent whose own child receives SSI, with that child outside the unit."""
        members = list(self.screen.household_members.all())
        has_ssi_child = any(
            member.relationship == CHILD and self._is_child_age(member) and self._receives_ssi(member)
            for member in members
        )
        if not has_ssi_child:
            return False

        head = self.screen.get_head()
        if head is not None and not self._receives_ssi(head):
            return True

        return any(member.relationship == "spouse" and not self._receives_ssi(member) for member in members)

    def assistance_unit(self) -> AssistanceUnit:
        if not hasattr(self, "_unit"):
            self._unit = self._build_assistance_unit()

        return self._unit

    def _build_assistance_unit(self) -> AssistanceUnit:
        members = list(self.screen.household_members.all())
        head = next((member for member in members if member.relationship == "headOfHousehold"), None)
        unit = AssistanceUnit()

        unit.children = [
            member
            for member in members
            if member.relationship in CHILD_RELATIONSHIPS
            and self._is_child_age(member)
            and not self._receives_ssi(member)
        ]

        child_only = not any(member.relationship in (CHILD, STEP_CHILD) for member in members) and bool(unit.children)
        if child_only:
            unit.members = list(unit.children)
            if head is not None:
                unit.child_support_payees = [*unit.children, head]
            else:
                unit.child_support_payees = list(unit.children)
            return unit

        adults = [member for member in members if member.relationship in ("headOfHousehold", "spouse")]
        unit.members = [adult for adult in adults if not self._receives_ssi(adult)] + unit.children
        unit.child_support_payees = list(unit.members)

        has_child_under_18 = any(
            child.relationship == CHILD and (child.calc_age() or 0) < self.minor_child_age for child in unit.children
        )
        head_in_unit = head is not None and head in unit.members
        spouse_in_unit = any(adult.relationship == "spouse" for adult in unit.members)

        for adult in adults:
            if not self._receives_ssi(adult):
                continue

            if adult.relationship == "headOfHousehold":
                is_parent = has_child_under_18
                if is_parent:
                    unit.child_support_payees.append(adult)
                if is_parent or spouse_in_unit:
                    unit.ssi_outsiders.append(adult)
            elif head_in_unit:
                unit.ssi_outsiders.append(adult)

        return unit

    def _is_child_age(self, member: HouseholdMember) -> bool:
        age = member.calc_age()
        return age is not None and age <= self.minor_child_age

    @staticmethod
    def _receives_ssi(member: HouseholdMember) -> bool:
        return member.calc_gross_income("monthly", ["sSI"]) > 0

    def _unearned_income(self) -> Decimal:
        unit = self.assistance_unit()
        return sum(
            (
                money(
                    member.calc_gross_income("monthly", ["unearned"], exclude=["sSI", "childSupport", "cashAssistance"])
                )
                for member in unit.members + unit.ssi_outsiders
            ),
            Decimal(0),
        )

    def _child_support_received(self) -> Decimal:
        return sum(
            (
                money(member.calc_gross_income("monthly", ["childSupport"]))
                for member in self.assistance_unit().child_support_payees
            ),
            Decimal(0),
        )

    def _earned_income(self) -> Decimal:
        """The unit's earnings, a child's exempt."""
        unit = self.assistance_unit()
        return sum(
            (
                money(member.calc_gross_income("monthly", ["earned"]))
                for member in unit.members
                if member not in unit.children
            ),
            Decimal(0),
        )

    def _ssi_outsider_earned_income(self) -> Decimal:
        """Counted gross: the earnings disregard applies only to members of the unit."""
        return sum(
            (money(member.calc_gross_income("monthly", ["earned"])) for member in self.assistance_unit().ssi_outsiders),
            Decimal(0),
        )

    def _child_support_paid(self) -> Decimal:
        return money(self.screen.calc_expenses("monthly", ["childSupport"]))

    def _child_support_pass_through(self) -> Decimal:
        children = len(self.assistance_unit().children)
        if children == 0:
            return Decimal(0)

        return Decimal(self.one_child_pass_through if children == 1 else self.two_child_pass_through)

    def _reports_cash_assistance(self) -> bool:
        return self.screen.calc_gross_income("monthly", ["cashAssistance"]) > 0

    @staticmethod
    def _by_size(table: dict[int, int], additional_person: int, size: int) -> Decimal:
        largest = max(table)
        if size <= largest:
            return Decimal(table[size])

        return Decimal(table[largest] + (size - largest) * additional_person)

    def countable_income(self) -> Decimal:
        """Schedule I income: everything in full, with no disregard or pass-through."""
        income = (
            self._unearned_income()
            + self._child_support_received()
            + self._earned_income()
            + self._ssi_outsider_earned_income()
            - self._child_support_paid()
        )
        return max(Decimal(0), income)

    def income_standard(self) -> Decimal:
        return self._by_size(self.schedule_i, self.schedule_i_additional_person, self.assistance_unit().size)

    def benefit_level_income(self) -> Decimal:
        """Schedule II income: earnings disregard and child support pass-through applied."""
        income = (
            self._unearned_income()
            + max(Decimal(0), self._child_support_received() - self._child_support_pass_through())
            + self._earned_income() * (1 - self.earned_income_disregard)
            + self._ssi_outsider_earned_income()
            - self._child_support_paid()
        )
        return max(Decimal(0), income)

    def maximum_benefit(self) -> Decimal:
        return self._by_size(self.schedule_ii, self.schedule_ii_additional_person, self.assistance_unit().size)

    def income_eligible(self, e: Eligibility) -> None:
        # A current case, shown by its own grant reported as income, isn't held to Schedule I.
        if not self._reports_cash_assistance():
            super().income_eligible(e)

        income = self.benefit_level_income()
        limit = self.maximum_benefit()
        e.condition(income < limit, messages.income(income * MONTHS_PER_YEAR, limit * MONTHS_PER_YEAR))

    def benefit_amount(self) -> Decimal:
        return self.maximum_benefit() - self.benefit_level_income()

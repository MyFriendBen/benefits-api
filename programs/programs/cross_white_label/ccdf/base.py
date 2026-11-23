"""Child Care and Development Fund (CCDF) — MFB federal base."""

from decimal import ROUND_HALF_UP, Decimal
from typing import ClassVar

import programs.framework.eligibility_messages as messages
from programs.framework.base import Eligibility, MemberEligibility, PaymentUnit, ProgramCalculator
from screener.models import HouseholdMember

#: Relationships to the head of household that make a member a child the head, or the
#: head's spouse or partner, can be raising.
CHILD_RELATIONSHIPS = ("child", "fosterChild", "stepChild", "grandChild", "sisterOrBrother")

#: Who counts as a child's parent besides the head of household.
PARTNER_RELATIONSHIPS = ("spouse", "domesticPartner")

#: Income types that show a parent is working.
WORK_INCOME_TYPES = ("wages", "selfEmployment")


class Ccdf(ProgramCalculator, abstract=True):
    """
    Federal CCDF child care subsidy (45 CFR 98.20, 98.45; 42 U.S.C. 9858n), computed in our
    own code. The base backs no program; each state subclasses it.

    A household is eligible when it has a child under 13, listed as the head's child, foster
    child, stepchild, grandchild or sibling, and:

    - its yearly income is at or under the state's limit for first qualifying
    - its assets are at or under 1,000,000 dollars, or it did not answer
    - the head of household, or the head's spouse or domestic partner, works or is in school or
      job training

    The child's immigration status is the program record's ``legal_status_required``, not this
    class's. The protective services route is not evaluated: the screener asks nothing about it.

    Approximations, from the spec's data gaps:

    - the household stands in for the child's family, for income, assets and size
    - the head and the head's spouse or partner stand in for the child's parents, so a child
      raised by anyone else is not counted, and a grandchild or sibling is
    - one active parent is enough, wherever a state requires every parent to be active
    - a child under 19 who cannot care for themselves or is under court supervision is not
      counted, and every income is counted, temporary or not

    The value is one amount for the household: the state's monthly payment rate for each
    eligible child, less the family's one monthly copay, never below 0, times 12.

    Each state sets:

    - ``income_limit()``: its yearly limit for the household size
    - ``payment_rate(child)``: its monthly rate for one child
    - ``family_copayment(children)``: the family's monthly copay
    - ``income_exclusions``: income types its limit and copay leave out
    - ``parent_is_active(parent)``: where its activity rule is stricter than the federal one

    The spec is ``programs/cross_white_label/ccdf/base/ccdf_base_spec.md`` in program-ops.
    """

    payment_unit = PaymentUnit.HOUSEHOLD

    max_child_age = 13
    asset_limit = 1_000_000
    income_exclusions: ClassVar[tuple[str, ...]] = ()

    dependencies = (
        "age",
        "relationship",
        "student",
        "household_size",
        "income_amount",
        "income_frequency",
        "income_type",
    )

    def member_eligible(self, e: MemberEligibility) -> None:
        member = e.member
        age = member.calc_age()
        e.condition(member.relationship in CHILD_RELATIONSHIPS and age is not None and age < self.max_child_age)

    def household_eligible(self, e: Eligibility) -> None:
        income = self.countable_income()
        income_limit = self.income_limit()
        e.condition(income <= income_limit, messages.income(income, income_limit))

        assets = self.screen.household_assets
        e.condition(assets is None or assets <= self.asset_limit, messages.assets(self.asset_limit))

        e.condition(any(self.parent_is_active(parent) for parent in self.parents()))

    def countable_income(self) -> Decimal:
        """Yearly income of everyone listed, less ``income_exclusions``, to the cent."""
        income = self.screen.calc_gross_income("yearly", ["all"], exclude=self.income_exclusions)
        return Decimal(str(round(income, 2)))

    def income_limit(self) -> int:
        """The state's yearly income limit for first qualifying, for the household size."""
        raise NotImplementedError

    def parents(self) -> list[HouseholdMember]:
        """The head of household and the head's spouse or domestic partner."""
        return [
            member
            for member in self.screen.household_members.all()
            if member.relationship == "headOfHousehold" or member.relationship in PARTNER_RELATIONSHIPS
        ]

    def parent_is_active(self, parent: HouseholdMember) -> bool:
        """Works, is a student, or is in job training."""
        works = any(stream.type in WORK_INCOME_TYPES for stream in parent.income_streams.all())
        return works or parent.student is True or parent.student_job_training_program is True

    def value(self, e: Eligibility) -> None:
        if not e.eligible:
            return

        children = [member_e.member for member_e in e.eligible_members if member_e.eligible]
        monthly = sum((self.payment_rate(child) for child in children), Decimal(0)) - self.family_copayment(children)
        annual = max(Decimal(0), monthly) * 12

        e.household_value = int(annual.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    def payment_rate(self, child: HouseholdMember) -> Decimal:
        """The state's monthly payment rate for one eligible child's care."""
        raise NotImplementedError

    def family_copayment(self, children: list[HouseholdMember]) -> Decimal:
        """The family's one monthly copay, for these eligible children."""
        raise NotImplementedError

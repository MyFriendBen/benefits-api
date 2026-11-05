"""Temporary Assistance for Needy Families — MFB federal base."""

from decimal import ROUND_HALF_UP, Decimal
from typing import ClassVar, Optional

import programs.framework.eligibility_messages as messages
from programs.framework.base import Eligibility, ProgramCalculator
from screener.models import HouseholdMember

MONTHS_PER_YEAR = 12


def money(amount: float) -> Decimal:
    """A screener amount as a Decimal, via its repr so a float sum keeps its cents."""
    return Decimal(str(amount))


class MfbTanf(ProgramCalculator, abstract=True):
    """
    Federal Temporary Assistance for Needy Families (42 U.S.C. 601 et seq.), computed in our own
    code. It sits beside the PolicyEngine ``Tanf`` in ``base.py``, which the states not yet moved
    still use (MFB-1919).

    A family is eligible when all of these hold:

    - it includes a minor child: someone under 18, or 18 and not the head of household, a spouse or
      a domestic partner (42 U.S.C. 619(2)); or, where the state serves them, a pregnant member
      (42 U.S.C. 608(a)(1))
    - its countable income, counted by the state's rules, is within the state's income standard
    - its assets are within the state's resource limit, where the state sets one

    Immigration status is enforced by the Program row's ``legal_status_required``, not here.

    Approximations, all from the spec's data gaps:

    - every 18-year-old who is not a head, spouse or partner counts as a high-school student;
      secondary-school enrollment is not collected
    - a child is assumed to live with a parent or other caretaker relative; relationships are
      recorded only to the head of household
    - sponsor income and resources are not deemed; sponsorship is not collected

    The base sets no figure. Each state supplies its income standard, its counting rules, its
    resource limit and its benefit amount, by overriding ``income_standard``, ``countable_income``,
    ``resource_limit`` and ``benefit_amount``. A state with its own household test or extra income
    test overrides ``has_qualifying_family`` or ``income_eligible``.

    The value is the state's monthly benefit, made annual and rounded to whole dollars, and never
    less than 1 dollar for an eligible household so the results page keeps it.

    The spec is ``programs/cross_white_label/tanf/base/tanf_base_spec.md`` in program-ops.
    """

    #: The state's resource standard. None where the state sets no resource test.
    resource_limit: ClassVar[Optional[int]] = None

    #: Whether a pregnant member alone makes a family eligible. A state that serves pregnant women
    #: with no other children outside TANF turns this off.
    serves_pregnant_individual: ClassVar[bool] = True

    minor_child_age = 18
    # The relationships an 18-year-old can't hold and still be someone's minor child.
    adult_relationships = ("headOfHousehold", "spouse", "domesticPartner")

    dependencies = [
        "age",
        "relationship",
        "household_assets",
        "income_type",
        "income_amount",
        "income_frequency",
    ]

    def household_eligible(self, e: Eligibility) -> None:
        if not self.has_qualifying_family():
            e.condition(False, messages.child(0, self.minor_child_age))
            return

        self.income_eligible(e)

        if self.resource_limit is not None:
            assets = self.screen.household_assets if self.screen.household_assets is not None else 0
            e.condition(assets <= self.resource_limit, messages.assets(self.resource_limit))

    def has_qualifying_family(self) -> bool:
        """A minor child, or a pregnant member where the state serves one."""
        members = list(self.screen.household_members.all())
        if any(self.is_minor_child(member) for member in members):
            return True

        return self.serves_pregnant_individual and any(member.pregnant is True for member in members)

    def is_minor_child(self, member: HouseholdMember) -> bool:
        age = member.calc_age()
        if age is None:
            return False

        if age < self.minor_child_age:
            return True

        return age == self.minor_child_age and member.relationship not in self.adult_relationships

    def income_eligible(self, e: Eligibility) -> None:
        """Countable income at or below the income standard, both monthly."""
        income = self.countable_income()
        limit = self.income_standard()
        e.condition(income <= limit, messages.income(income * MONTHS_PER_YEAR, limit * MONTHS_PER_YEAR))

    def countable_income(self) -> Decimal:
        """Monthly income counted by the state's rules."""
        raise NotImplementedError

    def income_standard(self) -> Decimal:
        """The state's monthly income standard for this family."""
        raise NotImplementedError

    def benefit_amount(self) -> Decimal:
        """The state's monthly benefit for this family."""
        raise NotImplementedError

    def household_value(self) -> int:
        annual = (self.benefit_amount() * MONTHS_PER_YEAR).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        return max(1, int(annual))

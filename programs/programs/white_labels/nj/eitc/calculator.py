from decimal import ROUND_HALF_UP, Decimal
from functools import cached_property

from programs.framework.base import Eligibility
from programs.programs.white_labels.federal.eitc.calculator import FederalEitc, eic_table


class NjEitc(FederalEitc):
    """
    New Jersey Earned Income Tax Credit (NJEITC), claimed on line 58 of the NJ-1040 for the
    program's tax year.

    Two routes, tried in this order:

    - Federal credit: a household that qualifies for the federal EITC gets 40% of it. The
      federal credit is worked out by ``FederalEitc``, so both programs read the same EIC
      Table and the same household rules.
    - Age expansion: a household the federal credit turns away only on age gets a flat $260
      (40% of the $649 federal maximum with no children). The head must be 18 or older at the
      end of the tax year and the household must have no qualifying child. Every other federal
      rule applies, including the income limits, but there is no maximum age and no minimum
      of 25.

    Values are whole dollars, so 40% of a federal credit is rounded to the dollar. It is
    floored at $1 because a value of $0 reads as not eligible, and a household that
    qualifies for a few dollars of federal credit does qualify.

    Data gaps (spec §5): Social Security numbers, whether another taxpayer can claim the
    filer as a dependent, and civil union partners entered as domestic partners, whom the
    federal rules count as unmarried. The credit is not prorated for part-year residency and
    is shown before any refund offset for debts.
    """

    program_code = "nj_eitc"

    nj_rate = Decimal("0.40")
    age_expansion_amount = 260
    age_expansion_min_age = 18

    def household_eligible(self, e: Eligibility) -> None:
        if self._on_federal_route:
            e.condition(True)
            return

        params = self._params
        column = self._column

        e.condition(self._head_is_old_enough())
        e.condition(self._qualifying_child_count == 0)
        e.condition(self._investment_income <= params.investment_income_limit)
        e.condition(0 < self._earned_income < column.limit)
        e.condition(self._agi < column.limit)
        # Worksheet A's $0 lookup ends the claim here as it does for the federal credit.
        e.condition(eic_table(self._earned_income, column) > 0)

    def household_value(self) -> int:
        if not self._on_federal_route:
            return self.age_expansion_amount

        credit = (self.nj_rate * super().household_value()).quantize(Decimal(1), rounding=ROUND_HALF_UP)
        return max(int(credit), 1)

    @cached_property
    def _on_federal_route(self) -> bool:
        """Whether the household qualifies for the federal credit, age rules included."""
        federal = Eligibility()
        super().household_eligible(federal)

        return federal.eligible

    def _head_is_old_enough(self) -> bool:
        heads = [m for m in self.screen.household_members.all() if m.relationship == "headOfHousehold"]
        return any(
            age is not None and age >= self.age_expansion_min_age
            for age in (head.age_at_end_of_year(self.tax_year) for head in heads)
        )

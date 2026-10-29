from decimal import Decimal
from functools import cached_property

from sentry_sdk import capture_message

import programs.framework.eligibility_messages as messages
from programs.framework.base import Eligibility, MemberEligibility, ProgramCalculator
from programs.programs.white_labels.federal.ctc.calculator import FederalCtc
from programs.programs.white_labels.nj.income_tax import EXCLUDED_INCOME_TYPES, filers
from screener.models import DEPENDENT_ELIGIBLE_RELATIONSHIPS, HouseholdMember


class NjCtc(ProgramCalculator):
    """
    New Jersey Child Tax Credit: a refundable credit on the NJ-1040 for each child who has not
    turned 6 by the end of the tax year, for filers with New Jersey taxable income of 80,000 or
    less. The amount per child falls by income bracket, on a higher schedule for tax years
    2026 to 2028. Rules and figures: program-ops `programs/white_labels/nj/ctc/nj_ctc_spec.md`.

    A child counts as a qualifying child (child, stepchild, foster child, grandchild, sibling
    or step-sibling) or, for any other relative, as a qualifying relative whose own income,
    less the untaxed types, is under the tax year's exemption amount. Age is judged on
    December 31 of the tax year.

    Income is the head's and spouse's, less the types New Jersey doesn't tax; the same figure
    picks the bracket. Data gaps (spec §5): NJ taxable income, filing status (married filing
    separately), the filer's tax unit, residency in the tax year, whether someone claims the
    filer, and the residency, support and tiebreaker tests for the child. Approximations (spec
    §7): no part-year proration and no refund offset for debts.
    """

    program_code = "nj_ctc"

    income_limit = 80_000
    child_age_limit = 6
    # Spec §4 `qc_relationship` and `qr_dependent`: the federal dependent relationships.
    child_relationships = FederalCtc.child_relationships
    dependent_relationships = DEPENDENT_ELIGIBLE_RELATIONSHIPS
    # Spec §4 `income_limit`: veteran stays counted, since the type mixes exempt military
    # pensions with taxable amounts.
    nj_exempt_income_types = [t for t in EXCLUDED_INCOME_TYPES if t != "veteran"]
    # Spec §4 `qr_dependent`: the federal untaxed types.
    federal_exempt_income_types = FederalCtc.tax_exempt_income_types
    # Spec §4 `qr_dependent`: the exemption amount by tax year.
    qualifying_relative_income_limits = {2025: 5_200, 2026: 5_300}

    # Spec §7: credit per child by the top of each income bracket.
    enhanced_schedule_years = (2026, 2027, 2028)
    enhanced_schedule = ((30_000, 1_250), (40_000, 1_000), (50_000, 750), (60_000, 500), (80_000, 250))
    standard_schedule = ((30_000, 1_000), (40_000, 800), (50_000, 600), (60_000, 400), (80_000, 200))

    dependencies = ["age", "relationship", "income_type", "income_amount", "income_frequency"]

    def household_eligible(self, e: Eligibility) -> None:
        e.condition(self._income <= self.income_limit, messages.income(self._income, self.income_limit))

    def member_eligible(self, e: MemberEligibility) -> None:
        member = e.member
        age = member.age_at_end_of_year(self.tax_year)
        e.condition(age is not None and age < self.child_age_limit)
        # `age_at_end_of_year` reads a child born after the tax year as 0, but they weren't
        # the filer's child that year.
        e.condition(member.birth_year is None or member.birth_year <= self.tax_year)
        e.condition(self._is_dependent(member))

    def member_value(self, member: HouseholdMember) -> int:
        schedule = self.enhanced_schedule if self.tax_year in self.enhanced_schedule_years else self.standard_schedule
        for top, credit in schedule:
            if self._income <= top:
                return credit

        return 0

    @cached_property
    def _income(self) -> Decimal:
        """Spec §4 `income_limit`: the head's and spouse's income less the NJ-exempt types."""
        return sum(
            (
                Decimal(str(m.calc_gross_income("yearly", ["all"], exclude=self.nj_exempt_income_types)))
                for m in filers(self.screen)
            ),
            Decimal(0),
        )

    def _is_dependent(self, member: HouseholdMember) -> bool:
        """Spec §3 routes: a qualifying child, or else a qualifying relative."""
        if member.relationship in self.child_relationships:
            return True
        if member.relationship not in self.dependent_relationships:
            return False

        own_income = Decimal(str(member.calc_gross_income("yearly", ["all"], exclude=self.federal_exempt_income_types)))
        return own_income < self._qualifying_relative_income_limit

    @cached_property
    def _qualifying_relative_income_limit(self) -> int:
        """A year with no figure takes the latest and reports to Sentry rather than raising."""
        tax_year = self.tax_year
        if tax_year in self.qualifying_relative_income_limits:
            return self.qualifying_relative_income_limits[tax_year]

        latest = max(self.qualifying_relative_income_limits)
        capture_message(
            f"No NJ CTC qualifying-relative income limit for tax year {tax_year}; using {latest}.",
            level="error",
        )
        return self.qualifying_relative_income_limits[latest]

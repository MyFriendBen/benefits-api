"""Head Start Preschool — MFB federal base."""

from datetime import date
from typing import ClassVar

import programs.framework.eligibility_messages as messages
from programs.framework.base import Eligibility, MemberEligibility, ProgramCalculator
from programs.framework.pe_dependencies.receipt import (
    SSI_INCOME_TYPE,
    screen_reports_snap,
    screen_reports_tanf,
)
from screener.models import HouseholdMember


class MfbHeadStart(ProgramCalculator, abstract=True):
    """
    Federal Head Start Preschool (45 CFR 1302.12), computed in our own code. It sits beside
    the PolicyEngine ``HeadStart`` in ``base.py``, which the states not yet moved still use.

    A child is eligible when they are of preschool age and one of these holds:

    - family income, less housing costs above 30% of it, is at or below the poverty line
    - the family receives or is eligible for TANF, SSI or SNAP
    - the child is in foster care

    Homelessness, the Migrant/Seasonal and Tribal routes, and the small-community rule have
    no screener field and are not evaluated. The 35% (under 130% FPL) and 10% over-income
    allowances are enrollment slots, not eligibility, so they are left out too.

    Each state sets:

    - ``school_eligibility_cutoff_date``: (month, day) a child must turn 3 by to count as 3
    - ``compulsory_school_age``: the age a child must be under
    - ``weekly_price`` and ``program_weeks``: the value is their product per eligible child
    - ``gates_on_any``: its own SNAP/TANF/SSI program codes, read tolerantly through
      ``any_program_eligible``. Leave it empty where the state has none.
    """

    min_age = 3

    school_eligibility_cutoff_date: ClassVar[tuple[int, int]]
    compulsory_school_age: ClassVar[int]
    weekly_price: ClassVar[float]
    program_weeks: ClassVar[int]

    # 45 CFR 1305.2 "Income": wages, business income, unemployment and pensions. Taxable
    # gifts and military pay exclusions can't be told apart in the screener's data.
    countable_income_types = ("wages", "selfEmployment", "unemployment", "pension")
    # 45 CFR 1305.2 "Housing costs". Renter's insurance isn't collected.
    housing_expense_types = (
        "rent",
        "mortgage",
        "propertyTax",
        "homeownersInsurance",
        "heating",
        "cooling",
        "otherUtilities",
    )
    housing_cost_share = 0.30

    dependencies = [
        "age",
        "relationship",
        "household_size",
        "income_amount",
        "income_frequency",
        "income_type",
        "expense_type",
        "expense_amount",
        "expense_frequency",
    ]

    def member_eligible(self, e: MemberEligibility) -> None:
        member = e.member
        age = member.calc_age()
        if age is None:
            e.condition(False)
            return

        e.condition(self._is_three_by_cutoff(member, age) and age < self.compulsory_school_age)

    def _is_three_by_cutoff(self, member: HouseholdMember, age: int) -> bool:
        """
        3 today, or 3 on the next school cutoff date. Birth is dated to the first of the
        month, since the screener collects no day of birth.
        """
        if age >= self.min_age:
            return True

        if member.birth_year_month is None:
            return False

        return HouseholdMember.age_from_date(member.birth_year_month, self._next_cutoff()) >= self.min_age

    def _next_cutoff(self) -> date:
        today = self.screen.get_reference_date()
        month, day = self.school_eligibility_cutoff_date
        cutoff = date(today.year, month, day)
        if cutoff < today:
            cutoff = date(today.year + 1, month, day)

        return cutoff

    def household_eligible(self, e: Eligibility) -> None:
        income = self._countable_income()
        income_limit = self._income_limit()
        if income <= income_limit:
            e.condition(True, messages.income(income, income_limit))
            return

        if self._public_assistance_eligible():
            e.condition(True, messages.presumed_eligibility())
            return

        # Foster care qualifies the foster child only, not their siblings.
        for member_eligibility in e.member_verdicts:
            if member_eligibility.member.relationship != "fosterChild":
                member_eligibility.condition(False)

        if not any(member_eligibility.eligible for member_eligibility in e.member_verdicts):
            e.condition(False, messages.income(income, income_limit))

    def _countable_income(self) -> float:
        """Gross income, less housing costs above 30% of it (45 CFR 1302.12(i)(1)(ii))."""
        gross = self.screen.calc_gross_income("yearly", list(self.countable_income_types))
        housing = self.screen.calc_expenses("yearly", list(self.housing_expense_types))
        excess_housing = max(0, housing - self.housing_cost_share * gross)

        return gross - excess_housing

    def _income_limit(self) -> int:
        return int(self.program.year.get_limit(self.screen.household_size))

    def _public_assistance_eligible(self) -> bool:
        """Receives TANF, SSI or SNAP, or is eligible for one of the state's own."""
        return (
            screen_reports_snap(self.screen)
            or screen_reports_tanf(self.screen)
            or self.screen.has_base_benefit("ssi")
            or self.screen.calc_gross_income("yearly", [SSI_INCOME_TYPE]) > 0
            or self.any_program_eligible(self.gates_on_any)
        )

    def member_value(self, member: HouseholdMember) -> int:
        return round(self.weekly_price * self.program_weeks)

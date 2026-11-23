"""The family-level eligibility rules shared by Head Start Preschool and Early Head Start."""

import programs.framework.eligibility_messages as messages
from programs.framework.base import Eligibility, ProgramCalculator
from programs.framework.pe_dependencies.receipt import (
    SSI_INCOME_TYPE,
    screen_reports_snap,
    screen_reports_tanf,
)
from screener.models import HouseholdMember


class HeadStartEligibility(ProgramCalculator, abstract=True):
    """
    The household rules of 45 CFR 1302.12(c), which Head Start Preschool and Early Head Start
    apply the same way. A member who passes the program's own age (or pregnancy) rule is
    eligible when one of these holds:

    - family income, less housing costs above 30% of it, is at or below the poverty line
    - the family receives or is eligible for TANF, SSI or SNAP
    - the member is in foster care, which qualifies that member alone

    Each program sets its own ``member_eligible``, ``member_value`` and, where its foster
    route is narrower than "any foster child", ``_in_foster_care``. Each state sets
    ``gates_on_any`` to its own SNAP, TANF or SSI program codes, read tolerantly through
    ``any_program_eligible``, and leaves it empty where it has none.
    """

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
        for member_eligibility in e.eligible_members:
            if not self._in_foster_care(member_eligibility.member):
                member_eligibility.condition(False)

        if not any(member_eligibility.eligible for member_eligibility in e.eligible_members):
            e.condition(False, messages.income(income, income_limit))

    def _in_foster_care(self, member: HouseholdMember) -> bool:
        return member.relationship == "fosterChild"

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

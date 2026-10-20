"""SUN Bucks (Summer EBT) — federal base."""

from typing import ClassVar

import programs.framework.eligibility_messages as messages
from programs.framework.base import Eligibility, MemberEligibility, ProgramCalculator

# Base programs whose receipt makes a child categorically eligible (7 CFR 292.2) or
# already certified for free or reduced-price school meals (7 CFR 292.12(d)(1)(i)(A)).
# FDPIR, homeless, migrant and runaway children have no screener field.
HOUSEHOLD_QUALIFYING_BASE_PROGRAMS = ("snap", "tanf", "nslp", "head_start")


class SunBucks(ProgramCalculator, abstract=True):
    """
    Federal SUN Bucks (Summer EBT, 7 CFR part 292): a one-time summer grocery benefit for each
    school-age child. The base sets the federal rules; each state sets its compulsory school ages
    and the program code it backs.

    A school-age child is eligible when any of these holds:

    - the household receives SNAP, TANF or school meals, or has a child in Head Start
    - the child is a foster child
    - household income is at or below 185% of the poverty line

    Approximations, all from the spec's data gaps:

    - school enrollment in a school meal school is not collected, so compulsory school age stands in for it
    - school meals and Head Start are recorded for the household, so every school-age child in it qualifies
    - any child listed as a foster child qualifies, whether or not the placement is formal
    - income is the gross amount entered, not net of business costs, for the household size entered

    FDPIR, homeless, migrant and runaway children are not evaluated: the screener collects nothing for them.

    The value is the 48 states and DC amount, $40 a month for the three summer months. Alaska, Hawaii
    and the territories pay more, and no white label of ours is in them.

    Each state sets:

    - ``min_school_age`` and ``max_school_age``: the compulsory school ages, inclusive
    """

    min_school_age: ClassVar[int]
    max_school_age: ClassVar[int]

    # 91 FR 17932: 185% of the poverty guideline, rounded up to the next whole dollar.
    income_limit_percent = 185
    member_amount = 40 * 3

    dependencies = [
        "age",
        "relationship",
        "household_size",
        "income_amount",
        "income_frequency",
    ]

    def member_eligible(self, e: MemberEligibility) -> None:
        age = e.member.calc_age()
        if age is None:
            e.condition(False)
            return

        e.condition(self.min_school_age <= age <= self.max_school_age)

    def household_eligible(self, e: Eligibility) -> None:
        if any(self.screen.has_base_benefit(program) for program in HOUSEHOLD_QUALIFYING_BASE_PROGRAMS):
            e.condition(True, messages.presumed_eligibility())
            return

        income = int(self.screen.calc_gross_income("yearly", ["all"]))
        income_limit = self._income_limit()
        if income <= income_limit:
            e.condition(True, messages.income(income, income_limit))
            return

        # Foster care qualifies the foster child only, not their siblings.
        for member_eligibility in e.eligible_members:
            if member_eligibility.member.relationship != "fosterChild":
                member_eligibility.condition(False)

        if not any(member_eligibility.eligible for member_eligibility in e.eligible_members):
            e.condition(False, messages.income(income, income_limit))

    def _income_limit(self) -> int:
        """185% of the poverty guideline, rounded up. Integer math, as 1.85 * 15,960 floats above 29,526."""
        guideline = int(self.program.year.get_limit(self.screen.household_size))

        return -(-guideline * self.income_limit_percent // 100)

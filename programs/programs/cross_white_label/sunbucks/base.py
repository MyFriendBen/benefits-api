"""SUN Bucks (Summer EBT) — MFB federal base."""

from datetime import date
from typing import ClassVar, Optional

import programs.framework.eligibility_messages as messages
from programs.framework.base import Eligibility, MemberEligibility, ProgramCalculator
from programs.framework.pe_dependencies.receipt import screen_reports_snap, screen_reports_tanf
from screener.models import HouseholdMember

# What a state can enroll a child through automatically, with no application.
SNAP = "snap"
TANF = "tanf"
FOSTER_CHILD = "foster_child"


class SunBucks(ProgramCalculator, abstract=True):
    """
    Federal SUN Bucks (Summer EBT, 7 CFR part 292), computed in our own code: a one-time summer
    grocery benefit for each school-age child.

    A school-age child is eligible when one of these holds:

    - the household receives SNAP or TANF, or reports school meals or Head Start
    - the child is a foster child
    - household income is at or below 185% of the poverty line

    A child the state enrolls automatically, with no application, is not shown the program:
    they get it without doing anything. Federal rule makes the state enroll every school-age
    child in a SNAP household this way, so the base holds SNAP. TANF and foster children are
    enrolled automatically only where the state has the data, so each state adds those its own
    sources confirm. School meals and Head Start never hide the program: only an individually
    certified child is enrolled automatically, and the screener can't tell one from a child
    eating free at a school that feeds everyone, or say who runs a Head Start program.

    Approximations, all from the spec's data gaps:

    - enrollment in a school meal school is not collected, so school age stands in for it, and
      it also decides which children count on the school meals route
    - school meals and Head Start are recorded for the household, so every school-age child in it qualifies
    - any child listed as a foster child qualifies, whether or not the placement is formal
    - income is the gross amount entered, not net of business costs, for the household size entered

    FDPIR, homeless, migrant and runaway children are not evaluated: the screener collects
    nothing for them.

    The value is the 48 states and DC amount, $40 a month for the three summer months. Alaska,
    Hawaii and the territories pay more, and no white label of ours is in them.

    Each state sets:

    - ``min_school_age`` and ``max_school_age``: the compulsory school ages, inclusive
    - ``school_age_window``: the first and last day a child must be school age at some point
      between. Leave it unset to test the child's age today.
    - ``enrolled_automatically``: SNAP, plus TANF or foster children where the state's own
      sources say it enrolls them with no application
    """

    min_school_age: ClassVar[int]
    max_school_age: ClassVar[int]
    school_age_window: ClassVar[Optional[tuple[date, date]]] = None
    enrolled_automatically: ClassVar[tuple[str, ...]] = (SNAP,)

    # 91 FR 17932: 185% of the poverty guideline, rounded up to the next whole dollar.
    income_limit_percent = 185
    member_amount = 40 * 3

    dependencies = [
        "age",
        "relationship",
        "household_size",
        "income_amount",
        "income_frequency",
        "income_type",
    ]

    def member_eligible(self, e: MemberEligibility) -> None:
        member = e.member
        e.condition(self._is_school_aged(member))

        # A foster child's automatic enrollment is their own, so their siblings stay.
        if FOSTER_CHILD in self.enrolled_automatically:
            e.condition(member.relationship != "fosterChild")

    def _is_school_aged(self, member: HouseholdMember) -> bool:
        """
        Within the state's compulsory school ages: today, or at some point in the state's
        window. Birth is dated to the first of the month, since the screener collects no day of
        birth. A member with no birth month is tested on their age today.
        """
        if self.school_age_window is None or member.birth_year_month is None:
            age = member.calc_age()
            return age is not None and self.min_school_age <= age <= self.max_school_age

        first_day, last_day = self.school_age_window
        return (
            HouseholdMember.age_from_date(member.birth_year_month, last_day) >= self.min_school_age
            and HouseholdMember.age_from_date(member.birth_year_month, first_day) <= self.max_school_age
        )

    def household_eligible(self, e: Eligibility) -> None:
        enrolled_through = self._household_enrolled_through()
        if enrolled_through is not None:
            e.condition(False, messages.must_not_have_benefit(enrolled_through))
            return

        if self._receives_categorical_benefit():
            e.condition(True, messages.presumed_eligibility())
            return

        income = int(self.screen.calc_gross_income("yearly", ["all"]))
        income_limit = self._income_limit()
        if income <= income_limit:
            e.condition(True, messages.income(income, income_limit))
            return

        # Foster care qualifies the foster child only, not their siblings.
        for member_eligibility in e.member_verdicts:
            if member_eligibility.member.relationship != "fosterChild":
                member_eligibility.condition(False)

        if not any(member_eligibility.eligible for member_eligibility in e.member_verdicts):
            e.condition(False, messages.income(income, income_limit))

    def _household_enrolled_through(self) -> Optional[str]:
        """The household benefit the state enrolls its children through automatically, if any."""
        if SNAP in self.enrolled_automatically and screen_reports_snap(self.screen):
            return "SNAP"

        if TANF in self.enrolled_automatically and screen_reports_tanf(self.screen):
            return "TANF"

        return None

    def _receives_categorical_benefit(self) -> bool:
        """SNAP, TANF, school meals (7 CFR 292.12(d)(1)(i)(A)) or Head Start (7 CFR 292.2)."""
        return (
            screen_reports_snap(self.screen)
            or screen_reports_tanf(self.screen)
            or self.screen.has_base_benefit("nslp")
            or self.screen.has_base_benefit("head_start")
        )

    def _income_limit(self) -> int:
        """185% of the poverty guideline, rounded up. Integer math, as 1.85 * 15,960 floats above 29,526."""
        guideline = int(self.program.year.get_limit(self.screen.household_size))

        return -(-guideline * self.income_limit_percent // 100)

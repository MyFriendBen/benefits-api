"""National School Lunch Program — MFB federal base."""

from decimal import ROUND_HALF_UP, Decimal
from typing import ClassVar, Optional

import programs.framework.eligibility_messages as messages
from programs.framework.base import Eligibility, MemberEligibility, ProgramCalculator
from programs.framework.pe_dependencies.receipt import screen_reports_snap, screen_reports_tanf
from screener.models import HouseholdMember

# Meal tiers. A state adds its own (NJ's expanded income band) alongside these.
FREE = "free"
REDUCED_PRICE = "reduced_price"

# The pay frequencies the income guidelines publish a column for, and how many of each make a year.
PERIODS_PER_YEAR = {"weekly": 52, "biweekly": 26, "semimonthly": 24, "monthly": 12}


def ceil_div(numerator: int, denominator: int) -> int:
    return -(-numerator // denominator)


class NationalSchoolLunchProgram(ProgramCalculator, abstract=True):
    """
    Federal National School Lunch Program (42 U.S.C. 1758, 7 CFR parts 210 and 245), computed
    in our own code: free or reduced-price lunch for each school child. It sits beside the
    PolicyEngine ``SchoolLunch`` in ``base.py``, which the states not yet moved still use.

    A child under 21 is eligible when one of these holds:

    - household income is at or below 185% of the poverty line (free at or below 130%)
    - the household receives SNAP, TANF or Head Start, which makes every child free
    - the child is a foster child, which makes that child free and no one else

    Income is compared the way schools compare it: when every income stream is paid at the
    same weekly, biweekly, twice-monthly or monthly frequency, their sum is tested against
    that frequency's limit, the annual limit divided down and rounded up. Anything else is
    annualized and tested against the annual limit.

    Approximations, all from the spec's data gaps:

    - school enrollment and grade are not collected, so every member under 21 counts, with no
      lower age or relationship test
    - Head Start is recorded for the household, so every child in it is free
    - any child listed as a foster child is free, whether or not the placement is formal
    - SNAP counts whatever its amount, which is not collected
    - income is the gross amount entered, for the household size entered

    FDPIR, homeless, migrant and runaway children, Head Start-equivalent pre-K and schools
    serving every child free meals are not evaluated: the screener collects nothing for them.

    The value is a lunch every school day at the federal reimbursement for the child's tier,
    section 4 plus section 11, at the 48 states and DC rates. Alaska, Hawaii and the
    territories pay more, and no white label of ours is in them.

    Each state sets ``school_days``, its minimum school year. A state with its own route or
    payments overrides ``_state_tier`` and ``lunch_rate``.

    The spec is ``programs/cross_white_label/nslp/base/nslp_base_spec.md`` in program-ops.
    """

    school_days: ClassVar[int]

    max_age = 20

    # 91 FR 17932: 130% and 185% of the poverty guideline, rounded up to the next whole dollar.
    free_percent = 130
    reduced_price_percent = 185

    # 91 FR 43597, SY 2026-27, contiguous states and DC.
    section_4_rate = Decimal("0.45")
    section_11_rates: ClassVar[dict[str, Decimal]] = {FREE: Decimal("4.31"), REDUCED_PRICE: Decimal("3.91")}

    dependencies = [
        "age",
        "relationship",
        "household_size",
        "income_amount",
        "income_frequency",
        "income_type",
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._tiers: dict[int, str] = {}

    def member_eligible(self, e: MemberEligibility) -> None:
        age = e.member.calc_age()
        e.condition(age is not None and age <= self.max_age)

    def household_eligible(self, e: Eligibility) -> None:
        income = int(self.screen.calc_gross_income("yearly", ["all"]))
        categorical = self._receives_categorical_benefit()
        income_tier = self._income_tier()
        admitted_on_income = False

        for member_eligibility in e.eligible_members:
            if not member_eligibility.eligible:
                continue

            member = member_eligibility.member
            # A foster child's eligibility is their own, so it never reaches their siblings.
            if categorical or member.relationship == "fosterChild":
                tier = FREE
            else:
                tier = income_tier or self._state_tier(member)
                admitted_on_income = admitted_on_income or tier is not None

            if tier is None:
                member_eligibility.condition(False)
            else:
                self._tiers[member.id] = tier

        if categorical:
            e.condition(True, messages.presumed_eligibility())
        elif admitted_on_income:
            e.condition(True, messages.income(income, self._widest_income_limit()))

        if not any(member_eligibility.eligible for member_eligibility in e.eligible_members):
            e.condition(False, messages.income(income, self._widest_income_limit()))

    def _state_tier(self, member: HouseholdMember) -> Optional[str]:
        """A state route for a child the federal income limits leave out. None in the base."""
        return None

    def _receives_categorical_benefit(self) -> bool:
        """SNAP or TANF (7 CFR 245.6(b)(7)), or Head Start, recorded for the household."""
        return (
            screen_reports_snap(self.screen)
            or screen_reports_tanf(self.screen)
            or self.screen.has_base_benefit("head_start")
        )

    def _income_tier(self) -> Optional[str]:
        if self._income_within(self._free_limit()):
            return FREE

        if self._income_within(self._reduced_price_limit()):
            return REDUCED_PRICE

        return None

    def _income_within(self, annual_limit: int) -> bool:
        """
        Same-frequency income against that frequency's limit, the annual limit divided down and
        rounded up; any other mix annualized against the annual limit.
        """
        streams = list(self.screen.income_streams.all())
        frequencies = {stream.frequency for stream in streams}

        if len(frequencies) == 1:
            frequency = frequencies.pop()
            if frequency in PERIODS_PER_YEAR:
                total = sum((stream.amount for stream in streams), Decimal(0))
                return total <= ceil_div(annual_limit, PERIODS_PER_YEAR[frequency])

        return self.screen.calc_gross_income("yearly", ["all"]) <= annual_limit

    def _poverty_percent(self, percent: int) -> int:
        """``percent`` of the poverty guideline, rounded up. Integer math, so 1.85 never floats over."""
        guideline = int(self.program.year.get_limit(self.screen.household_size))

        return ceil_div(guideline * percent, 100)

    def _free_limit(self) -> int:
        return self._poverty_percent(self.free_percent)

    def _reduced_price_limit(self) -> int:
        return self._poverty_percent(self.reduced_price_percent)

    def _widest_income_limit(self) -> int:
        """The highest income any route admits, for the message when every route fails."""
        return self._reduced_price_limit()

    def lunch_rate(self, member: HouseholdMember, tier: str) -> Decimal:
        """What one lunch is worth at this tier: the federal section 4 and section 11 payments."""
        return self.section_4_rate + self.section_11_rates[tier]

    def member_value(self, member: HouseholdMember) -> int:
        annual = self.lunch_rate(member, self._tiers[member.id]) * self.school_days

        return int(annual.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

"""Supplemental Nutrition Assistance Program — MFB federal base."""

from decimal import Decimal
from functools import cached_property
from math import ceil
from typing import ClassVar, Optional

import programs.framework.eligibility_messages as messages
from programs.framework.base import Eligibility, ProgramCalculator
from programs.framework.pe_dependencies.member import SSDI_INCOME_TYPE
from programs.framework.pe_dependencies.receipt import SSI_INCOME_TYPE, screen_reports_tanf
from programs.programs.shared.income import table_income_limit
from screener.models import HouseholdMember, IncomeStream

MONTHS_PER_YEAR = 12
# The screener's weeks-per-month factor, as an exact Decimal.
WEEKS_PER_MONTH = Decimal("4.35")

ELDERLY_AGE = 60
# The age bounds of the student rule: under 18 or 50 and over is excused.
STUDENT_MIN_AGE = 18
STUDENT_MAX_AGE = 50
# A parent of a child under 6 is excused from the student rule; a single parent, under 12.
YOUNG_CHILD_AGE = 6
SINGLE_PARENT_CHILD_AGE = 12
# Income streams that make a member "elderly or disabled" besides age and the disability flags.
DISABILITY_INCOME_TYPES = [SSI_INCOME_TYPE, SSDI_INCOME_TYPE]
PARTNER_RELATIONSHIPS = ("spouse", "domesticPartner")
HOUSEHOLD_ADULT_RELATIONSHIPS = ("headOfHousehold", *PARTNER_RELATIONSHIPS)

# Everything below is the 48 contiguous states and DC, 2026-10-01 through 2027-09-30.
GROSS_INCOME_LIMITS = {1: 1729, 2: 2345, 3: 2960, 4: 3575, 5: 4191, 6: 4806, 7: 5421, 8: 6037}
GROSS_INCOME_LIMIT_PER_ADDITIONAL = 616
NET_INCOME_LIMITS = {1: 1330, 2: 1804, 3: 2277, 4: 2750, 5: 3224, 6: 3697, 7: 4170, 8: 4644}
NET_INCOME_LIMIT_PER_ADDITIONAL = 474
MAX_ALLOTMENTS = {1: 306, 2: 562, 3: 808, 4: 1023, 5: 1217, 6: 1463, 7: 1616, 8: 1841}
MAX_ALLOTMENT_PER_ADDITIONAL = 225
MAX_ALLOTMENT_LARGEST = 3887
LARGEST_HOUSEHOLD = 18
STANDARD_DEDUCTION_MINIMUM = 217
STANDARD_DEDUCTION_SHARE = Decimal("0.0831")
STANDARD_DEDUCTION_MAX_SIZE = 6
EARNED_INCOME_DEDUCTION = Decimal("0.2")
EXCESS_MEDICAL_THRESHOLD = 35
SHELTER_CAP = 769
SHELTER_INCOME_SHARE = Decimal("0.5")
RESOURCE_LIMIT = 3_000
RESOURCE_LIMIT_ELDERLY_DISABLED = 4_750
NET_INCOME_SHARE = Decimal("0.3")
MINIMUM_BENEFIT = 25
MINIMUM_BENEFIT_MAX_SIZE = 2
ALLOTMENT_REQUIRED_FROM_SIZE = 3


def money(amount: float) -> Decimal:
    """A screener amount as a Decimal, via its repr so a float sum keeps its cents."""
    return Decimal(str(amount))


def gross_income_limit(household_size: int) -> int:
    """Monthly gross income limit, 130% of poverty."""
    return table_income_limit(GROSS_INCOME_LIMITS, household_size, GROSS_INCOME_LIMIT_PER_ADDITIONAL)


def net_income_limit(household_size: int) -> int:
    """Monthly net income limit, 100% of poverty."""
    return table_income_limit(NET_INCOME_LIMITS, household_size, NET_INCOME_LIMIT_PER_ADDITIONAL)


def max_allotment(household_size: int) -> int:
    """Maximum monthly allotment."""
    if household_size >= LARGEST_HOUSEHOLD:
        return MAX_ALLOTMENT_LARGEST

    return table_income_limit(MAX_ALLOTMENTS, household_size, MAX_ALLOTMENT_PER_ADDITIONAL)


def standard_deduction(household_size: int) -> int:
    """The larger of the minimum and 8.31% of the net limit for min(size, 6), rounded up."""
    share = STANDARD_DEDUCTION_SHARE * net_income_limit(min(household_size, STANDARD_DEDUCTION_MAX_SIZE))

    return max(STANDARD_DEDUCTION_MINIMUM, ceil(share))


class MfbSnap(ProgramCalculator, abstract=True):
    """
    Federal Supplemental Nutrition Assistance Program (7 U.S.C. 2011 et seq.), computed in our
    own code. It sits beside the PolicyEngine ``Snap`` in ``base.py``, which the states not yet
    moved still use (MFB-1940).

    A household is eligible by one of two routes:

    - categorical: it reports TANF (the tile or cash assistance) or SSI, and with three or more
      people its allotment is above zero
    - the income and resource tests: gross income within 130% of poverty (skipped when someone is
      60 or older or disabled), net income within 100% of poverty, and resources within 3,000
      dollars (4,750 when someone is 60 or older or disabled)

    A full-time student who meets no exception is left out: their income is not counted and they
    are not counted in household size. The rest of the household can still receive.

    Residency is the white label's job and immigration status is enforced by the Program row's
    ``legal_status_required``, so neither is checked here.

    Approximations, all from the spec's data gaps:

    - every listed member is assumed to buy and prepare food with the household, and none is a
      boarder, institution resident, or a person the work, SSN, felony, strike or program-violation
      rules would leave out
    - income is counted as entered, with no exclusions (education aid, K-12 earnings, energy
      assistance, irregular income), and no sponsor is deemed
    - every reported ``childSupport`` expense is subtracted, as if legally owed to a non-member
    - every reported ``childCare``, ``dependentCare`` and ``medical`` amount is deducted
    - only liquid resources are counted; no household is treated as homeless
    - the first month is not prorated

    A state may set ``utility_allowance`` (its standard, where it requires one), or override
    ``utility_costs`` when its rule is more than a flat amount; extend the categorical route by
    overriding ``categorically_eligible``; round the net income inputs by overriding
    ``round_amount``; and adjust the federal allotment by overriding ``state_allotment``.
    Everything else is federal.

    The value is the monthly allotment made annual, and never less than 1 dollar for an eligible
    household so the results page keeps it.

    The spec is ``programs/cross_white_label/snap/base/snap_base_spec.md`` in program-ops.
    """

    #: The state's standard utility allowance, monthly, where the state requires it. None where
    #: the household's actual utility bills count instead.
    utility_allowance: ClassVar[Optional[int]] = None

    dependencies = [
        "household_size",
        "household_assets",
        "age",
        "relationship",
        "student",
        "disabled",
        "visually_impaired",
        "long_term_disability",
        "income_type",
        "income_amount",
        "income_frequency",
        "expense_type",
        "expense_amount",
        "expense_frequency",
    ]

    def household_eligible(self, e: Eligibility) -> None:
        size = self.household_size
        if size < 1:
            # Every member is an ineligible student: nobody is left to receive.
            e.condition(False)
            return

        if self.categorically_eligible() and (size < ALLOTMENT_REQUIRED_FROM_SIZE or self.allotment() > 0):
            e.condition(True, messages.presumed_eligibility())
            return

        if not self.has_elderly_or_disabled_member:
            gross = self.countable_income
            limit = gross_income_limit(size)
            e.condition(gross <= limit, messages.income(gross * MONTHS_PER_YEAR, limit * MONTHS_PER_YEAR))

        net = self.net_income
        net_limit = net_income_limit(size)
        e.condition(net <= net_limit, messages.income(net * MONTHS_PER_YEAR, net_limit * MONTHS_PER_YEAR))

        assets = self.screen.household_assets
        asset_limit = RESOURCE_LIMIT_ELDERLY_DISABLED if self.has_elderly_or_disabled_member else RESOURCE_LIMIT
        e.condition(assets <= asset_limit, messages.assets(asset_limit))

    def categorically_eligible(self) -> bool:
        """Receives TANF-funded benefits or SSI. A state adds its own qualifying assistance here."""
        return screen_reports_tanf(self.screen) or self.counted_yearly_income([SSI_INCOME_TYPE]) > 0

    def household_value(self) -> int:
        return max(1, self.allotment() * MONTHS_PER_YEAR)

    def allotment(self) -> int:
        """Monthly allotment: the maximum less 30% of net income (rounded up), or the minimum benefit."""
        return self.state_allotment(self.federal_allotment())

    def federal_allotment(self) -> int:
        size = self.household_size
        reduction = ceil(NET_INCOME_SHARE * self.net_income)
        floor = MINIMUM_BENEFIT if size <= MINIMUM_BENEFIT_MAX_SIZE else 0

        return max(max_allotment(size) - reduction, floor)

    def state_allotment(self, federal_allotment: int) -> int:
        """The allotment after any state supplement. The federal amount where the state adds none."""
        return federal_allotment

    def round_amount(self, amount: Decimal) -> Decimal:
        """How a state rounds each income amount and each deduction. The federal base does not."""
        return amount

    # ----- household composition -----

    @cached_property
    def members(self) -> list[HouseholdMember]:
        return list(self.screen.household_members.all())

    @cached_property
    def ineligible_students(self) -> list[HouseholdMember]:
        return [member for member in self.members if self.is_ineligible_student(member)]

    @cached_property
    def counted_members(self) -> list[HouseholdMember]:
        left_out = {member.id for member in self.ineligible_students}

        return [member for member in self.members if member.id not in left_out]

    @cached_property
    def household_size(self) -> int:
        """The screener's household size, less the students the rule leaves out."""
        return self.screen.household_size - len(self.ineligible_students)

    @cached_property
    def has_elderly_or_disabled_member(self) -> bool:
        """Someone 60 or older, disabled, or reporting SSI or Social Security disability."""
        for member in self.counted_members:
            age = member.calc_age()
            if (age is not None and age >= ELDERLY_AGE) or member.has_disability():
                return True

        return self.counted_yearly_income(DISABILITY_INCOME_TYPES) > 0

    def counted_yearly_income(self, types: list[str]) -> float:
        """Yearly income of the given types for the members who are counted (not excluded students)."""
        return sum(member.calc_gross_income("yearly", types) for member in self.counted_members)

    def is_ineligible_student(self, member: HouseholdMember) -> bool:
        """A full-time student who meets none of the exceptions to the student rule."""
        if member.student is not True or member.student_full_time is not True:
            return False

        age = member.calc_age()
        if age is not None and (age < STUDENT_MIN_AGE or age >= STUDENT_MAX_AGE):
            return False

        if member.has_disability():
            return False

        if member.student_works_20_plus_hrs is True or member.student_has_work_study is True:
            return False

        if member.student_job_training_program is True:
            return False

        if screen_reports_tanf(self.screen):
            return False

        return not self.is_student_parent_of_young_child(member)

    def is_student_parent_of_young_child(self, member: HouseholdMember) -> bool:
        """A head, spouse or partner with a child under 6, or a head with no partner and a child under 12."""
        if member.relationship not in HOUSEHOLD_ADULT_RELATIONSHIPS:
            return False

        if self.has_child_under(YOUNG_CHILD_AGE):
            return True

        has_partner = any(other.relationship in PARTNER_RELATIONSHIPS for other in self.members)

        return (
            member.relationship == "headOfHousehold"
            and not has_partner
            and self.has_child_under(SINGLE_PARENT_CHILD_AGE)
        )

    def has_child_under(self, age_limit: int) -> bool:
        for member in self.members:
            age = member.calc_age()
            if member.relationship == "child" and age is not None and age < age_limit:
                return True

        return False

    # ----- income and deductions, all monthly -----

    def income(self, types: list[str]) -> Decimal:
        """Monthly income of the members who are counted, of the given types."""
        return sum((money(member.calc_gross_income("monthly", types)) for member in self.counted_members), Decimal(0))

    def rounded_income(self, types: list[str]) -> Decimal:
        """Like ``income``, with each income stream rounded by the state's ``round_amount``."""
        total = Decimal(0)
        for member in self.counted_members:
            for stream in member.income_streams.all():
                if "all" in types or stream.type in types:
                    total += self.round_amount(self.monthly_amount(stream))

        return total

    @staticmethod
    def monthly_amount(stream: IncomeStream) -> Decimal:
        """
        A stream's monthly amount as an exact Decimal. ``IncomeStream.monthly`` builds its weekly
        factor from the float 4.35, which is slightly under 4.35, so a weekly 250 comes out at
        1,087.4999… and a round-half-up state rounds it down. The factors here are exact.
        """
        amount = stream.amount
        if stream.frequency == "weekly":
            return amount * WEEKS_PER_MONTH
        if stream.frequency == "biweekly":
            return amount * WEEKS_PER_MONTH / 2
        if stream.frequency == "hourly":
            return amount * stream.hours_worked * WEEKS_PER_MONTH

        return money(stream.monthly())

    def expenses(self, types: list[str]) -> Decimal:
        return money(self.screen.calc_expenses("monthly", types))

    @cached_property
    def countable_income(self) -> Decimal:
        """All income, less child support paid out."""
        return self.income(["all"]) - self.expenses(["childSupport"])

    @cached_property
    def net_income(self) -> Decimal:
        """Countable income after the earned income, standard, dependent care, medical and shelter deductions."""
        income = self.rounded_income(["all"]) - self.expenses(["childSupport"])
        earned = self.rounded_income(["wages", "selfEmployment", "boarder"])
        adjusted = income - self.round_amount(EARNED_INCOME_DEDUCTION * earned)
        adjusted -= standard_deduction(self.household_size)
        adjusted -= self.round_amount(self.expenses(["childCare", "dependentCare"]))
        adjusted -= self.round_amount(self.excess_medical_deduction())
        adjusted -= self.excess_shelter_deduction(adjusted)

        return max(Decimal(0), adjusted)

    def excess_medical_deduction(self) -> Decimal:
        if not self.has_elderly_or_disabled_member:
            return Decimal(0)

        return max(Decimal(0), self.expenses(["medical"]) - EXCESS_MEDICAL_THRESHOLD)

    def utility_costs(self) -> Decimal:
        """Monthly utility costs in the shelter total: the state's standard allowance, or actual bills."""
        if self.utility_allowance is not None:
            return Decimal(self.utility_allowance)

        return self.expenses(["heating", "cooling", "telephone", "otherUtilities"])

    def excess_shelter_deduction(self, income_after_other_deductions: Decimal) -> Decimal:
        shelter = self.expenses(["rent", "mortgage", "propertyTax", "hoa", "homeownersInsurance"])
        shelter += self.utility_costs()

        excess = max(Decimal(0), shelter - SHELTER_INCOME_SHARE * income_after_other_deductions)
        excess = self.round_amount(excess)

        return excess if self.has_elderly_or_disabled_member else min(excess, Decimal(SHELTER_CAP))

"""CHIP — MFB federal base.

Sits beside the PolicyEngine ``Chip`` in ``base.py``, which MassHealth (``ma.py``) and the
framework tests still read for its PolicyEngine inputs. The states not yet moved here keep
their own calculators.

Rules: program-ops ``programs/cross_white_label/medicaid/chip/base/chip_base_spec.md``.
"""

from decimal import ROUND_HALF_UP, Decimal
from functools import cached_property
from typing import ClassVar, Literal, Optional

from programs.framework.base import MemberEligibility, ProgramCalculator
from screener.models import HouseholdMember

#: Income types MAGI leaves out, by the screener's names (spec `child_income_band`): child
#: support received, SSI, workers' compensation, VA benefits, TANF and other need-based cash
#: aid, and gifts. Military retirement is reported under `pension` and counts.
MAGI_EXCLUDED_INCOME_TYPES = (
    "childSupport",
    "sSI",
    "workersComp",
    "veteran",
    "cashAssistance",
    "cashAssistanceOther",
    "gifts",
)

#: The 5-point disregard (42 CFR 435.603(d)(4)), in percent of the poverty line.
DISREGARD = 5

#: The poverty tables the spec defines. `program.year` carries the 48-state table only, so a
#: state on another one can't be built until that table exists.
SUPPORTED_POVERTY_TABLES = ("48-state",)

PregnantCount = Literal["1", "2", "herself_plus_expected"]


def round_half_up(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


class MfbChipCommon(ProgramCalculator, abstract=True):
    """
    What every CHIP route shares: MAGI-style countable income, the member's family size, its
    percent of the poverty line, and the Medicaid and other-coverage bars.

    Each state sets:

    - ``poverty_guideline_table``: the poverty table that applies in the state. Only
      ``"48-state"`` is supported, since ``program.year`` holds no other.
    - ``pregnant_member_count_for_others``: how a pregnant member counts in the other members'
      family size (42 CFR 435.603(b)): ``"1"``, ``"2"`` or ``"herself_plus_expected"``.
    - ``state_magi_excluded_income_types``: the state's own income types MAGI leaves out.
    - ``other_coverage_types``: the insurance answers that bar a member. The base's are
      employer and private coverage.

    A pregnant member's own expected child always counts in her own family size. The
    screener records whether someone is pregnant but not how many children she expects, so
    each pregnancy adds one, and a blank answer counts as not pregnant.
    """

    poverty_guideline_table: ClassVar[str]
    pregnant_member_count_for_others: ClassVar[PregnantCount]
    state_magi_excluded_income_types: ClassVar[tuple[str, ...]] = ()
    other_coverage_types: ClassVar[tuple[str, ...]] = ("employer", "private")

    # Not `pregnant`: a blank answer reads as not pregnant (spec `child_income_band`), so
    # requiring it would drop the program for a household that left it blank.
    dependencies = ("age", "household_size", "income_type", "income_amount", "income_frequency", "insurance")

    def __init_subclass__(cls, abstract: bool = False, **kwargs) -> None:
        super().__init_subclass__(abstract=abstract, **kwargs)
        if abstract:
            return

        # A state that leaves a constant out fails at import, not on the first screen.
        if getattr(cls, "poverty_guideline_table", None) not in SUPPORTED_POVERTY_TABLES:
            raise TypeError(f"{cls.__name__}.poverty_guideline_table must be one of {SUPPORTED_POVERTY_TABLES}")
        if getattr(cls, "pregnant_member_count_for_others", None) not in ("1", "2", "herself_plus_expected"):
            raise TypeError(f"{cls.__name__}.pregnant_member_count_for_others is not set")

    # Income

    @cached_property
    def countable_income(self) -> Decimal:
        exclude = MAGI_EXCLUDED_INCOME_TYPES + tuple(self.state_magi_excluded_income_types)
        return Decimal(str(self.screen.calc_gross_income("yearly", ["all"], exclude=exclude)))

    @cached_property
    def _members(self) -> list[HouseholdMember]:
        return list(self.screen.household_members.all())

    def family_size(self, member: HouseholdMember) -> int:
        """
        `household_size`, plus one for the member's own expected child, plus what each other
        pregnant member adds under the state's election.
        """
        own = 1 if member.pregnant is True else 0
        others = sum(1 for m in self._members if m.id != member.id and m.pregnant is True)
        per_other = 0 if self.pregnant_member_count_for_others == "1" else 1

        return self.screen.household_size + own + others * per_other

    def above_disregard(self, member: HouseholdMember, limit_fpl: int) -> bool:
        """Whether income less the 5-point disregard is above `limit_fpl`% of the poverty line."""
        return self._percent_of_poverty(member) - DISREGARD > limit_fpl

    def within(self, member: HouseholdMember, limit_fpl: int) -> bool:
        """Whether income less the 5-point disregard is at or below `limit_fpl`%."""
        return self._percent_of_poverty(member) - DISREGARD <= limit_fpl

    def _percent_of_poverty(self, member: HouseholdMember) -> Decimal:
        poverty_line = Decimal(self.program.year.get_limit(self.family_size(member)))
        return 100 * self.countable_income / poverty_line

    # Coverage

    def not_enrolled_in_medicaid(self, member: HouseholdMember) -> bool:
        return not member.has_insurance_types(("medicaid",))

    def no_other_coverage(self, member: HouseholdMember) -> bool:
        return not member.has_insurance_types(self.other_coverage_types)


class MfbChip(MfbChipCommon, abstract=True):
    """
    CHIP for a targeted low-income child, and, where the state elects it, a targeted
    low-income pregnant woman. A member qualifies through either route:

    - **child:** under 19, not on Medicaid, no other coverage, and income above Medicaid's
      limit for their age (for a pregnant child, the higher of that and the pregnancy limit)
      and at or below the CHIP limit
    - **pregnant woman:** pregnant, not on Medicaid, no other coverage, and income above
      Medicaid's pregnancy limit (for one under 19, the higher of that and her age's limit)
      and at or below the CHIP limit

    The unborn-child (FCEP) route is ``MfbChipFcep``, a separate program, because its
    any-status rule can't share a ``legal_status_required`` with these. Residency is the
    white label's and immigration status is the program record's. Data gaps (spec section 5):
    MAGI income and tax households are approximated; incarceration, IMD stays, public-employee
    coverage, postpartum women, deemed newborns, non-MAGI Medicaid and limited-benefit plans
    are not evaluated.

    Value: the state's per-child monthly estimate, children's route only. The pregnancy route
    has no estimate, so a member eligible only through it is valued at 0, and a household
    eligible only that way isn't shown until results can say "no estimate".

    Each state sets, besides ``MfbChipCommon``'s:

    - ``chip_income_limit_fpl``
    - ``medicaid_child_income_limit_under_1_fpl``, ``medicaid_child_income_limit_1_to_5_fpl``
      and ``medicaid_child_income_limit_6_to_18_fpl``
    - ``pregnant_women_option`` and ``medicaid_pregnancy_income_limit_fpl``
    - either the two section 7 inputs (``separate_chip_benefit_spending`` and
      ``separate_chip_average_monthly_enrollment``), or its own ``child_monthly_value``
    - ``child_route_other_coverage_types``: coverage that bars the children's route only

    Every limit is the published standard before the 5-point disregard.
    """

    max_child_age = 19

    chip_income_limit_fpl: ClassVar[int]
    medicaid_child_income_limit_under_1_fpl: ClassVar[int]
    medicaid_child_income_limit_1_to_5_fpl: ClassVar[int]
    medicaid_child_income_limit_6_to_18_fpl: ClassVar[int]
    pregnant_women_option: ClassVar[bool]
    medicaid_pregnancy_income_limit_fpl: ClassVar[int]
    child_route_other_coverage_types: ClassVar[tuple[str, ...]] = ()

    #: Section 7's inputs: FFY 2024 separate-CHIP benefit spending, in dollars, and its
    #: average monthly enrollment. A state that values children another way overrides
    #: `child_monthly_value` instead.
    separate_chip_benefit_spending: ClassVar[Optional[int]] = None
    separate_chip_average_monthly_enrollment: ClassVar[Optional[int]] = None

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._child_route: set[int] = set()

    def member_eligible(self, e: MemberEligibility) -> None:
        member = e.member
        child = self.child_route(member)
        if child:
            self._child_route.add(member.id)

        e.condition(child or self.pregnant_route(member))

    # Children's route

    def child_route(self, member: HouseholdMember) -> bool:
        age = member.calc_age()
        if age is None or age >= self.max_child_age:
            return False

        return (
            self.not_enrolled_in_medicaid(member)
            and self.no_other_coverage(member)
            and not member.has_insurance_types(self.child_route_other_coverage_types)
            and self.above_disregard(member, self.child_medicaid_limit(member, age))
            and self.within(member, self.chip_income_limit_fpl)
        )

    def medicaid_limit_for_age(self, age: int) -> int:
        if age < 1:
            return self.medicaid_child_income_limit_under_1_fpl
        if age < 6:
            return self.medicaid_child_income_limit_1_to_5_fpl
        return self.medicaid_child_income_limit_6_to_18_fpl

    def child_medicaid_limit(self, member: HouseholdMember, age: int) -> int:
        limit = self.medicaid_limit_for_age(age)
        if member.pregnant is True:
            return max(limit, self.medicaid_pregnancy_income_limit_fpl)
        return limit

    # Pregnant woman's route

    def pregnant_route(self, member: HouseholdMember) -> bool:
        if not self.pregnant_women_option or member.pregnant is not True:
            return False

        return (
            self.not_enrolled_in_medicaid(member)
            and self.no_other_coverage(member)
            and self.above_disregard(member, self.pregnant_medicaid_limit(member))
            and self.within(member, self.pregnant_income_limit_fpl)
        )

    @property
    def pregnant_income_limit_fpl(self) -> int:
        """The pregnancy route's ceiling, the children's CHIP limit unless a state sets lower."""
        return self.chip_income_limit_fpl

    def pregnant_medicaid_limit(self, member: HouseholdMember) -> int:
        age = member.calc_age()
        if age is not None and age < self.max_child_age:
            return max(self.medicaid_pregnancy_income_limit_fpl, self.medicaid_limit_for_age(age))
        return self.medicaid_pregnancy_income_limit_fpl

    # Value

    def member_value(self, member: HouseholdMember) -> int:
        if member.id not in self._child_route:
            return 0

        return self.child_monthly_value(member) * 12

    def child_monthly_value(self, member: HouseholdMember) -> int:
        """Section 7: benefit spending per average enrollee, per month."""
        if self.separate_chip_benefit_spending is None or self.separate_chip_average_monthly_enrollment is None:
            raise NotImplementedError(f"{type(self).__name__} sets no section 7 inputs and no child_monthly_value")

        spending = Decimal(self.separate_chip_benefit_spending)
        return round_half_up(spending / Decimal(self.separate_chip_average_monthly_enrollment) / 12)


class MfbChipFcep(MfbChipCommon, abstract=True):
    """
    CHIP's from-conception-to-end-of-pregnancy (FCEP) option: an unborn child, through a
    pregnant mother of any immigration status who is not on Medicaid, has no other coverage,
    and whose income less the 5-point disregard is at or below the state's FCEP limit.

    Its own program, so its ``legal_status_required`` can admit every status without
    reaching the children's and pregnant-woman routes (``MfbChip``). Not evaluated: whether
    the mother qualifies for other Medicaid or CHIP coverage, MAGI income and tax households.
    No state elects it yet, and section 7 gives it no value.

    Each state sets ``fcep_income_limit_fpl``, besides ``MfbChipCommon``'s.
    """

    fcep_income_limit_fpl: ClassVar[int]

    def member_eligible(self, e: MemberEligibility) -> None:
        member = e.member
        e.condition(
            member.pregnant is True
            and self.not_enrolled_in_medicaid(member)
            and self.no_other_coverage(member)
            and self.within(member, self.fcep_income_limit_fpl)
        )

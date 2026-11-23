from screener.models import Screen, HouseholdMember
import re
from typing import List, Optional

#: The period shapes PolicyEngine accepts, and the only two `period_for` produces: a bare
#: year for an annual variable, ``YYYY-MM`` for a monthly one.
_PERIOD_PATTERN = re.compile(r"^(\d{4})(?:-(0[1-9]|1[0-2]))?$")


class PolicyEngineScreenInput:
    """
    Base class for all Policy Engine dependencies
    """

    unit = ""
    sub_unit = ""
    field = ""
    dependencies = tuple()

    # PolicyEngine package-version window (major, minor, patch tuples) in which this
    # variable exists, so pe_input() never sends a variable to a model that doesn't
    # define it (which would 400 the whole request). Both bounds are optional:
    #   min_pe_version  - first version that defines it; () = no floor (always existed)
    #   max_pe_version  - last version that still defines it; () = no ceiling (current)
    # Examples:
    #   new variable (added 1.715.2):     min_pe_version = (1, 715, 2)
    #   removed variable (dropped after X): max_pe_version = (last version that had it)
    #   windowed variable (existed A..B):  min_pe_version = A; max_pe_version = B
    #
    # Scope: this gates whether a variable is SENT (add/remove across versions). It does
    # NOT handle a variable whose accepted value/format changes per version (e.g.
    # county_str -> county_fips); value() has no access to the resolved version today.
    # Design that against the first real value-changing migration (MFB-1104).
    min_pe_version: tuple = ()
    max_pe_version: tuple = ()

    #: The period this variable is being sent at, as PolicyEngine spells it: ``YYYY`` for an
    #: annual variable, ``YYYY-MM`` for a monthly one. `pe_input` resolves it per variable
    #: (see `PolicyEngineCalulator.period_for`) and passes it in, so `value` can return a
    #: value that depends on the period it is being asked about -- an age, for instance, is
    #: only meaningful relative to a period. None when a caller constructs the dependency
    #: outside payload assembly; `value` implementations that read it must handle that.
    period: Optional[str] = None

    def __init__(
        self,
        screen: Screen,
        members: List[HouseholdMember],
        relationship_map,
        period: Optional[str] = None,
    ):
        self.screen = screen
        self.members = members
        self.relationship_map = relationship_map
        self.period = period

    @property
    def period_year(self) -> Optional[int]:
        """The calendar year of `period`, or None when there is no usable period.

        Accepts only the two shapes `PolicyEngineCalulator.period_for` produces -- ``YYYY``
        annual and ``YYYY-MM`` monthly, month 01 through 12 -- and returns None for anything
        else. Reading the leading digits of whatever it was handed would turn a malformed
        period into a confidently wrong year (``"20260"`` becomes year 20260, and an age
        computed from it), where None sends a dependency to whatever it does without a
        period. A malformed period is also the payload's period key, so such a request is
        already doomed; this only keeps it from being doomed *and* nonsensical.

        Returns None rather than raising, because the payload-shape tests pass a calculator
        class whose `pe_period` is an unevaluated property object. A dependency that cannot
        resolve a year should fall back, not break payload assembly.
        """
        if self.period is None:
            return None

        match = _PERIOD_PATTERN.match(str(self.period))

        return int(match.group(1)) if match else None

    def value(self) -> object:
        """
        Return the value to send to Policy Engine
        """
        return None


class Household(PolicyEngineScreenInput):
    """
    Base class for all household unit Policy Engine dependencies
    """

    unit = "households"
    sub_unit = "household"


class TaxUnit(PolicyEngineScreenInput):
    """
    Base class for all tax unit Policy Engine dependencies
    """

    unit = "tax_units"


class SpmUnit(PolicyEngineScreenInput):
    """
    Base class for all spm unit Policy Engine dependencies
    """

    unit = "spm_units"
    sub_unit = "spm_unit"


class Member(PolicyEngineScreenInput):
    """
    Base class for all member unit Policy Engine dependencies
    """

    unit = "people"

    def __init__(
        self,
        screen: Screen,
        member: HouseholdMember,
        relationship_map,
        period: Optional[str] = None,
    ):
        self.screen = screen
        self.member = member
        self.relationship_map = relationship_map
        self.period = period


class ConflictingDependencyError(Exception):
    """Two dependencies wrote different values to one PolicyEngine payload slot.

    Named apart from `programs.util.DependencyError` on purpose. That one means "a screen is
    missing a field this program needs" and takes no arguments; this one means "two programs
    disagree about what to send" and takes four. They used to share a name across one call
    graph, so the catch site in ``screener.views`` imported the missing-dependency class and
    this one propagated uncaught, taking down every program's results over one program's
    disagreement.

    Payload assembly now partitions disagreeing programs into separate requests before any
    value is written, so a raise from here means the partition itself is wrong rather than
    that two programs disagree. `calc_pe_eligibility` still catches it as a backstop.
    """

    def __init__(self, field, value_1, value_2, period=None, member=None) -> None:
        self.field = field
        self.value_1 = value_1
        self.value_2 = value_2
        self.period = period
        self.member = member

        where = f"{field} at {period}" if period is not None else field
        if member is not None:
            where = f"{where} for member {member}"

        super().__init__(f"Conflicting Policy Engine dependencies in {where}: {value_1} and {value_2}")

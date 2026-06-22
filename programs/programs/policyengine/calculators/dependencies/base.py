from screener.models import Screen, HouseholdMember
from typing import List


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

    def __init__(self, screen: Screen, members: List[HouseholdMember], relationship_map) -> None:
        self.screen = screen
        self.members = members
        self.relationship_map = relationship_map

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

    def __init__(self, screen: Screen, member: HouseholdMember, relationship_map) -> None:
        self.screen = screen
        self.member = member
        self.relationship_map = relationship_map


class DependencyError(Exception):
    """
    Dependency conflict error
    """

    def __init__(self, field, value_1, value_2) -> None:
        super().__init__(f"Confilcting Policy Engine Dependencies in {field}: {value_1} and {value_2}")

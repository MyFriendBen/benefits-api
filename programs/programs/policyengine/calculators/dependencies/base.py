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

    def __init__(self, screen: Screen, members: List[HouseholdMember], relationship_map):
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

    def __init__(self, screen: Screen, member: HouseholdMember, relationship_map):
        self.screen = screen
        self.member = member
        self.relationship_map = relationship_map


class DependencyError(Exception):
    """
    Dependency conflict error
    """

    def __init__(self, field, value_1, value_2) -> None:
        super().__init__(f"Confilcting Policy Engine Dependencies in {field}: {value_1} and {value_2}")

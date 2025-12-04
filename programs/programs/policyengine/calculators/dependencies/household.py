from .base import Household
import re
from typing import ClassVar, Optional, Type


class StateCode(Household):
    field = "state_code"

    state = ""

    def value(self):
        return self.state


class CoStateCodeDependency(StateCode):
    state = "CO"


class NcStateCodeDependency(StateCode):
    state = "NC"


class MaStateCodeDependency(StateCode):
    state = "MA"


class IlStateCodeDependency(StateCode):
    state = "IL"


class TxStateCodeDependency(StateCode):
    state = "TX"


class CountyDependency(Household):
    field: ClassVar[str] = "county_str"
    dependencies: ClassVar[list[str]] = ["county"]
    state_dependency_class: ClassVar[Optional[Type]] = None  # Override in subclasses

    def value(self):
        if self.state_dependency_class is None:
            raise ValueError(f"{self.__class__.__name__} must define state_dependency_class")

        if not self.screen.county:
            raise ValueError("county missing")

        state_code = self.state_dependency_class.state
        county_str = self.screen.county.strip()

        # Robust county normalization: remove non-alphanumeric except spaces,
        # normalize whitespace to single underscores, then uppercase
        county_token = re.sub(r"[^\w\s]", "", county_str)  # Remove non-alphanumeric except spaces
        county_token = re.sub(r"\s+", "_", county_token.strip())  # Replace whitespace with underscores
        county_token = county_token.upper()  # Uppercase

        return f"{county_token}_{state_code}"


class NcCountyDependency(CountyDependency):
    state_dependency_class = NcStateCodeDependency


class IlCountyDependency(CountyDependency):
    state_dependency_class = IlStateCodeDependency


class ZipCodeDependency(Household):
    field = "zip_code"
    dependencies = ["zipcode"]

    def value(self):
        return self.screen.zipcode


class IsInPublicHousingDependency(Household):
    field = "is_in_public_housing"

    def value(self):
        return self.screen.has_expense(["subsidizedRent"])

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


class WaStateCodeDependency(StateCode):
    state = "WA"


class KsStateCodeDependency(StateCode):
    state = "KS"


class MoStateCodeDependency(StateCode):
    state = "MO"


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

        # Don't append COUNTY if it's already in the county token
        if county_token.endswith("COUNTY"):
            return f"{county_token}_{state_code}"

        return f"{county_token}_COUNTY_{state_code}"


class NcCountyDependency(CountyDependency):
    state_dependency_class = NcStateCodeDependency


class IlCountyDependency(CountyDependency):
    state_dependency_class = IlStateCodeDependency


class MaCountyDependency(CountyDependency):
    state_dependency_class = MaStateCodeDependency


class TxCountyDependency(CountyDependency):
    state_dependency_class = TxStateCodeDependency


class KsCountyDependency(CountyDependency):
    state_dependency_class = KsStateCodeDependency


class MoCountyDependency(CountyDependency):
    """
    Missouri county token, with the St. Louis City special case handled.

    Missouri has one independent city — St. Louis — which is its own county-equivalent
    (FIPS 29510) and is *not* part of St. Louis County. The screener's ZIP map stores it
    as the literal string ``"St. Louis City"``, and the base normalizer would append
    ``_COUNTY`` to produce ``ST_LOUIS_CITY_COUNTY_MO``. PolicyEngine doesn't define that
    token: it silently falls back to a default rating area rather than erroring, which
    for ACA PTC returns an SLCSP of $9,121 instead of the correct $6,275 — overstating
    the credit by roughly $2,846/year for the state's second-largest jurisdiction.

    PolicyEngine's own token is ``ST_LOUIS_CITY_MO`` (verified against ``county_fips``
    29510, which returns the same value), so drop the ``_COUNTY`` insert for it. Every
    other one of Missouri's 114 counties resolves correctly through the base normalizer —
    checked by sweeping the full ``counties_by_zipcode`` list against the PE API.
    """

    state_dependency_class = MoStateCodeDependency

    # Screener county strings (normalized, pre-suffix) that PolicyEngine names without
    # the "_COUNTY" insert. Missouri has exactly one independent city.
    independent_cities = ("ST_LOUIS_CITY",)

    def value(self):
        county_token = super().value()

        for city in self.independent_cities:
            if county_token == f"{city}_COUNTY_{self.state_dependency_class.state}":
                return f"{city}_{self.state_dependency_class.state}"

        return county_token


class ZipCodeDependency(Household):
    field = "zip_code"
    dependencies = ["zipcode"]

    def value(self):
        return self.screen.zipcode


class IsInPublicHousingDependency(Household):
    field = "is_in_public_housing"

    def value(self):
        return self.screen.has_expense(["subsidizedRent"])

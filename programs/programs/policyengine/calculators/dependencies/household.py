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

    # Normalized county tokens that PolicyEngine names WITHOUT the "_COUNTY" insert —
    # county-equivalents that aren't counties: independent cities (St. Louis MO,
    # Baltimore MD, Carson City NV, and Virginia's 38), and, if we ever ship those
    # states, Louisiana parishes and Alaska boroughs / census areas.
    #
    # This matters because PolicyEngine does NOT reject an unknown county_str. It
    # silently falls back to a default rating area, so a bad token surfaces as a
    # plausible-but-wrong benefit value rather than an error. For MO ACA PTC the
    # unrecognized ST_LOUIS_CITY_COUNTY_MO returned an SLCSP of $9,121 instead of
    # $6,275 — a ~$2,846/year overstatement that nothing would have flagged.
    #
    # Empty by default: no behavior change for any state that doesn't set it.
    independent_cities: ClassVar[tuple[str, ...]] = ()

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

        # County-equivalents PolicyEngine names without the "_COUNTY" insert
        if county_token in self.independent_cities:
            return f"{county_token}_{state_code}"

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
    as the literal string ``"St. Louis City"``, which the base normalizer would otherwise
    turn into ``ST_LOUIS_CITY_COUNTY_MO``. PolicyEngine's own token is
    ``ST_LOUIS_CITY_MO`` (verified against ``county_fips`` 29510, which returns the same
    value); see ``CountyDependency.independent_cities`` for why the mismatch is dangerous.

    Every other one of Missouri's 114 counties resolves correctly through the base
    normalizer — checked by sweeping the full ``counties_by_zipcode`` list against the
    PE API.
    """

    state_dependency_class = MoStateCodeDependency
    independent_cities = ("ST_LOUIS_CITY",)


class ZipCodeDependency(Household):
    field = "zip_code"
    dependencies = ["zipcode"]

    def value(self):
        return self.screen.zipcode


class IsInPublicHousingDependency(Household):
    field = "is_in_public_housing"

    def value(self):
        return self.screen.has_expense(["subsidizedRent"])

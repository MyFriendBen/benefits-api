from .base import Household


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


class CountyDependency(Household):
    field = "county_str"
    dependencies = ["county"]
    state_dependency_class = None  # Override in subclasses

    def value(self):
        state_code = self.state_dependency_class.state
        return self.screen.county.replace(" ", "_").upper() + f"_{state_code}"


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

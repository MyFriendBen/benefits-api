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


class NcCountyDependency(Household):
    field = "county_str"

    def value(self):
        return self.screen.county.replace(" ", "_").upper() + "_NC"


class ZipCodeDependency(Household):
    field = "zip_code"
    dependencies = ["zipcode"]

    def value(self):
        return self.screen.zipcode


class IsInPublicHousingDependency(Household):
    field = "is_in_public_housing"

    def value(self):
        return self.screen.has_expense(["subsidizedRent"])

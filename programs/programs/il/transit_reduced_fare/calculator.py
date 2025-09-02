from programs.programs.il.bap.calculator import IlBenefitAccess
from programs.programs.calc import ProgramCalculator, Eligibility
from programs.programs.mixins import IlTransportationMixin


class IlTransitReducedFare(IlTransportationMixin, ProgramCalculator):
    dependencies = IlTransportationMixin.dependencies + ["county"]
    eligible_counties = ["cook", "dupage", "kane", "lake", "mchenry", "will"]

    def household_eligible(self, e: Eligibility):
        e.condition(not self.screen.has_benefit("il_transit_reduced_fare"))

        presumptive_eligible = self.check_presumptive_eligibility()

        household_size = self.screen.household_size
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))
        bap_income_limit = IlBenefitAccess.income_limit_by_household_size[min(household_size, 3)]
        income_eligible = gross_income > bap_income_limit

        county = (self.screen.county or "").lower()
        county_eligible = county in self.eligible_counties

        e.condition(county_eligible and (presumptive_eligible or income_eligible))

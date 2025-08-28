from programs.programs.il.bap.calculator import IlBenefitAccess
from programs.programs.calc import ProgramCalculator, Eligibility
from programs.programs.mixins import IlTransportationMixin


class IlTransitReducedFare(IlTransportationMixin, ProgramCalculator):
    eligible_counties = ["cook", "dupage", "kane", "lake", "mchenry", "will"]

    def household_eligible(self, e: Eligibility):
        presumptive_eligible = self.check_presumptive_eligibility()

        household_size = self.screen.household_size
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))
        bap_income_limit = IlBenefitAccess.income_limit_by_household_size.get(
            min(household_size, 3), IlBenefitAccess.income_limit_by_household_size[3]
        )
        income_eligible = gross_income > bap_income_limit

        county = (self.screen.county or "").lower()
        county_eligible = county in self.eligible_counties

        e.condition(presumptive_eligible or (income_eligible and county_eligible))

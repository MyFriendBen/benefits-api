from programs.programs.il.bap.calculator import IlBenefitAccess
from programs.programs.calc import Eligibility


class IlTransitReducedFare(IlBenefitAccess):
    county_benefit_amounts = {
        # Chicago Area counties - $40/month ($480/year)
        "cook": 480,
        "dupage": 480,
        "kane": 480,
        "lake": 480,
        "mchenry": 480,
        "will": 480,
        # Other counties
        "madison": 240,
        "peoria": 240,
        "sangamon": 228,
        "jackson": 120,
    }

    def household_eligible(self, e: Eligibility):
        # Check presumptive eligibility
        presumptive_eligible = self.screen.has_benefit_from_list(
            self.presumptive_eligibility_programs
        ) or self.screen.has_insurance_types(self.presumptive_eligibility_insurances)

        # Check income eligibility
        household_size = self.screen.household_size
        income_limit = self.income_by_household_size.get(min(household_size, 3), self.income_by_household_size[3])

        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))

        # Income must be above the Benefit Access limit
        income_eligible = gross_income > income_limit

        e.condition(presumptive_eligible or income_eligible)

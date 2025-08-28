from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility
import programs.programs.messages as messages


class IlBenefitAccess(ProgramCalculator):
    dependencies = [
        "age",
        "household_size",
        "income_amount",
        "income_frequency",
        "visually_impaired",
        "disabled",
    ]

    presumptive_eligibility_programs = ["ssi", "ssdi"]

    presumptive_eligibility_insurances = ["medicare"]

    minimum_age = 65

    minimum_age_with_disability = 16

    income_by_household_size = {
        1: 33_562,
        2: 44_533,
        3: 55_500,
    }

    county_benefit_amounts = {
        # Chicago Area counties - $75/month ($900/year)
        "cook": 900,
        "dupage": 900,
        "kane": 900,
        "lake": 900,
        "mchenry": 900,
        "will": 900,
        # $40/month counties ($480/year)
        "madison": 480,
        "peoria": 480,
        "sangamon": 480,
        # Jackson county - $25/month ($300/year)
        "jackson": 300,
    }

    def household_eligible(self, e: Eligibility):
        presumptive_eligible = self.screen.has_benefit_from_list(
            self.presumptive_eligibility_programs
        ) or self.screen.has_insurance_types(self.presumptive_eligibility_insurances)

        household_size = self.screen.household_size
        income_limit = self.income_by_household_size.get(min(household_size, 3), self.income_by_household_size[3])
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))

        income_eligible = gross_income <= income_limit
        household_eligible = household_size <= 3

        e.condition(presumptive_eligible or (income_eligible and household_eligible))

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # Check age eligibility
        age_eligible = member.age >= self.minimum_age

        disability_eligible = member.age >= self.minimum_age_with_disability and (
            member.visually_impaired or member.disabled
        )

        e.condition(age_eligible or disability_eligible)

    def member_value(self, member):
        county = self.screen.county.lower() if self.screen.county else ""

        # Default to positive value to enable manual "Varies" override, since county_benefit_amounts are not comprehensive
        return self.county_benefit_amounts.get(county, 1)

from programs.programs.calc import Eligibility, MemberEligibility
import programs.programs.messages as messages


class FplIncomeCheckMixin:
    """
    Mixin for programs that check household income against Federal Poverty Level percentages.
    """

    def check_fpl_income(self, e: Eligibility, fpl_percent: float) -> None:
        """
        Check household income against FPL percentage.

        Args:
            e: Eligibility object for condition checks
            fpl_percent: FPL percentage to check (e.g., 1.38 for 138% FPL)
        """
        # Calculate income limit
        fpl = self.program.year
        income_limit = int(fpl_percent * fpl.get_limit(self.screen.household_size))

        # Calculate gross income
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))

        # Add eligibility condition
        e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))


class IlTransportationMixin:
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

    def check_presumptive_eligibility(self):
        has_presumptive_program = self.screen.has_benefit_from_list(self.presumptive_eligibility_programs)
        has_presumptive_insurance = self.screen.has_insurance_types(self.presumptive_eligibility_insurances)
        return has_presumptive_program or has_presumptive_insurance

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        age_eligible = member.age >= self.minimum_age

        has_minimum_age_with_disability = member.age >= self.minimum_age_with_disability
        has_eligible_disability = member.visually_impaired or member.disabled
        disability_eligible = has_minimum_age_with_disability and has_eligible_disability

        e.condition(age_eligible or disability_eligible)

    def member_value(self, member):
        # Default to positive value to enable manual "Varies" override
        return 1

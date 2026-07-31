from programs.programs.calc import Eligibility, MemberEligibility
import programs.programs.messages as messages


class IlMedicaidFplIncomeCheckMixin:
    """
    Mixin for Illinois Medicaid programs that check household income against Federal Poverty Level percentages.
    Counts pregnant household members as 2 people when calculating household size.
    """

    def check_fpl_income(self, e: Eligibility, fpl_percent: float) -> None:
        """
        Check household income against FPL percentage with pregnancy-adjusted household size.

        Args:
            e: Eligibility object for condition checks
            fpl_percent: FPL percentage to check (e.g., 1.38 for 138% FPL)
        """
        # Calculate pregnancy-adjusted household size
        pregnant_count = self.screen.household_members.filter(pregnant=True).count()
        adjusted_household_size = self.screen.household_size + pregnant_count

        # Calculate income limit using adjusted household size
        # Round to match IL DHS published tables (WAG 25-03-02 Medical FPLs)
        # Source: https://ilaging.illinois.gov/content/dam/soi/en/web/aging/ship/documents/medicaidincomeassetlimits.pdf
        fpl = self.program.year
        income_limit = round(fpl_percent * fpl.get_limit(adjusted_household_size))

        # Calculate gross income
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))

        # Add eligibility condition
        e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))


class IlTransportationMixin:
    dependencies = [
        "age",
        "visually_impaired",
        "disabled",
    ]
    minimum_age = 65
    minimum_age_with_disability = 16

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

from programs.programs.calc import ProgramCalculator, Eligibility, MemberEligibility
import programs.programs.messages as messages
from .rate_data import SUBSIDY_RATE_TABLE, COPAYMENT_TABLE_A


class IlChildCareAssistanceProgram(ProgramCalculator):
    """
    Illinois Child Care Assistance Program (CCAP)

    Provides subsidized child care for low-income families who are working or attending school.

    Eligibility:
    - Live in Illinois
    - Be employed and/or going to an eligible educational activity
    - Have children younger than 13 (or up to 19 with special needs)
    - Family income at or below 225% FPL (initial application)

    Value varies by county group and child age.

    Note: The estimated value represents the state subsidy amount. Families are required to pay
    a monthly copayment based on income and family size. The copayment is per family, not per child.
    """

    dependencies = ["age", "county", "income_amount", "income_frequency", "household_size"]
    # Per IDHS policy 01.01.02, eligible children include:
    # - Biological/adoptive children and stepchildren of applicant
    # - Children cared for by legal guardian (foster/kinship care)
    # - Children cared for by caretaker relatives within 5th degree (grandchildren, siblings, etc.)
    # - The child's dependent blood-related and adoptive siblings
    child_relationships = ["child", "stepChild", "fosterChild", "grandChild", "sisterOrBrother", "stepSisterOrBrother"]

    # County groups for rate determination - if not in Group 1A or Group 1B, automatically in Group 2
    county_group_1a = ["Cook", "DeKalb", "DuPage", "Kane", "Kendall", "Lake", "McHenry"]
    county_group_1b = [
        "Boone",
        "Champaign",
        "Kankakee",
        "Madison",
        "McLean",
        "Monroe",
        "Ogle",
        "Peoria",
        "Rock Island",
        "Sangamon",
        "St. Clair",
        "Tazewell",
        "Whiteside",
        "Will",
        "Winnebago",
        "Woodford",
    ]

    # Income eligibility
    fpl_percent = 2.25  # 225% FPL for initial applications

    def get_county_group(self, county: str) -> str:
        """Determine the county group (IA, IB, or II) for rate calculation"""
        if county in self.county_group_1a:
            return "GROUP_1A"
        elif county in self.county_group_1b:
            return "GROUP_1B"
        else:
            return "GROUP_2"  # All other Illinois counties

    def household_eligible(self, e: Eligibility):
        """Check household-level eligibility conditions"""

        # Check: User hasn't already selected this benefit
        e.condition(not self.screen.has_benefit("il_ccap"))

        # Check: Asset limit ($1,000,000)
        if self.screen.household_assets is not None:
            e.condition(self.screen.household_assets < 1_000_000)

        # Check: Income eligibility (225% of FPL for initial applications)
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))
        income_limit = int(self.fpl_percent * self.program.year.get_limit(self.screen.household_size))
        e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))

        # Check: Household head must be employed or attending school
        head = self.screen.get_head()
        # Infer employment from earned income (wages or self-employment)
        earned_income = head.calc_gross_income("yearly", ["earned"])
        is_employed = earned_income > 0
        is_student = head.student if head.student is not None else False
        e.condition(is_employed or is_student)

    def member_eligible(self, e: MemberEligibility):
        """Check member-level eligibility conditions"""
        member = e.member

        # Check: Must be a child of the household
        e.condition(member.relationship in self.child_relationships)

        # Check: Child is under 13 years old, or under 19 if they have a disability
        if member.age is None:
            e.condition(False)
        elif member.has_disability():
            e.condition(member.age < 19)
        else:
            e.condition(member.age < 13)

    def calculate_monthly_copayment(self) -> int:
        """
        Calculate the monthly copayment based on family size and income.

        Uses standard copayment rates for first-time applications.

        Returns monthly copayment in dollars.

        Note: The copayment table already includes the $1/month copayment for low-income families.
        Other copayment exemptions and reductions (TANF, homelessness, part-time care, etc.)
        are detailed in the program description and not calculated here.
        """
        if self.screen.household_size is None or self.program.year is None:
            return 0

        family_size = self.screen.household_size
        monthly_income = int(self.screen.calc_gross_income("monthly", ["all"]))

        # Look up copayment in Table A
        if family_size in COPAYMENT_TABLE_A:
            for (min_income, max_income), copayment in COPAYMENT_TABLE_A[family_size]:
                if min_income <= monthly_income <= max_income:
                    return copayment

        # If no match found in table, return 0
        # This shouldn't happen for eligible families, but provides a safe default
        return 0

    def household_value(self) -> int:
        """
        Override household value to return net benefit (subsidy minus copayment).

        The household value is calculated as the total subsidy for all children
        minus the family's annual copayment.

        Note: This overrides the base class method to provide net benefit calculation.
        """
        # Total subsidy is calculated by summing member values
        # (member_value is called separately by the base class for each eligible member)
        # So we return the negative copayment here to offset the total
        annual_copayment = self.calculate_monthly_copayment() * 12
        return -annual_copayment

    def member_value(self, member) -> int:
        """
        Calculate the annual subsidy value for an eligible child.

        Value depends on:
        1. County group (IA, IB, or II)
        2. Child's age in months

        Note: Children 13-19 years old must have a disability to receive subsidy.
        This check is also in member_eligible(), but included here as a defensive check.
        """
        if member.age is None or self.screen.county is None:
            return 0

        # Defensive check: Children over 13 must have disability to be eligible for subsidy
        if member.age >= 13 and not member.has_disability():
            return 0

        county_group = self.get_county_group(self.screen.county)
        age_months = member.age * 12

        # Find matching rate in table
        for group, (min_age, max_age), monthly_rate in SUBSIDY_RATE_TABLE:
            if group == county_group and min_age <= age_months <= max_age:
                return monthly_rate * 12

        return 0  # No matching rate found (child too old or other reason)

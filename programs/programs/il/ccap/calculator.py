from programs.programs.calc import ProgramCalculator, Eligibility, MemberEligibility
import programs.programs.messages as messages


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

    # County groups for rate determination
    county_group_ia = ["Cook", "DeKalb", "DuPage", "Kane", "Kendall", "Lake", "McHenry"]

    county_group_ib = [
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

    # All other Illinois counties are Group II (handled in get_county_group method)

    # Monthly rates by county group and age (from PDF)
    # Multiplied by 12 to get annual value
    rates = {
        "IA": {
            "0-23_months": 1474 * 12,  # Infants (0-23 months)
            "24-35_months": 1188 * 12,  # Twos (24-35 months)
            "36-71_months": 1012 * 12,  # Preschool (36-71 months / 3-5 years)
            "6-13_years": 506 * 12,  # School age (6-13 years)
        },
        "IB": {
            "0-23_months": 1408 * 12,
            "24-35_months": 1122 * 12,
            "36-71_months": 946 * 12,
            "6-13_years": 484 * 12,
        },
        "II": {
            "0-23_months": 1254 * 12,
            "24-35_months": 1012 * 12,
            "36-71_months": 880 * 12,
            "6-13_years": 440 * 12,
        },
    }

    # Income eligibility
    fpl_percent = 2.25  # 225% FPL for initial applications

    def get_county_group(self, county: str) -> str:
        """Determine the county group (IA, IB, or II) for rate calculation"""
        if county in self.county_group_ia:
            return "IA"
        elif county in self.county_group_ib:
            return "IB"
        else:
            return "II"  # All other Illinois counties

    def get_age_bracket(self, age: int) -> str:
        """
        Determine the age bracket for rate calculation.

        Age brackets (in months):
        - 0-23 months (0-1 years)
        - 24-35 months (2 years)
        - 36-71 months (3-5 years)
        - 72-156 months (6-13 years)
        """
        age_months = age * 12  # Convert years to months

        if age_months <= 23:
            return "0-23_months"
        elif age_months <= 35:
            return "24-35_months"
        elif age_months <= 71:
            return "36-71_months"
        elif age_months <= 156:  # 13 years * 12 months
            return "6-13_years"
        else:
            return None  # Not eligible (too old)

    def household_eligible(self, e: Eligibility):
        """Check household-level eligibility conditions"""

        # Check: User hasn't already selected this benefit
        e.condition(not self.screen.has_benefit("il_ccap"))

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

    def member_value(self, member) -> int:
        """
        Calculate the annual subsidy value for an eligible child.

        Value depends on:
        1. County group (IA, IB, or II)
        2. Child's age bracket
        """
        county_group = self.get_county_group(self.screen.county)
        age_bracket = self.get_age_bracket(member.age)

        if age_bracket is None:
            return 0  # Child is too old

        # Get the annual rate for this county group and age bracket
        return self.rates[county_group][age_bracket]

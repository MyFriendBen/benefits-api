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

    # All other Illinois counties are Group II (handled in get_county_group method)

    # Monthly rates by county group and age range (from PDF)
    # Format: (county_group, (min_age_months, max_age_months), monthly_rate)
    # Annual value calculated as monthly_rate * 12
    RATE_TABLE = [
        ("GROUP_1A", (0, 23), 1474),      # Infants (0-23 months)
        ("GROUP_1A", (24, 35), 1188),     # Twos (24-35 months)
        ("GROUP_1A", (36, 71), 1012),     # Preschool (36-71 months / 3-5 years)
        ("GROUP_1A", (72, 156), 506),     # School age (6-13 years)
        ("GROUP_1B", (0, 23), 1408),      # Infants
        ("GROUP_1B", (24, 35), 1122),     # Twos
        ("GROUP_1B", (36, 71), 946),      # Preschool
        ("GROUP_1B", (72, 156), 484),     # School age
        ("GROUP_2", (0, 23), 1254),       # Infants
        ("GROUP_2", (24, 35), 1012),      # Twos
        ("GROUP_2", (36, 71), 880),       # Preschool
        ("GROUP_2", (72, 156), 440),      # School age
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
        2. Child's age in months
        """
        if member.age is None:
            return 0

        county_group = self.get_county_group(self.screen.county)
        age_months = member.age * 12

        # Find matching rate in table
        for group, (min_age, max_age), monthly_rate in self.RATE_TABLE:
            if group == county_group and min_age <= age_months <= max_age:
                return monthly_rate * 12

        return 0  # No matching rate found (child too old or other reason)

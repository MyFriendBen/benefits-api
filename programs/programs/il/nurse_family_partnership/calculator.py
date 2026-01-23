from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility


class IlNurseFamilyPartnership(ProgramCalculator):
    """
    Illinois Nurse-Family Partnership (NFP)

    Pairs first-time pregnant women with registered nurses who provide support
    from early pregnancy through the child's second birthday.

    Eligibility:
    - Pregnant (typically first-time moms, 28 weeks or less, but requirements vary by location so kept it flexible)
    - Income <= 300% FPL OR has WIC (presumed eligibility)

    Note: One partner confirmed they use 200% FPL, but WIC partners indicated flexibility
    in practice. We use a higher cutoff (300% FPL) and note in descriptions that
    requirements vary by location.

    Value estimate ($6,000):
    - ~60 visits over 2.5 years (weekly first month, bi-weekly until birth, weekly 6 weeks
      postpartum, bi-weekly until 20 months, monthly until 2nd birthday)
    - 60-minute visits (reasonable estimate)
    - $100/visit (mid-range for in-home specialized RN visit)
    - Source:
        - https://www.cebc4cw.org/program/nurse-family-partnership/
        - https://arhomecare.com/how-much-does-private-home-care-really-cost-your-2025-price-guide


    References:
    - https://changent.org/what-we-do/nurse-family-partnership/
    - https://changent.org/nfp-moms/
    - https://changent.org/locations/
    - https://www.cebc4cw.org/program/nurse-family-partnership/
    - CEDA (Community and Economic Development Association of Cook County) WIC Program
    """

    fpl_percent = 3
    child_relationships = ["child"]
    # annual amt = total value divided by length of program (2.5 years)
    amount = 6_000 / 2.5
    dependencies = [
        "relationship",
        "income_frequency",
        "income_amount",
        "age",
        "pregnant",
    ]

    def household_eligible(self, e: Eligibility):
        # income eligibility: 300% FPL or has WIC (presumed eligibility)
        income_limit = int(self.fpl_percent * self.program.year.get_limit(self.screen.household_size))
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))
        is_income_eligible = gross_income <= income_limit

        has_wic = self.screen.has_benefit("wic")

        e.condition(is_income_eligible or has_wic)

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # pregnant
        e.condition(member.pregnant is True)

from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility
from screener.models import Insurance


class CoNurseFamilyPartnership(ProgramCalculator):
    """
    Colorado Nurse-Family Partnership (NFP)

    Pairs first-time pregnant women with registered nurses who provide support
    from early pregnancy through the child's second birthday.

    Eligibility:
    - Pregnant (first-time, typically 28 weeks or less)
    - No other children in household
    - Income <= 200% FPL OR has Medicaid/emergency Medicaid OR has WIC (only Mother's income considered)

    Value estimate ($6,000):
    - ~60 visits over 2.5 years (weekly first month, bi-weekly until birth, weekly 6 weeks
      postpartum, bi-weekly until 20 months, monthly until 2nd birthday)
    - 60-minute visits (reasonable estimate)
    - $100/visit (mid-range for in-home specialized RN visit)
    - Source:
        - https://www.cebc4cw.org/program/nurse-family-partnership/
        - https://arhomecare.com/how-much-does-private-home-care-really-cost-your-2025-price-guide 

    References:
    - https://www.cebc4cw.org/program/nurse-family-partnership/
    - https://bouldercounty.gov/families/pregnancy/nurse-family-partnership/
    - https://www.elpasocountyhealth.org/appointments-adults-children-families/nurse-family-partnership-nfp/
    - https://www.larimer.gov/health/maternal-child-and-family-health/nurse-family-partnership-program
    """

    fpl_percent = 2
    # Only mother's income is considered; household size of 2 (mother + unborn child)
    income_household_size = 2
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
        # no other children
        e.condition(self.screen.num_children(child_relationship=self.child_relationships) == 0)

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # pregnant
        e.condition(member.pregnant)

        # income (only mother's income, household size of 2 for mother + unborn child)
        income_limit = int(self.fpl_percent * self.program.year.get_limit(self.income_household_size))
        income = int(member.calc_gross_income("yearly", ["all"]))
        is_income_eligible = income <= income_limit

        insurance: Insurance = member.insurance
        has_medicaid = insurance.medicaid or insurance.emergency_medicaid
        has_wic = self.screen.has_benefit("wic")

        e.condition(is_income_eligible or has_medicaid or has_wic)

from programs.programs.calc import ProgramCalculator, Eligibility, MemberEligibility
import programs.programs.messages as messages


class IlSilverAccess(ProgramCalculator):
    """
    Silver Access — DuPage Health Coalition ACA Marketplace premium assistance.

    Provides up to $150/member/month toward Marketplace premiums for DuPage County
    residents. Not insurance itself. Members already in Medicaid/Medicare are excluded;
    members aged 65+ are treated as Medicare-eligible even without reported coverage.

    Data gaps: Marketplace enrollment, Silver/Gold plan selection, and full-APTC use
    are surfaced in the description rather than gated in the screener. Employer/VA
    exclusion applies only to currently-reported coverage, not unenrolled offers.
    """

    member_amount = 150 * 12  # $150/month × 12 = $1,800/year
    fpl_percent = 2.5  # 250% FPL income ceiling
    medicaid_fpl_percent = 1.38  # 138% FPL — inline Medicaid income threshold
    medicare_age = 65
    eligible_county = "DuPage"
    eligible_insurance_types = ["none", "private"]

    dependencies = ["age", "insurance", "income_amount", "income_frequency", "household_size", "county"]

    def household_eligible(self, e: Eligibility):
        # Must reside in DuPage County
        e.condition(self.screen.county == self.eligible_county, messages.location())

        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))

        # Household income ≤ 250% FPL
        income_limit = int(self.fpl_percent * self.program.year.get_limit(self.screen.household_size))
        e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))

        # Household income must exceed the 138% FPL Medicaid threshold; if the household
        # qualifies for Medicaid by income they cannot receive Marketplace premium tax
        # credits and Silver Access cannot help them (criterion 3b in spec).
        medicaid_limit = int(self.medicaid_fpl_percent * self.program.year.get_limit(self.screen.household_size))
        e.condition(gross_income > medicaid_limit, messages.must_not_have_benefit("Medicaid or Medicare"))

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # Must not currently have employer/VA/Medicaid/Medicare coverage
        e.condition(member.insurance.has_insurance_types(self.eligible_insurance_types))

        # Members 65+ are Medicare-eligible by age even without reported coverage
        e.condition(member.age is None or member.age < self.medicare_age)

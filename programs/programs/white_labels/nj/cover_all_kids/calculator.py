from programs.framework.base import ProgramCalculator, Eligibility, MemberEligibility
import programs.framework.eligibility_messages as messages
from screener.models import HouseholdMember


class NjCoverAllKids(ProgramCalculator):
    """
    NJ FamilyCare Cover All Kids: free or low-cost health coverage for New Jersey children
    under 19, whatever their immigration status, with household MAGI income up to 355% FPL.

    Immigration status is open on the program row (`legal_status_required`), not here.

    Income is MAGI for the screener's tax unit: SSI, child support, gifts, workers'
    compensation and cash assistance (TANF and other, which is tax-exempt) are left out, and a
    dependent's income counts only if the dependent must file a federal return for the year
    eligibility is judged in. The filing test follows
    IRS Publication 501, Table 2 (single dependents) with the 2026 amounts from
    Rev. Proc. 2025-32.

    Data gaps (spec §5): the screener's tax unit stands in for who claims each child; veterans'
    disability pay and post-2018 alimony count in full; every dependent is tested as unmarried;
    and the $400 self-employment test reads the amount entered, not net earnings.

    Value is the unsubsidized 2026 NJ benchmark silver premium for one child, per eligible child.
    """

    program_code = "nj_cover_all_kids"
    max_age = 18
    fpl_percent = 3.55
    member_amount = 3_915

    excluded_income_types = ["sSI", "childSupport", "gifts", "workersComp", "cashAssistance", "cashAssistanceOther"]
    earned_income_types = ["wages", "selfEmployment"]
    social_security_types = ["sSDisability", "sSRetirement", "sSSurvivor", "sSDependent"]

    # 2026 single-dependent filing thresholds (Rev. Proc. 2025-32, §4.14)
    unearned_threshold = 1_350
    earned_threshold = 16_100
    earned_income_addition = 450
    aged_or_blind_addition = 2_050
    aged_min_age = 65
    self_employment_threshold = 400
    social_security_base_amount = 25_000

    dependencies = [
        "age",
        "relationship",
        "student",
        "disabled",
        "visually_impaired",
        "long_term_disability",
        "income_type",
        "income_amount",
        "income_frequency",
    ]

    def member_eligible(self, e: MemberEligibility) -> None:
        age = e.member.calc_age()
        e.condition(age is not None and age <= self.max_age)

    def household_eligible(self, e: Eligibility) -> None:
        tax_unit = [m for m in self.screen.household_members.all() if m.is_in_tax_unit()]

        income = sum(self._countable_income(m) for m in tax_unit)
        income_limit = self.fpl_percent * self.program.year.get_limit(len(tax_unit))

        e.condition(income <= income_limit, messages.income(income, income_limit))

    def _countable_income(self, member: HouseholdMember) -> float:
        """
        Yearly MAGI the member adds to the household. The head and spouse always count;
        anyone else counts only if they must file a tax return.
        """
        if not (member.is_head() or member.is_spouse()) and not self._must_file(member):
            return 0

        return member.calc_gross_income("yearly", ["all"], exclude=self.excluded_income_types)

    def _must_file(self, member: HouseholdMember) -> bool:
        """IRS Publication 501, Table 2 and Table 3, for an unmarried dependent."""
        counted = member.calc_gross_income("yearly", ["all"], exclude=self.excluded_income_types)
        earned = member.calc_gross_income("yearly", self.earned_income_types)
        social_security = member.calc_gross_income("yearly", self.social_security_types)
        other_unearned = counted - earned - social_security

        # Social Security enters the test only when half of it plus other income passes the base amount
        social_security_counts = social_security / 2 + earned + other_unearned > self.social_security_base_amount
        unearned = other_unearned + (social_security if social_security_counts else 0)

        addition = 0
        age = member.calc_age()
        if age is not None and age >= self.aged_min_age:
            addition += self.aged_or_blind_addition
        if member.visually_impaired:
            addition += self.aged_or_blind_addition

        gross_threshold = min(max(self.unearned_threshold, earned + self.earned_income_addition), self.earned_threshold)
        self_employment = member.calc_gross_income("yearly", ["selfEmployment"])

        return (
            unearned > self.unearned_threshold + addition
            or earned > self.earned_threshold + addition
            or earned + unearned > gross_threshold + addition
            or self_employment >= self.self_employment_threshold
        )

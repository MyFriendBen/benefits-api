from datetime import date

from programs.framework.base import MemberEligibility, ProgramCalculator
from screener.models import HouseholdMember


class FederalSsdi(ProgramCalculator):
    """
    Social Security Disability Insurance, one calculator for every white label.

    A member qualifies on one of three routes:

    - **worker**: under full retirement age, monthly earnings at or under the substantial
      gainful activity limit, and either disabled (both the "unable to work" and the 12-month
      condition checkboxes) or reporting a visual impairment. Under 18, the member must also be
      earning: work credits come only from earnings, and the screener sees only current income.
    - **child**: the head of household's or spouse's child, stepchild or grandchild, unmarried,
      and under 18, a full-time student under 19, or a disabled adult with earnings under the
      limit, where the head or spouse receives Social Security disability or retirement income.
    - **surviving spouse**: aged 50 to 60, disabled, with earnings under the limit. The screener
      cannot tell whether a spouse has died, so every household that passes this route also
      passes the worker route at the same amount.

    Nobody already receiving SSDI qualifies: a member with SSDI income is excluded, and so is the
    whole household when it reports SSDI as a current benefit, since a current benefit names no
    member. The check matches the `ssdi` base program rather than this program's name, so a
    screen still holding a deactivated state SSDI row is excluded too.

    Not evaluated, because the screener does not collect them: work credits, the five-month
    waiting period, whether a parent or spouse has died, and when a disability began.
    """

    program_code = "federal_ssdi"

    # 2026 substantial gainful activity limits, per month.
    sga_limit = 1_690
    sga_limit_blind = 2_830

    # Monthly estimate for a disabled worker or surviving spouse; a child gets half.
    worker_amount = 1_497 * 12
    child_amount = 748 * 12

    child_relationships = ("child", "stepChild", "grandChild")
    insured_parent_relationships = ("headOfHousehold", "spouse")
    insured_parent_income_types = ("sSDisability", "sSRetirement")

    survivor_min_age = 50
    survivor_max_age = 60
    child_age_limit = 18
    # Below this, a worker is taken to have work credits only while reporting earnings.
    adult_worker_age = 18
    student_age_limit = 19

    # Full retirement age for anyone born on 1/2/1960 or later. Without a birth month, a member
    # is compared against this, the age that applies to everyone currently under 66.
    latest_full_retirement_age = 67

    dependencies = [
        "age",
        "relationship",
        "disabled",
        "long_term_disability",
        "visually_impaired",
        "income_type",
        "income_amount",
        "income_frequency",
    ]

    def member_eligible(self, e: MemberEligibility) -> None:
        member = e.member

        e.condition(self._route_value(member) > 0)

    def member_value(self, member: HouseholdMember) -> int:
        return self._route_value(member)

    def _route_value(self, member: HouseholdMember) -> int:
        """The member's annual amount on the first route they pass, or 0 if they pass none.

        A disabled adult child under the earnings limit passes the worker route too, so the
        worker amount is checked first.
        """
        if not self._not_receiving_ssdi(member):
            return 0

        if self._worker_eligible(member) or self._surviving_spouse_eligible(member):
            return self.worker_amount

        if self._child_eligible(member):
            return self.child_amount

        return 0

    def _not_receiving_ssdi(self, member: HouseholdMember) -> bool:
        if member.calc_gross_income("monthly", ["sSDisability"]) > 0:
            return False

        return not self.screen.has_base_benefit("ssdi")

    def _worker_eligible(self, member: HouseholdMember) -> bool:
        if not self._below_full_retirement_age(member):
            return False

        if not self._earnings_below_sga(member):
            return False

        if not self._minor_has_earnings(member):
            return False

        return self._disabling_condition(member) or bool(member.visually_impaired)

    def _minor_has_earnings(self, member: HouseholdMember) -> bool:
        age = member.calc_age()
        if age is not None and age >= self.adult_worker_age:
            return True

        return member.calc_gross_income("monthly", ["earned"]) > 0

    def _surviving_spouse_eligible(self, member: HouseholdMember) -> bool:
        age = member.calc_age()
        if age is None or not self.survivor_min_age <= age <= self.survivor_max_age:
            return False

        return self._disabling_condition(member) and self._earnings_below_sga(member)

    def _child_eligible(self, member: HouseholdMember) -> bool:
        if member.relationship not in self.child_relationships:
            return False

        if member.is_married()["is_married"]:
            return False

        if not self._insured_parent_entitled():
            return False

        age = member.calc_age()
        if age is None:
            return False

        if age < self.child_age_limit:
            return True

        if member.student_full_time and age < self.student_age_limit:
            return True

        # An adult child's long-term condition is part of the disability test.
        return self._disabling_condition(member) and self._earnings_below_sga(member)

    def _insured_parent_entitled(self) -> bool:
        for member in self.screen.household_members.all():
            if member.relationship not in self.insured_parent_relationships:
                continue

            if member.calc_gross_income("monthly", self.insured_parent_income_types) > 0:
                return True

        return False

    @staticmethod
    def _disabling_condition(member: HouseholdMember) -> bool:
        return bool(member.disabled) and bool(member.long_term_disability)

    def _earnings_below_sga(self, member: HouseholdMember) -> bool:
        limit = self.sga_limit_blind if member.visually_impaired else self.sga_limit
        return member.calc_gross_income("monthly", ["earned"]) <= limit

    def _below_full_retirement_age(self, member: HouseholdMember) -> bool:
        birth_year_month = member.birth_year_month
        if birth_year_month is None:
            age = member.calc_age()
            return age is not None and age < self.latest_full_retirement_age

        reference_date = self.screen.get_reference_date()
        age_in_months = (reference_date.year - birth_year_month.year) * 12 + (
            reference_date.month - birth_year_month.month
        )

        return age_in_months < self.full_retirement_age_months(birth_year_month)

    @staticmethod
    def full_retirement_age_months(birth_year_month: date) -> int:
        """Full retirement age in months, by the 20 CFR 404.409(a) table.

        The table's rows start on the 2nd of January, and the screener records only a birth
        month, which is taken as the 1st. So a January birth falls in the previous year's row.
        """
        cohort = birth_year_month.year if birth_year_month.month > 1 else birth_year_month.year - 1

        if cohort < 1938:
            return 65 * 12
        if cohort <= 1942:
            return 65 * 12 + (cohort - 1937) * 2
        if cohort <= 1954:
            return 66 * 12
        if cohort <= 1959:
            return 66 * 12 + (cohort - 1954) * 2
        return 67 * 12

from programs.framework.base import ProgramCalculator, Eligibility, MemberEligibility


class MoMetroTransitReducedFare(ProgramCalculator):
    """
    Metro Transit Reduced Fare Program (St. Louis) — half-price MetroBus and
    MetroLink fares.

    A member qualifies through any one of five pathways: age, disability,
    Medicare, SSDI, or SSI. Value is a flat annual estimate per eligible member.

    See spec.md for the eligibility rules, their sources, and the data gaps.
    """

    program_code = "mo_mtrfp"
    dependencies = ["age", "disabled", "visually_impaired", "health_insurance", "income_type", "income_amount"]

    minimum_age = 65
    # Annual; see spec.md for the derivation.
    member_amount = 468

    # Read from the member's own income streams, not household current
    # benefits: `CurrentBenefit` is keyed on (screen, program) with no member
    # FK, so it cannot say who receives the benefit and would qualify a
    # recipient's whole household. `IncomeStream` is member-scoped.
    qualifying_income_types = ("sSDisability", "sSI")

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        age = member.calc_age()
        age_eligible = age is not None and age >= self.minimum_age

        disability_eligible = member.disabled or member.visually_impaired

        has_medicare = member.has_insurance("medicare")

        receives_qualifying_benefit = member.calc_gross_income("yearly", self.qualifying_income_types) > 0

        e.condition(age_eligible or disability_eligible or has_medicare or receives_qualifying_benefit)

    def household_eligible(self, e: Eligibility):
        # Every criterion is evaluated per member.
        pass

from programs.framework.base import ProgramCalculator, Eligibility, MemberEligibility


class MoMetroTransitReducedFare(ProgramCalculator):
    """
    Metro Transit Reduced Fare Program (St. Louis) — half-price MetroBus and
    MetroLink fares for riders who hold a Reduced Fare Permit.

    Eligibility is purely categorical: a member qualifies by meeting any one of
    five pathways — age 65+, a disability requiring accessibility features,
    Medicare enrollment, SSDI receipt, or SSI receipt. There is no income test,
    asset test, or county restriction; neither Metro's Reduced Fare Programs page
    nor its Reduced Fare Application limits eligibility by geography.

    Two pathways from Metro's application cannot be screened:

    - VA disability documentation showing 100% status — no screener field
      captures a VA rating percentage, so this pathway is surfaced in the
      program description instead.
    - Metro excludes disabilities that do not require accessibility features,
      limitations based solely on pregnancy, obesity, substance dependency,
      contagious disease or controlled epilepsy, and conditions in remission.
      The screener collects only a general disability flag, so these exclusions
      are not applied; Metro's ADA Services makes the final determination.

    Value is the monthly 30-Day Pass differential ($78.00 standard less $39.00
    reduced), annualized per eligible member. Only the 30-Day Pass has a
    published reduced price, so this is an estimate of average annual savings
    rather than a fixed per-ride discount.
    """

    program_code = "mo_mtrfp"
    dependencies = ["age", "disabled", "visually_impaired", "health_insurance", "income_type", "income_amount"]

    minimum_age = 65
    # $78.00 standard 30-Day Pass less $39.00 reduced, x 12 months
    member_amount = 468

    # SSDI and SSI are read from the member's own income streams rather than
    # from household current benefits. The permit is per person, and its
    # qualifying document is the applicant's own award letter, so a parent's
    # SSDI must not qualify their child. `CurrentBenefit` is keyed on
    # (screen, program) with no member FK, so it cannot answer "who receives
    # this"; `IncomeStream` is member-scoped and can.
    qualifying_income_types = ("sSDisability", "sSI")

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        age = member.calc_age()
        age_eligible = age is not None and age >= self.minimum_age

        # Metro accepts legal blindness as satisfying its "requires special
        # facilities" standard, so visual impairment is its own path in.
        disability_eligible = member.disabled or member.visually_impaired

        has_medicare = member.has_insurance("medicare")

        # SSDI and SSI award letters are each sufficient proof on their own
        # under Metro's qualifying-document list.
        receives_qualifying_benefit = member.calc_gross_income("yearly", self.qualifying_income_types) > 0

        e.condition(age_eligible or disability_eligible or has_medicare or receives_qualifying_benefit)

    def household_eligible(self, e: Eligibility):
        # No household-level requirements: the program has no income, asset or
        # county gate. Every criterion is evaluated per member.
        pass

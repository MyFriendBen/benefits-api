from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility
import programs.programs.messages as messages


class KsNurseFamilyPartnership(ProgramCalculator):
    """
    Kansas Nurse-Family Partnership (NFP)

    Pairs first-time pregnant women with registered nurses who provide support
    from early pregnancy through the child's second birthday. Adapted from the
    existing MFB `co_nfp` and `il_nfp` calculators.

    Eligibility:
    - Pregnant (first-time mother, enrolled during pregnancy)
    - No previous live births, approximated by "no existing children in the
      household" via `num_children`
    - Resides in a Kansas service area: Shawnee County or Johnson County (KS is
      NOT statewide for NFP). This ZIP/county gate is new for MFB NFP.
    - Household income <= 171% FPL (Kansas Medicaid/KanCare threshold for
      pregnant women, used as the low-income proxy)

    Value estimate ($6,000):
    - ~60 visits over 2.5 years, $100/visit (mid-range in-home RN visit)
    - annual amt = total value divided by length of program (2.5 years) = $2,400
    - Source:
        - https://www.cebc4cw.org/program/nurse-family-partnership/detailed
        - https://arhomecare.com/blog/how-much-does-private-home-care-really-cost-your-2025-price-guide

    Data gaps / nuances (see spec.md):
    - First-time-parent status has no dedicated screener field. `num_children` is
      household-level and `relationship` is always relative to the head of
      household, so children cannot be attributed to a specific parent. A
      household with any child of the head is treated as not first-time. This
      correctly excludes second-time mothers but also excludes households where
      the child belongs to a partner (documented limitation).
    - Gestational age / enrollment timing (<= 28 weeks) is not captured; only the
      `pregnant` boolean is available.
    - A KCMO-area affiliate may serve some KS residents in the KC metro area; this
      cannot be gated on KS county/ZIP alone.
    - Prior NFP participation history is not tracked. Suppression of applicants
      already enrolled is handled by the framework (`show_on_current_benefits` /
      `already_has`), not by this calculator.

    References:
    - https://www.snco.gov/hd/nurse_family_partnership.php
    - https://www.jocogov.org/department/health/pregnancy-services
    - https://www.nursefamilypartnership.org/locations/kansas/
    """

    fpl_percent = 1.71
    eligible_counties = ["Shawnee County", "Johnson County"]
    # Only the head's own children (prior live births) disqualify. Step/foster
    # children are not the mother's live births, so only "child" is counted.
    child_relationships = ["child"]
    # annual amt = total value divided by length of program (2.5 years)
    amount = 6_000 / 2.5
    dependencies = [
        "relationship",
        "income_frequency",
        "income_amount",
        "age",
        "pregnant",
        "county",
        "household_size",
    ]

    def household_eligible(self, e: Eligibility):
        # must reside in a Kansas NFP service area (Shawnee or Johnson County)
        e.condition(self.screen.county in self.eligible_counties, messages.location())

        # first-time parent proxy: no existing children of the head in the household
        e.condition(self.screen.num_children(child_relationship=self.child_relationships) == 0)

        # income <= 171% FPL for the household. Round to the nearest whole dollar
        # (not truncate) so the limit matches the documented threshold: for a
        # 1-person household in 2026, 15,960 * 1.71 = 27,291.6 -> $27,292.
        income_limit = round(self.fpl_percent * self.program.year.get_limit(self.screen.household_size))
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))
        e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # pregnant first-time mother
        e.condition(member.pregnant is True)

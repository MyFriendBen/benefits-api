from programs.framework.base import MemberEligibility, ProgramCalculator, Eligibility
import programs.framework.eligibility_messages as messages


class MoNurseFamilyPartnership(ProgramCalculator):
    """
    Missouri Nurse-Family Partnership (NFP)

    Pairs first-time pregnant women with registered nurses who provide support
    from early pregnancy through the child's second birthday. Adapted from the
    existing MFB `co_nfp`, `il_nfp` and `ks_nurse_family_partnership` calculators.

    Eligibility:
    - Pregnant
    - Resides in one of the 14 Missouri jurisdictions served by one of the three
      regional NFP providers (MO is NOT statewide for NFP):
        - Kansas City Health Department: Cass, Clay, Jackson, Johnson, Lafayette,
          Platte, Ray counties
        - Building Blocks of Missouri Southeast (Mercy): Butler, Dunklin,
          Pemiscot, Ripley, Wayne counties
        - St. Louis County Department of Public Health: St. Louis County,
          St. Louis City
    - Household income <= 185% FPL (Children's Trust Fund of Missouri MIECHV
      statewide threshold, which names NFP explicitly)

    Value estimate ($6,000):
    - ~60 visits over 2.5 years, $100/visit (mid-range in-home RN visit)
    - annual amt = total value divided by length of program (2.5 years) = $2,400
    - Source:
        - https://www.cebc4cw.org/program/nurse-family-partnership/detailed
        - https://arhomecare.com/blog/how-much-does-private-home-care-really-cost-your-2025-price-guide

    The value is awarded per eligible member rather than per household: each
    pregnant person enrolls independently with their own nurse, so a household
    with two eligible pregnant members is worth $4,800/year. This is why
    `member_amount` is used here where the CO/IL/KS siblings use `amount`.

    Data gaps / nuances (see spec.md):
    - First-time-parent status has no dedicated screener field. Unlike the KS
      sibling, which approximates it by excluding households that already have a
      child of the head, MO applies the inclusive default and does not gate on it
      at all: `num_children` is household-level and `relationship` is always
      relative to the head, so a partner's child would wrongly disqualify a
      first-time mother. The requirement is surfaced in the program description
      instead so the user self-identifies.
    - Gestational age / enrollment timing (<= 28 weeks) is not captured; only the
      `pregnant` boolean is available. Also surfaced in the description.
    - The MIECHV priority populations (pregnant people under 21, child-welfare
      involvement, substance/tobacco use, developmental delays, military service)
      determine which eligible families a provider serves first when demand
      exceeds capacity. They are not eligibility gates and are deliberately not
      implemented here.

    References:
    - https://ctf4kids.org/home-visiting-programs/miechv/
    - https://dese.mo.gov/childhood/home-visiting/nurse-family-partnership
    - https://dese.mo.gov/communications/missouri-home-visiting-programs-restructured
    - https://www.kcmo.gov/city-hall/departments/health/community-and-family-health-education
    - https://www.mercy.net/practice/mercy-birthplace-cape-girardeau/building-blocks-of-missouri-southeast/
    - https://stlouiscountymo.gov/st-louis-county-departments/public-health/divisions/health-promotion-and-public-health-research/public-health-nursing/nurse-family-partnership/
    """

    program_code = "mo_nfp"

    fpl_percent = 1.85
    # The 14 jurisdictions covered by the three regional providers. These strings
    # must match the county names the screener sends for MO exactly (see
    # configuration/white_labels/mo.py counties_by_zipcode) — note St. Louis City
    # carries no "County" suffix.
    eligible_counties = [
        # Kansas City region
        "Cass County",
        "Clay County",
        "Jackson County",
        "Johnson County",
        "Lafayette County",
        "Platte County",
        "Ray County",
        # Southeast region
        "Butler County",
        "Dunklin County",
        "Pemiscot County",
        "Ripley County",
        "Wayne County",
        # St. Louis region
        "St. Louis County",
        "St. Louis City",
    ]
    # annual amt = total value divided by length of program (2.5 years)
    member_amount = 6_000 / 2.5
    dependencies = [
        "income_frequency",
        "income_amount",
        "pregnant",
        "county",
        "household_size",
    ]

    def household_eligible(self, e: Eligibility):
        # must reside in one of the 14 jurisdictions an NFP provider serves
        e.condition(self.screen.county in self.eligible_counties, messages.location())

        # income <= 185% FPL for the household
        income_limit = int(self.fpl_percent * self.program.year.get_limit(self.screen.household_size))
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))
        e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # pregnant
        e.condition(member.pregnant is True)

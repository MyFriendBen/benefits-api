import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.federal.pe.member import Medicaid, Ssi
from screener.models import HouseholdMember


class WaAppleHealthMedicaid(Medicaid):
    pe_inputs = [
        *Medicaid.pe_inputs,
        dependency.household.WaStateCodeDependency,
    ]

    # KFF 2023 WA Medicaid Spending Per Full-Benefit Enrollee (monthly)
    medicaid_categories = {
        "NONE": 0,
        "ADULT": 471,
        "INFANT": 233,
        "YOUNG_CHILD": 233,
        "OLDER_CHILD": 233,
        "PREGNANT": 445,
        "YOUNG_ADULT": 471,
        "PARENT": 445,
        "SSI_RECIPIENT": 2627,
        "AGED": 1921,
        "DISABLED": 2627,
    }

    # HCA 2026 Apple Health for Kids premium tier ceiling (317% effective FPL, annual).
    # Source: WAC 182-505-0215; derived from 2026 HHS FPL guidelines × 3.17.
    _PREMIUM_CHIP_ANNUAL_CEILING = {
        1: 50_591,
        2: 68_591,
        3: 86_604,
        4: 104_610,
        5: 122_636,
        6: 140_621,
        7: 158_627,
    }

    # FPL per-additional-member increment ($5,680 in 2026) × 3.17
    _PREMIUM_CHIP_ADDITIONAL_MEMBER = 18_006

    def member_value(self, member: HouseholdMember):
        age = member.calc_age()

        # 1. Foster care categorical (42 U.S.C. § 1396a(a)(10)(A)(i)(I); WAC 182-505-0211)
        #    Children ≤20 in foster care are categorically eligible regardless of income.
        if member.relationship == "fosterChild" and age is not None and age <= 20:
            return self.medicaid_categories["OLDER_CHILD"] * 12

        # 2. Medicare exclusion (42 CFR § 435.119(b)(3))
        #    Medicare-entitled *adults* cannot use ACA expansion. Route to ABD if
        #    senior/disabled; otherwise ineligible for this program.
        #    Children with Medicare are not subject to this exclusion — they use
        #    standard child MAGI pathways handled by PE in step 3.
        if age is not None and age >= 19 and member.has_insurance_types(("medicare",), strict=False):
            is_senior = age is not None and age >= self.aged_min_age
            is_disabled = member.has_disability()

            if is_senior or is_disabled:
                qualifies = self.get_member_dependency_value(dependency.member.MedicaidSeniorOrDisabled, member.id)
                if not qualifies:
                    return 0
                if is_disabled:
                    return self.medicaid_categories["DISABLED"] * 12
                return self.medicaid_categories["AGED"] * 12

            # Medicare-entitled, not senior/disabled → ineligible for expansion
            return 0

        # 3. Standard PE pathway (parent class handles expansion + ABD)
        value = super().member_value(member)
        if value > 0:
            return value

        # 4. Premium CHIP fallback (WAC 182-505-0215)
        #    Children <19 above the free tier (≤215% FPL) but below the premium
        #    ceiling (317% effective FPL) who are uninsured qualify for Apple
        #    Health for Kids with a premium.
        if age is not None and age < 19:
            if not member.has_insurance_types(("none",)):
                return 0
            gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))
            hh_size = self.screen.household_size
            ceiling = self._premium_chip_ceiling(hh_size)
            if ceiling is not None and gross_income <= ceiling:
                return self.medicaid_categories["OLDER_CHILD"] * 12

        return 0

    @classmethod
    def _premium_chip_ceiling(cls, household_size: int) -> int | None:
        """Return the annual income ceiling for the WA premium CHIP tier.

        For household sizes 1–7 the values come from the HCA 2026 table.
        Larger households are extrapolated using the FPL per-member increment × 3.17.
        """
        if household_size <= 0:
            return None
        if household_size <= 7:
            return cls._PREMIUM_CHIP_ANNUAL_CEILING[household_size]
        extra_members = household_size - 7
        return cls._PREMIUM_CHIP_ANNUAL_CEILING[7] + (extra_members * cls._PREMIUM_CHIP_ADDITIONAL_MEMBER)


class WaSsi(Ssi):
    """
    Washington Supplemental Security Income — federal SSI applied to WA residents.

    A thin wrapper around the federal `Ssi` PolicyEngine calculator that adds the
    WA state code so PolicyEngine can apply state-specific SSI rules. Washington
    pays no general SSI state supplement (a small supplement exists for narrow
    residential-care categories that are out of scope for the screener), so the
    output is the federal Federal Benefit Rate (FBR) — published annually by the
    SSA — minus PolicyEngine's countable income. The current FBR is sourced from
    PolicyEngine's parameters at calculation time, not pinned in this file, so
    the calculator naturally tracks SSA cost-of-living adjustments year over year.

    All eligibility math (categorical entry: aged / disabled / blind, the
    $20 + $65 + 1/2 income exclusion stack, SGA cutoff, in-kind support and
    maintenance reductions, spousal and parental deeming, resource limits)
    is handled by PolicyEngine. The screener contributes only:
      - the per-member SSI input dependencies inherited from `Ssi.pe_inputs`
      - the WA state code so PE knows which state to model

    Duplicate-enrollment filtering ("not already receiving SSI") is enforced
    one layer up via `Screen.has_benefit("wa_ssi")`, which reads from the
    `CurrentBenefit` join table.

    See `programs/programs/wa/ssi/spec.md` for the full eligibility criteria,
    PolicyEngine variable mapping, and the 15 reference test scenarios.
    """

    pe_inputs = [
        *Ssi.pe_inputs,
        dependency.household.WaStateCodeDependency,
    ]

import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.federal.pe.member import Medicaid, Ssi, HeadStart, Msp
from programs.programs.policyengine.calculators.base import PolicyEngineMembersCalculator
from screener.models import HouseholdMember


class KsSsi(Ssi):
    """
    Kansas Supplemental Security Income — federal SSI applied to KS residents.

    A thin wrapper around the federal ``Ssi`` PolicyEngine calculator that adds the
    KS state code so PolicyEngine can apply state-specific SSI handling. Kansas pays
    no general SSI state supplement (the KS supplement, SSPP, is tracked as its own
    program), so the output is the federal Federal Benefit Rate (FBR) minus
    PolicyEngine's countable income. The FBR is sourced from PolicyEngine's
    parameters at calculation time, so the value tracks SSA COLA updates year over
    year.
    """

    pe_inputs = [
        *Ssi.pe_inputs,
        dependency.household.KsStateCodeDependency,
    ]


class KsKanCare(Medicaid):
    """KanCare is Kansas's Medicaid program (subclass of the federal ``medicaid`` calculator).

    Kansas has not adopted ACA adult expansion, so PE returns ineligible for
    non-disabled, non-pregnant, childless adults under 65 at any income.

    KS-specific inputs beyond the federal Medicaid set:

    - ``SsiCountableResourcesDependency`` screens the ABD $2,000/$3,000 resource limit.
    - ``MeetsSsiDisabilityCriteriaDependency`` / ``IsBlindDependency`` map the screener's
      disability, long-term-disability, SSDI, and visual-impairment signals to PE's
      SSI-criterion inputs (leaving the SGA earnings test intact). Without them,
      disabled/blind applicants would wrongly return ineligible.
    """

    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.PregnancyDependency,
        dependency.member.IsDisabledDependency,
        dependency.member.MeetsSsiDisabilityCriteriaDependency,
        dependency.member.IsBlindDependency,
        dependency.member.SsiCountableResourcesDependency,
        *dependency.irs_gross_income,
        dependency.household.KsStateCodeDependency,
    ]

    # KHI / Kansas Action for Children FY2023 KS Medicaid & CHIP per-enrollee
    # spending by group, monthly (annual figure returned = value * 12):
    #   MAGI groups  -> $3,644/yr  -> $304/mo
    #   aged (65+)   -> $20,511/yr -> $1,709/mo
    #   disabled     -> $32,459/yr -> $2,705/mo
    medicaid_categories = {
        "NONE": 0,
        "ADULT": 304,
        "INFANT": 304,
        "YOUNG_CHILD": 304,
        "OLDER_CHILD": 304,
        "PREGNANT": 304,
        "YOUNG_ADULT": 304,
        "PARENT": 304,
        "SSI_RECIPIENT": 2705,
        "AGED": 1709,
        "DISABLED": 2705,
    }


class KsChip(PolicyEngineMembersCalculator):
    """Kansas CHIP calculator (mirrors the TxChip precedent).

    Member value is PE's federal ``chip`` output (all CHIP eligibility logic — under 19,
    income ≤ the 255% FPL effective cap, not Medicaid-eligible — is already baked in),
    surfaced only for children whose insurance is exactly ``none``. Also outputs the
    Kansas ``ks_chip_premium`` (annual = monthly premium × 12) for display; it is not
    netted against the coverage value.

    PE gates CHIP on ``~is_medicaid_eligible``, so CHIP reuses ``KsKanCare.pe_inputs``
    to compute Medicaid eligibility the same way KanCare does. CHIP applies no resource
    test of its own.
    """

    pe_name = "chip"
    pe_inputs = [
        *KsKanCare.pe_inputs,
    ]
    pe_outputs = [
        dependency.member.Chip,
        dependency.tax.KsChipPremium,
    ]

    def member_value(self, member: HouseholdMember):
        """
        Returns the CHIP coverage value for this member, applying the
        uninsured-only rule.
        """
        pe_value = self.get_member_variable(member.id)

        # CHIP is only for children with no other health coverage. Any insurance
        # type other than "none" disqualifies the child.
        if member.has_insurance_types(("none",)):
            return pe_value

        return 0


class KsMsp(Msp):
    """Kansas Medicare Savings Program. Federal ``Msp`` plus the KS state code and KanCare's
    Medicaid inputs (which supply ``is_medicaid_eligible`` and ``ssi_countable_resources``)."""

    pe_inputs = [
        *Msp.pe_inputs,
        dependency.household.KsStateCodeDependency,
        *Medicaid.pe_inputs,
    ]


class KsHeadStart(HeadStart):
    """
    Kansas Head Start (ages 3-5). Thin wrapper on the federal ``HeadStart`` PE
    calculator that adds the KS state code; all eligibility and the per-child
    value are computed by PolicyEngine with no KS-specific variance. Early Head
    Start (birth to age 3, and pregnant women) is a separate program.
    """

    pe_inputs = [
        *HeadStart.pe_inputs,
        dependency.household.KsStateCodeDependency,
    ]

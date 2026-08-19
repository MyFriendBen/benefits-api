import programs.framework.pe_dependencies as dependency
from programs.programs.federal.pe.member import Ssi, HeadStart, EarlyHeadStart, Msp
from programs.framework.pe_base import PolicyEngineMembersCalculator
from screener.models import HouseholdMember
from programs.programs.cross_white_label.medicaid.ks import KsKanCare
from programs.programs.cross_white_label.medicaid.base import Medicaid


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

    program_code = "ks_ssi"

    pe_inputs = [
        *Ssi.pe_inputs,
        dependency.household.KsStateCodeDependency,
    ]


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

    program_code = "ks_chip"

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
    Medicaid inputs (see ``Msp`` for why the Medicaid inputs are required)."""

    program_code = "ks_medicare_savings"

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

    program_code = "ks_head_start"

    pe_inputs = [
        *HeadStart.pe_inputs,
        dependency.household.KsStateCodeDependency,
    ]


class KsEarlyHeadStart(EarlyHeadStart):
    """
    Kansas Early Head Start (birth to age 3, and pregnant women). Thin wrapper on
    the federal ``EarlyHeadStart`` PE calculator that adds the KS state code; all
    eligibility and the per-individual value are computed by PolicyEngine's
    ``early_head_start`` variable with no KS-specific variance. Head Start (ages
    3-5) is a separate program (``KsHeadStart``).
    """

    program_code = "ks_early_head_start"

    pe_inputs = [
        *EarlyHeadStart.pe_inputs,
        dependency.household.KsStateCodeDependency,
    ]

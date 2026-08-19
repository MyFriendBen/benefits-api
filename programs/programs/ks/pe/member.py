import programs.framework.pe_dependencies as dependency
from programs.framework.pe_base import PolicyEngineMembersCalculator
from screener.models import HouseholdMember
from programs.programs.cross_white_label.medicaid.ks import KsKanCare
from programs.programs.cross_white_label.medicaid.base import Medicaid
from programs.programs.cross_white_label.ssi.base import Ssi
from programs.programs.cross_white_label.msp.base import Msp
from programs.programs.cross_white_label.head_start.base import HeadStart
from programs.programs.cross_white_label.head_start.ks import KsHeadStart
from programs.programs.cross_white_label.early_head_start.base import EarlyHeadStart


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

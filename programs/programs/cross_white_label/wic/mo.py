"""MO WIC."""

from programs.programs.cross_white_label.wic.base import Wic
from screener.models import HouseholdMember
import programs.framework.pe_dependencies as dependency


class MoWic(Wic):
    """
    Missouri WIC — federal ``Wic`` PE calculator + MO state code.

    Missouri has no WIC-specific rules of its own: income limits (185% FPL) and the
    categorical pathways (SNAP / Temporary Assistance / MO HealthNet) are federal, and
    PolicyEngine's WIC tree only branches on AK/HI vs. contiguous-US FPG tables. MO
    falls in the contiguous set, so the federal calculator applies as-is.

    Unlike CO/NC/MA — which override ``wic_categories`` with hardcoded per-category
    monthly amounts — this returns PolicyEngine's own computed benefit amount, the same
    approach ``TxWic`` takes. The federal base class's ``wic_categories`` are all zeros,
    so inheriting ``member_value`` unchanged would value every eligible member at $0 and
    the frontend's ``value > 0`` filter would drop the program from results entirely.
    """

    program_code = "mo_wic"

    pe_inputs = [
        *Wic.pe_inputs,
        dependency.household.MoStateCodeDependency,
    ]

    def member_value(self, member: HouseholdMember):
        """Return PolicyEngine's calculated WIC benefit for this member."""
        return self.get_member_variable(member.id)

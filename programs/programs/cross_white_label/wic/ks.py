"""KS WIC."""

from programs.programs.cross_white_label.wic.base import Wic
from screener.models import HouseholdMember
import programs.framework.pe_dependencies as dependency


class KsWic(Wic):
    """
    Kansas WIC — federal ``Wic`` PE calculator + KS state code.

    Kansas sets no WIC rules of its own: the income limit (185% FPG) and the
    categorical pathways (SNAP / TANF / Medicaid) are federal, and PolicyEngine's
    WIC tree branches only on AK/HI vs. contiguous-US FPG tables. KS falls in the
    contiguous set, so the federal calculator applies unchanged.

    Returns PolicyEngine's computed benefit rather than a per-category table, the
    approach ``MoWic`` and ``TxWic`` take. The federal base's ``wic_categories``
    are all zeros, so inheriting ``member_value`` would value every eligible
    member at $0 and the frontend's ``value > 0`` filter would drop the program
    from results. CO/IL/MA/NC instead hardcode per-category monthly amounts;
    Kansas publishes no such table, so deriving the value from PE avoids
    inventing one.
    """

    program_code = "ks_wic"

    pe_inputs = [
        *Wic.pe_inputs,
        dependency.household.KsStateCodeDependency,
    ]

    def member_value(self, member: HouseholdMember):
        """Return PolicyEngine's calculated WIC benefit for this member."""
        return self.get_member_variable(member.id)

from programs.programs.federal.pe.member import (
    Wic,
    HeadStart,
    EarlyHeadStart,
)
import programs.programs.policyengine.calculators.dependencies as dependency
from screener.models import HouseholdMember


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

    This class used to carry its own ``*dependency.irs_gross_income`` as a partial fix for
    WIC income-blindness, ahead of the federal base being fixed. The full ``wic_income``
    bundle now lives on ``Wic``, so MO inherits it (and the other five WIC programs get it
    too) and only the state code is added here.
    """

    pe_inputs = [
        *Wic.pe_inputs,
        dependency.household.MoStateCodeDependency,
    ]

    def member_value(self, member: HouseholdMember):
        """Return PolicyEngine's calculated WIC benefit for this member."""
        return self.get_member_variable(member.id)


class MoHeadStart(HeadStart):
    """Missouri Head Start (ages 3-5) — federal ``HeadStart`` PE calculator + MO state code."""

    pe_inputs = [
        *HeadStart.pe_inputs,
        dependency.household.MoStateCodeDependency,
    ]


class MoEarlyHeadStart(EarlyHeadStart):
    """Missouri Early Head Start (birth-3 / pregnant) — federal ``EarlyHeadStart`` PE calculator + MO state code."""

    pe_inputs = [
        *EarlyHeadStart.pe_inputs,
        dependency.household.MoStateCodeDependency,
    ]

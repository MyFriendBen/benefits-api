"""NJ FamilyCare (Medicaid) — the first state on the federal Medicaid base."""

from typing import ClassVar, Optional

import programs.framework.pe_dependencies as dependency
from programs.programs.cross_white_label.medicaid.federal_base import (
    AGED,
    CHILD,
    DISABLED,
    NEW_ADULT,
    OTHER_ADULT,
    FederalMedicaid,
)
from screener.models import HouseholdMember


class NjMedicaid(FederalMedicaid):
    """
    NJ FamilyCare (Medicaid). Rules: program-ops
    ``programs/cross_white_label/medicaid/nj/medicaid_nj_spec.md``.

    PolicyEngine decides eligibility from NJ's state code and county; the value is §7's figure for
    the member's spending group.
    """

    program_code = "nj_medicaid"

    pe_inputs = [
        *FederalMedicaid.pe_inputs,
        dependency.household.NjStateCodeDependency,
        dependency.household.NjCountyDependency,
    ]

    # §7: New Jersey's row of MACStats Exhibit 22, FY 2023, "Full-benefit enrollees" columns.
    group_spend_per_fye_enrollee: ClassVar[dict[str, int]] = {
        CHILD: 4_203,
        NEW_ADULT: 7_248,
        OTHER_ADULT: 7_351,
        DISABLED: 38_688,
        AGED: 28_650,
    }

    def spending_group(self, category: str, member: HouseholdMember) -> Optional[str]:
        """§7: a pregnant member PolicyEngine places in a child group takes the other adult figure.

        NJ gives every pregnant woman in the group full coverage (``pregnancy_services_only_option``
        ``false``), and "For a member eligible as both pregnant and a child, MFB's value mapping uses
        the other adult figure". A pregnant SSI recipient keeps the disabled figure.
        """
        group = super().spending_group(category, member)
        if group == CHILD and member.pregnant:
            return OTHER_ADULT
        return group

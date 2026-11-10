"""NJ FamilyCare (Medicaid) — the first state on the federal Medicaid base."""

import programs.framework.pe_dependencies as dependency
from programs.programs.cross_white_label.medicaid.federal_base import FederalMedicaid


class NjMedicaid(FederalMedicaid):
    """
    NJ FamilyCare (Medicaid). Rules: program-ops
    ``programs/cross_white_label/medicaid/nj/medicaid_nj_spec.md``.

    PolicyEngine decides eligibility and each member's value from NJ's state code and county;
    the county sets the rating area PolicyEngine prices coverage against.
    """

    program_code = "nj_medicaid"

    pe_inputs = [
        *FederalMedicaid.pe_inputs,
        dependency.household.NjStateCodeDependency,
        dependency.household.NjCountyDependency,
    ]

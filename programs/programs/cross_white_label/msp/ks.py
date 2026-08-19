"""KS Medicare Savings Program."""

from programs.programs.cross_white_label.msp.base import Msp
from programs.programs.cross_white_label.medicaid.base import Medicaid
import programs.framework.pe_dependencies as dependency


class KsMsp(Msp):
    """Kansas Medicare Savings Program. Federal ``Msp`` plus the KS state code and KanCare's
    Medicaid inputs (see ``Msp`` for why the Medicaid inputs are required)."""

    program_code = "ks_medicare_savings"

    pe_inputs = [
        *Msp.pe_inputs,
        dependency.household.KsStateCodeDependency,
        *Medicaid.pe_inputs,
    ]

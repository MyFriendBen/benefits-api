"""IL Medicare Savings Program."""

from programs.programs.cross_white_label.msp.base import Msp
from programs.programs.cross_white_label.medicaid.il import IlMedicaid
import programs.framework.pe_dependencies.household as household_dependency


class IlMsp(Msp):
    """Illinois Medicare Savings Program. Federal ``Msp`` plus the IL state code and
    ``IlMedicaid`` inputs (see ``Msp`` for why the Medicaid inputs are required)."""

    program_code = "il_msp"

    pe_inputs = [
        *Msp.pe_inputs,
        household_dependency.IlStateCodeDependency,
        *IlMedicaid.pe_inputs,
    ]

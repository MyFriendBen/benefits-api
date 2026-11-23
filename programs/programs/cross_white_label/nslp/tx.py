"""TX National School Lunch Program."""

from programs.programs.cross_white_label.nslp.base import SchoolLunch
import programs.framework.pe_dependencies as dependency


class TxNslp(SchoolLunch):
    """
    Texas National School Lunch Program (NSLP) calculator.

    Uses PolicyEngine-calculated benefit amounts for TX-specific NSLP eligibility
    and benefit values. Inherits from federal SchoolLunch calculator and adds
    TX state code dependency.
    """

    program_code = "tx_nslp"

    pe_inputs = [
        *SchoolLunch.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]

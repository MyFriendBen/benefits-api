"""TX CSFP."""

from programs.programs.cross_white_label.csfp.base import CommoditySupplementalFoodProgram
import programs.framework.pe_dependencies as dependency


class TxCsfp(CommoditySupplementalFoodProgram):
    """
    Texas Commodity Supplemental Food Program (CSFP) calculator that uses PolicyEngine's calculations.
    Extends the federal CSFP calculator with Texas state code dependency.
    """

    program_code = "tx_csfp"

    pe_inputs = [
        *CommoditySupplementalFoodProgram.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]

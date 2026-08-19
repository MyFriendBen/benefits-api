"""NC Medicaid."""

from programs.programs.cross_white_label.medicaid.base import Medicaid
import programs.framework.pe_dependencies as dependency


class NcMedicaid(Medicaid):
    program_code = "nc_medicaid"
    pe_inputs = [
        *Medicaid.pe_inputs,
        dependency.household.NcStateCodeDependency,
    ]

    medicaid_categories = {
        "NONE": 0,
        "ADULT": 512,  # * 12 = 6146,  Medicaid Expansion Adults
        "INFANT": 372,  # * 12 = 4464,  Medicaid for Children
        "YOUNG_CHILD": 372,  # * 12 = 4464,  Medicaid for Children
        "OLDER_CHILD": 372,  # * 12 = 4464,  Medicaid for Children
        "PREGNANT": 1045,  # * 12 = 12536, Medicaid for Pregnant Women
        "YOUNG_ADULT": 512,  # * 12 = 6146,  Medicaid Expansion Adults
        "PARENT": 512,  # * 12 = 6146,  Medicaid Expansion Parents
        "SSI_RECIPIENT": 1519,  # * 12 = 18227,  Medicaid Expansion Parents
        "AGED": 1086,  # * 12 = 13035, Medicaid for the Aged
        "DISABLED": 1519,  # * 12 = 18227, Medicaid for the Disabled
    }

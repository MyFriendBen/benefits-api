"""IL Medicaid."""

from programs.programs.cross_white_label.medicaid.base import Medicaid
import programs.framework.pe_dependencies.household as household_dependency


class IlMedicaid(Medicaid):
    """Base Illinois Medicaid eligibility through PolicyEngine"""

    program_code = "il_medicaid"

    medicaid_categories = {
        "NONE": 0,
        "ADULT": 474,
        "INFANT": 0,
        "YOUNG_CHILD": 0,
        "OLDER_CHILD": 0,
        "PREGNANT": 474,
        "YOUNG_ADULT": 0,
        "PARENT": 474,
        "SSI_RECIPIENT": 474,
        "AGED": 474,
        "DISABLED": 474,
    }
    pe_inputs = [
        *Medicaid.pe_inputs,
        household_dependency.IlStateCodeDependency,
    ]

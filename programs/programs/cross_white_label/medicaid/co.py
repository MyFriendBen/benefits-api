"""CO Medicaid."""

from programs.programs.cross_white_label.medicaid.base import Medicaid
import programs.framework.pe_dependencies as dependency


class CoMedicaid(Medicaid):
    program_code = "co_medicaid"
    medicaid_categories = {
        "NONE": 0,
        "ADULT": 310,
        "INFANT": 200,
        "YOUNG_CHILD": 200,
        "OLDER_CHILD": 200,
        "PREGNANT": 310,
        "YOUNG_ADULT": 310,
        "PARENT": 310,
        "SSI_RECIPIENT": 310,
        "AGED": 170,
        "DISABLED": 310,
    }
    pe_inputs = [
        *Medicaid.pe_inputs,
        dependency.household.CoStateCodeDependency,
    ]

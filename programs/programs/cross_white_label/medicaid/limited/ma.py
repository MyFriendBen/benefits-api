"""MaMassHealthLimited."""

from programs.programs.cross_white_label.medicaid.base import Medicaid
import programs.framework.pe_dependencies as dependency


class MaMassHealthLimited(Medicaid):
    program_code = "ma_mass_health_limited"
    pe_inputs = [
        *Medicaid.pe_inputs,
        dependency.household.MaStateCodeDependency,
    ]

    medicaid_categories = {
        "NONE": 0,
        "ADULT": 255,
        "INFANT": 255,
        "YOUNG_CHILD": 255,
        "OLDER_CHILD": 255,
        "PREGNANT": 255,
        "YOUNG_ADULT": 255,
        "PARENT": 255,
        "SSI_RECIPIENT": 255,
        "AGED": 255,
        "DISABLED": 255,
    }

"""MA Medicaid."""

from programs.programs.cross_white_label.medicaid.base import Medicaid
from programs.programs.federal.pe.member import Chip
from screener.models import HouseholdMember
import programs.framework.pe_dependencies as dependency


class MaMassHealth(Medicaid):
    program_code = "ma_mass_health"
    pe_inputs = [
        *Medicaid.pe_inputs,
        *Chip.pe_inputs,
        dependency.household.MaStateCodeDependency,
    ]
    pe_outputs = [
        *Medicaid.pe_outputs,
        *Chip.pe_outputs,
    ]

    medicaid_categories = {
        "NONE": 0,
        "ADULT": 419,
        "INFANT": 239,
        "YOUNG_CHILD": 239,
        "OLDER_CHILD": 239,
        "PREGNANT": 419,
        "YOUNG_ADULT": 419,
        "PARENT": 419,
        "SSI_RECIPIENT": 419,
        "AGED": 185,
        "DISABLED": 419,
    }

    chip_categories = {
        "CHILD": 239,
        "PREGNANT_STANDARD": 0,
        "PREGNANT_FCEP": 0,
        "NONE": 0,
    }

    def member_value(self, member: HouseholdMember):
        medicaid_value = super().member_value(member)

        if medicaid_value > 0:
            return medicaid_value

        chip_category = self.get_member_dependency_value(dependency.member.ChipCategory, member.id)
        return self.chip_categories[chip_category] * 12


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

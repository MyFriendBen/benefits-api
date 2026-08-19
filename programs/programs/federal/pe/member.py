from programs.framework.pe_base import PolicyEngineMembersCalculator
import programs.framework.pe_dependencies as dependency
from screener.models import HouseholdMember
from programs.programs.cross_white_label.medicaid.base import Medicaid
from programs.programs.cross_white_label.head_start.base import HeadStart


class Chip(PolicyEngineMembersCalculator, abstract=True):
    pe_name = "chip_category"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.PregnancyDependency,
        *Medicaid.pe_inputs,
    ]
    pe_outputs = [dependency.member.ChipCategory]

    # NOTE: Monthly
    chip_categories = {
        "CHILD": 0,
        "PREGNANT_STANDARD": 0,
        "PREGNANT_FCEP": 0,
        "NONE": 0,
    }

    def member_value(self, member: HouseholdMember):
        chip_category = self.get_member_dependency_value(dependency.member.ChipCategory, member.id)

        return self.chip_categories[chip_category] * 12


class PellGrant(PolicyEngineMembersCalculator):
    program_code = "pell_grant"
    pe_name = "pell_grant"
    pe_inputs = [
        dependency.member.PellGrantDependentAvailableIncomeDependency,
        dependency.member.PellGrantCountableAssetsDependency,
        dependency.member.CostOfAttendingCollegeDependency,
        dependency.member.PellGrantMonthsInSchoolDependency,
        dependency.tax.PellGrantPrimaryIncomeDependency,
        dependency.tax.PellGrantDependentsInCollegeDependency,
        dependency.member.TaxUnitDependentDependency,
        dependency.member.TaxUnitHeadDependency,
        dependency.member.TaxUnitSpouseDependency,
    ]
    pe_outputs = [dependency.member.PellGrant]

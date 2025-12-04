from programs.programs.policyengine.calculators.base import PolicyEngineMembersCalculator
import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.federal.pe.member import Ccdf, Chip, Medicaid, Wic, Ssi
from .spm import MaSnap, MaTafdc, MaEaedc
from screener.models import HouseholdMember


# NOTE: MassHealth is Medicaid in MA
class MaMassHealth(Medicaid):
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


# NOTE: MassHealth Limited is Emergency Medicaid in MA
class MaMassHealthLimited(Medicaid):
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


class MaWic(Wic):
    wic_categories = {
        "NONE": 0,
        "INFANT": 186,
        "CHILD": 77,
        "PREGNANT": 107,
        # NOTE: guesses based off Colorado
        "POSTPARTUM": 91,
        "BREASTFEEDING": 124,
    }


class MaCcdf(Ccdf):
    cost_by_age = (
        # cost, age
        (23_191, 2),
        (21_125, 3),
        (16_572, 4.5),
        (12_632, 14),
    )

    def child_care_cost(self, member: HouseholdMember):
        age = member.fraction_age()

        for [cost, age_limit] in self.cost_by_age:
            if age < age_limit:
                return cost

        return 0


class MaMbta(PolicyEngineMembersCalculator):
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.IsDisabledDependency,
        *MaSnap.pe_inputs,
        *MaTafdc.pe_inputs,
        *MaMassHealth.pe_inputs,
        *MaEaedc.pe_inputs,
    ]
    pe_outputs = [
        dependency.member.MaMbtaProgramsEligible,
        dependency.member.MaMbtaAgeEligible,
        dependency.member.MaSeniorCharlieCardEligible,
        dependency.member.MaTapCharlieCardEligible,
    ]

    amount = 60 * 12

    def member_value(self, member: HouseholdMember):
        mbta_programs_eligible = self.get_member_dependency_value(dependency.member.MaMbtaProgramsEligible, member.id)
        mbta_age_eligible = self.get_member_dependency_value(dependency.member.MaMbtaAgeEligible, member.id)
        mbta_eligible = mbta_programs_eligible and mbta_age_eligible
        senior_charlie_eligible = self.get_member_dependency_value(
            dependency.member.MaSeniorCharlieCardEligible, member.id
        )
        tap_charlie_eligible = self.get_member_dependency_value(dependency.member.MaTapCharlieCardEligible, member.id)

        if mbta_eligible or tap_charlie_eligible or senior_charlie_eligible:
            return self.amount

        return 0


class MaStateSupplementProgram(PolicyEngineMembersCalculator):
    pe_name = "ma_state_supplement"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.IsDisabledDependency,
        dependency.member.IsBlindDependency,
        dependency.member.SsiCountableResourcesDependency,
        *Ssi.pe_inputs,
    ]
    pe_outputs = [dependency.member.MaStateSupplementProgram]


class MaHeadStart(PolicyEngineMembersCalculator):
    pe_name = "head_start"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.household.MaStateCodeDependency,
        *dependency.irs_gross_income,
    ]
    pe_outputs = [dependency.member.HeadStart]


class MaEarlyHeadStart(PolicyEngineMembersCalculator):
    pe_name = "early_head_start"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.household.MaStateCodeDependency,
        *dependency.irs_gross_income,
    ]
    pe_outputs = [dependency.member.EarlyHeadStart]

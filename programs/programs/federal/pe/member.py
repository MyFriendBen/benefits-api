from programs.programs.policyengine.calculators.base import PolicyEngineMembersCalculator
import programs.programs.policyengine.calculators.dependencies as dependency
from screener.models import HouseholdMember


class Wic(PolicyEngineMembersCalculator):
    wic_categories = {
        "NONE": 0,
        "INFANT": 0,
        "CHILD": 0,
        "PREGNANT": 0,
        "POSTPARTUM": 0,
        "BREASTFEEDING": 0,
    }
    pe_name = "wic"
    pe_inputs = [
        dependency.member.PregnancyDependency,
        dependency.member.ExpectedChildrenPregnancyDependency,
        dependency.member.AgeDependency,
        dependency.spm.SchoolMealCountableIncomeDependency,
    ]
    pe_outputs = [dependency.member.Wic, dependency.member.WicCategory]

    def member_value(self, member: HouseholdMember):
        if self.get_member_variable(member.id) <= 0:
            return 0

        wic_category = self.get_member_dependency_value(dependency.member.WicCategory, member.id)
        return self.wic_categories[wic_category] * 12


class Medicaid(PolicyEngineMembersCalculator):
    pe_name = "medicaid"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.PregnancyDependency,
        dependency.member.SsiCountableResourcesDependency,
        dependency.member.IsDisabledDependency,
        *dependency.irs_gross_income,
    ]
    pe_outputs = [
        dependency.member.AgeDependency,
        dependency.member.Medicaid,
        dependency.member.MedicaidCategory,
        dependency.member.MedicaidSeniorOrDisabled,
    ]

    # NOTE: Monthly
    medicaid_categories = {
        "NONE": 0,
        "ADULT": 0,
        "INFANT": 0,
        "YOUNG_CHILD": 0,
        "OLDER_CHILD": 0,
        "PREGNANT": 0,
        "YOUNG_ADULT": 0,
        "PARENT": 0,
        "SSI_RECIPIENT": 0,
        "AGED": 0,
        "DISABLED": 0,
    }

    aged_min_age = 65

    def member_value(self, member: HouseholdMember):
        # In Policy Engine, senior and disabled are not included in the medicaid categories variable.
        # Instead, a separate variable is used to determine the medicaid eligiblity for a senior or disabled member.
        is_senior_or_disabled = self.get_member_dependency_value(dependency.member.MedicaidSeniorOrDisabled, member.id)

        if is_senior_or_disabled:
            if member.has_disability():
                return self.medicaid_categories["DISABLED"] * 12
            elif member.age >= self.aged_min_age:
                return self.medicaid_categories["AGED"] * 12

        if self.get_member_variable(member.id) <= 0:
            return 0

        medicaid_category = self.get_member_dependency_value(dependency.member.MedicaidCategory, member.id)

        return self.medicaid_categories[medicaid_category] * 12


class Chip(PolicyEngineMembersCalculator):
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


class Ssi(PolicyEngineMembersCalculator):
    pe_name = "ssi"
    pe_inputs = [
        dependency.member.SsiCountableResourcesDependency,
        dependency.member.SsiReportedDependency,
        dependency.member.IsBlindDependency,
        dependency.member.IsDisabledDependency,
        dependency.member.SsiEarnedIncomeDependency,
        dependency.member.SsiUnearnedIncomeDependency,
        dependency.member.AgeDependency,
        dependency.member.TaxUnitSpouseDependency,
        dependency.member.TaxUnitHeadDependency,
        dependency.member.TaxUnitDependentDependency,
    ]
    pe_outputs = [dependency.member.Ssi]


class CommoditySupplementalFoodProgram(PolicyEngineMembersCalculator):
    pe_name = "commodity_supplemental_food_program"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.spm.SchoolMealCountableIncomeDependency,
    ]
    pe_outputs = [dependency.member.CommoditySupplementalFoodProgram]


class Ccdf(PolicyEngineMembersCalculator):
    pe_name = "is_ccdf_eligible"
    pe_inputs = [
        dependency.spm.AssetsDependency,
        dependency.member.CcdfReasonCareEligibleDependency,
        dependency.member.EmploymentIncomeDependency,
        dependency.member.SelfEmploymentIncomeDependency,
        dependency.member.PensionIncomeDependency,
        dependency.member.InvestmentIncomeDependency,
        dependency.member.RentalIncomeDependency,
        dependency.member.MiscellaneousIncomeDependency,
    ]
    pe_outputs = [dependency.member.Ccdf]

    def child_care_cost(self, member: HouseholdMember) -> int:
        raise NotImplemented("Please define the 'child_care_cost' method")

    def member_value(self, member: HouseholdMember):
        if not self.get_member_variable(member.id):
            return 0

        return self.child_care_cost(member)


class EmergencyMedicaid(PolicyEngineMembersCalculator):
    """
    Federal Emergency Medicaid eligibility for undocumented immigrants.

    Based on 42 USC 1396b(v), Emergency Medicaid provides coverage for emergency
    medical conditions to individuals who would otherwise qualify for Medicaid
    but are ineligible due to immigration status.

    Eligibility requires:
    1. Immigration ineligibility for regular Medicaid
    2. Meeting all other Medicaid requirements (income, categorical eligibility)
    3. Having a qualifying emergency medical condition

    For screening purposes, we assume has_emergency_medical_condition=True since
    the actual emergency is verified at the point of care.

    State-specific implementations should set appropriate benefit amounts.
    """

    pe_name = "is_emergency_medicaid_eligible"
    pe_inputs = [
        *Medicaid.pe_inputs,
        dependency.member.HasEmergencyMedicalCondition,
    ]
    pe_outputs = [
        dependency.member.EmergencyMedicaidEligible,
    ]

    # Default amount - states should override with their specific values
    amount = 0

    def member_value(self, member: HouseholdMember):
        is_eligible = self.get_member_variable(member.id)

        if is_eligible:
            return self.amount

        return 0

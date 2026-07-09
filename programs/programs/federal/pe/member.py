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
        # PolicyEngine uses two separate pathways for Medicaid eligibility:
        # 1. "medicaid" variable - ACA expansion eligibility (138% FPL for adults under 65)
        # 2. "is_optional_senior_or_disabled_for_medicaid" - aged/disabled pathway
        #    (state-specific FPL thresholds, typically 74-100%)
        #
        # Seniors (65+) and disabled individuals must use the aged/disabled pathway,
        # as ACA expansion only applies to adults under 65.
        age = member.calc_age()
        is_senior = age is not None and age >= self.aged_min_age
        is_disabled = member.has_disability()

        if is_senior or is_disabled:
            qualifies_via_aged_disabled_pathway = self.get_member_dependency_value(
                dependency.member.MedicaidSeniorOrDisabled, member.id
            )
            if not qualifies_via_aged_disabled_pathway:
                return 0

            if is_disabled:
                return self.medicaid_categories["DISABLED"] * 12
            else:
                return self.medicaid_categories["AGED"] * 12

        # Non-senior, non-disabled members use regular Medicaid eligibility
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
        dependency.member.MeetsSsiDisabilityCriteriaDependency,
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


class HeadStart(PolicyEngineMembersCalculator):
    """
    Federal Head Start (ages 3-5). Eligibility and per-child value are computed by
    PolicyEngine's ``head_start`` variable. State subclasses add their state-code
    dependency; the rest of the inputs are shared. Categorical eligibility is fed
    by the SSI/SNAP/TANF inputs plus foster care.
    """

    pe_name = "head_start"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.FosterCareDependency,
        *dependency.irs_gross_income,
        dependency.member.Ssi,
        dependency.spm.Snap,
        dependency.spm.Tanf,
    ]
    pe_outputs = [dependency.member.HeadStart]


class EarlyHeadStart(PolicyEngineMembersCalculator):
    """
    Federal Early Head Start (birth to age 3, and pregnant women). Same computed
    eligibility/value model as ``HeadStart`` via PolicyEngine's ``early_head_start``
    variable, plus a pregnancy input (EHS serves pregnant women). State subclasses
    add their state-code dependency.
    """

    pe_name = "early_head_start"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.PregnancyDependency,
        dependency.member.FosterCareDependency,
        *dependency.irs_gross_income,
        dependency.member.Ssi,
        dependency.spm.Snap,
        dependency.spm.Tanf,
    ]
    pe_outputs = [dependency.member.EarlyHeadStart]


class Msp(PolicyEngineMembersCalculator):
    """
    Federal Medicare Savings Program (QMB/SLMB/QI). Eligibility, category, and value
    are computed by PolicyEngine's ``msp`` variable; MSP rules are federal, so state
    subclasses only add their state-code dependency and the state's Medicaid inputs
    (``msp`` gates QI on ``~is_medicaid_eligible`` and reads ``ssi_countable_resources``,
    both of which come from the Medicaid input set).

    Categories: QMB (≤100% FPL, Part A/B premiums + deductibles + coinsurance),
    SLMB (100-120% FPL, Part B premium), QI (120-135% FPL and not Medicaid-eligible,
    Part B premium).

    Limitations:
        - SSDI pathway partial: months_receiving_social_security_disability isn't collected,
          but IsMedicareEligibleDependency short-circuits when the user reports Medicare.
        - Assumes 40 quarters of covered employment (free Part A); ~99% of beneficiaries qualify.
        - Benefit value is premium savings only (no QMB deductible/coinsurance).
    """

    pe_name = "msp"
    # Shared inputs. State subclasses append their state-code dependency and the state's
    # Medicaid inputs (see e.g. TxMsp / KsMsp / IlMsp).
    pe_inputs = [
        # is_medicare_eligible: overrides PE when the user reports Medicare
        dependency.member.IsMedicareEligibleDependency,
        dependency.member.AgeDependency,
        dependency.member.SsdiReportedDependency,
        # msp_countable_income (SSI methodology)
        dependency.member.SsiEarnedIncomeDependency,
        dependency.member.SsiUnearnedIncomeDependency,
        dependency.spm.CashAssetsDependency,
        # 40 quarters -> free Part A -> QMB value is the Part B premium
        dependency.member.MedicareQuartersOfCoverageDependency,
        # is_medicaid_eligible for the QI exclusion; overrides when the user reports Medicaid
        dependency.member.IsMedicaidEligibleDependency,
    ]
    pe_outputs = [
        dependency.member.MspEligible,
        dependency.member.MspCategory,
        dependency.member.Msp,
    ]

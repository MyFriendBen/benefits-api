from programs.programs.helpers import snap_ineligible_student
from .base import Member


class AgeDependency(Member):
    field = "age"
    dependencies = ("age",)

    def value(self):
        return self.member.age


class PregnancyDependency(Member):
    field = "is_pregnant"

    def value(self):
        return self.member.pregnant or False


class ExpectedChildrenPregnancyDependency(Member):
    field = "current_pregnancies"

    def value(self):
        return 1 if self.member.pregnant else 0


class FullTimeCollegeStudentDependency(Member):
    field = "is_full_time_college_student"

    def value(self):
        return self.member.student or False


class TaxUnitHeadDependency(Member):
    field = "is_tax_unit_head"
    dependencies = ("relationship",)

    def value(self):
        if self.member.is_head():
            return True

        other_unit = self.screen.other_tax_unit_structure()

        if other_unit["head"] is None:
            return False

        return other_unit["head"].id == self.member.id


class TaxUnitSpouseDependency(Member):
    field = "is_tax_unit_spouse"
    dependencies = ("relationship",)

    def value(self):
        if self.member.is_spouse():
            return True

        other_unit = self.screen.other_tax_unit_structure()

        if other_unit["spouse"] is None:
            return False

        return other_unit["spouse"].id == self.member.id


class TaxUnitDependentDependency(Member):
    field = "is_tax_unit_dependent"
    dependencies = (
        "relationship",
        "age",
        "income_amount",
        "income_frequency",
    )

    def value(self):
        if self.member.is_dependent():
            return True

        other_unit = self.screen.other_tax_unit_structure()

        for member in other_unit["dependents"]:
            if member.id == self.member.id:
                return True

        return False


class WicCategory(Member):
    field = "wic_category"


class MedicaidCategory(Member):
    field = "medicaid_category"


class MedicaidSeniorOrDisabled(Member):
    field = "is_optional_senior_or_disabled_for_medicaid"


class Wic(Member):
    field = "wic"


class Medicaid(Member):
    field = "medicaid"


class Ssi(Member):
    """
    SSI as both PE input and output.

    - If user reports SSI: use reported value
    - If no reported SSI: return None so PE calculates eligibility

    Warning: When PE calculates SSI, the value sometimes counts as unearned
    income for downstream calculations (e.g., IL AABD).
    """

    field = "ssi"
    dependencies = (
        "income_type",
        "income_amount",
        "income_frequency",
    )

    def value(self):
        ssi = self.member.calc_gross_income("yearly", ["sSI"])
        return None if ssi == 0 else ssi


class IsDisabledDependency(Member):
    field = "is_disabled"

    def value(self):
        # per discussion with PolicyEngine 01/02/2026, should include blindness in is_disabled
        return self.member.disabled or self.member.long_term_disability or self.member.visually_impaired


# The Member class runs once per each household member, to ensure that the medical expenses
# are only counted once and only if a member is elderly or disabled; the medical expense is divided
# by the total number of elderly or disabled members.
class MedicalExpenseDependency(Member):
    field = "medical_out_of_pocket_expenses"
    dependencies = ["age"]

    def value(self):
        elderly_or_disabled_members = [
            member for member in self.screen.household_members.all() if member.age >= 60 or member.has_disability()
        ]
        count_of_elderly_or_disabled_members = len(elderly_or_disabled_members)

        if self.member.age >= 60 or self.member.has_disability():
            return self.screen.calc_expenses("yearly", ["medical"]) / count_of_elderly_or_disabled_members

        return 0


class PropertyTaxExpenseDependency(Member):
    """
    Property tax expense for PolicyEngine tax calculations.

    PE treats this as a person-level field for state tax calculations.
    We split the household's total property tax between head and spouse only
    (the tax filers), not all adults, since this is used for tax filing purposes.
    """

    field = "real_estate_taxes"

    def value(self):
        # Only assign to head and spouse (tax filers)
        if not (self.member.is_head() or self.member.is_spouse()):
            return 0

        total_property_tax = self.screen.calc_expenses("yearly", ["propertyTax"])

        # If married/joint filing, split between head and spouse
        if self.screen.is_joint():
            return int(total_property_tax / 2)

        return int(total_property_tax)


class IsBlindDependency(Member):
    field = "is_blind"

    def value(self):
        return self.member.visually_impaired or False


class SsiReportedDependency(Member):
    field = "ssi_reported"
    dependencies = (
        "income_type",
        "income_amount",
        "income_frequency",
    )

    def value(self):
        return self.member.calc_gross_income("yearly", ["sSI"])


class SsdiReportedDependency(Member):
    # Amount in "Social Security disability benefits (SSDI)"
    field = "social_security_disability"
    dependencies = (
        "income_type",
        "income_amount",
        "income_frequency",
    )

    def value(self):
        return self.member.calc_gross_income("yearly", ["sSDisability"])


class SsiCountableResourcesDependency(Member):
    field = "ssi_countable_resources"
    dependencies = (
        "household_assets",
        "age",
    )

    def value(self):
        ssi_assets = 0
        if self.member.age >= 19:
            ssi_assets = self.screen.household_assets / self.screen.num_adults()

        return int(ssi_assets)


class SsiAmountIfEligible(Member):
    field = "ssi_amount_if_eligible"


class Andcs(Member):
    field = "co_state_supplement"


class Oap(Member):
    field = "co_oap"


class FamilyAffordabilityTaxCredit(Member):
    field = "co_family_affordability_credit"


class CareWorkerEligibleDependency(Member):
    field = "co_care_worker_credit_eligible_care_worker"
    dependencies = ("is_care_worker",)

    def value(self):
        return self.member.is_care_worker or False


class PellGrant(Member):
    field = "pell_grant"


class PellGrantDependentAvailableIncomeDependency(Member):
    field = "pell_grant_dependent_available_income"
    dependencies = (
        "income_type",
        "income_amount",
        "income_frequency",
    )

    def value(self):
        return int(self.member.calc_gross_income("yearly", ["all"]))


class PellGrantCountableAssetsDependency(Member):
    field = "pell_grant_countable_assets"
    dependencies = ("household_assets",)

    def value(self):
        return int(self.screen.household_assets)


class CostOfAttendingCollegeDependency(Member):
    field = "cost_of_attending_college"
    dependencies = ("age", "student")

    def value(self):
        return 22_288 * (self.member.age >= 16 and self.member.student)


class PellGrantMonthsInSchoolDependency(Member):
    field = "pell_grant_months_in_school"

    def value(self):
        return 9


class ChpEligible(Member):
    field = "co_chp_eligible"


class CommoditySupplementalFoodProgram(Member):
    field = "commodity_supplemental_food_program"


class SnapChildSupportDependency(Member):
    field = "child_support_expense"
    dependencies = ("age", "household_size")

    def value(self):
        return self.screen.calc_expenses("yearly", ["childSupport"]) / self.screen.household_size


class SnapIneligibleStudentDependency(Member):
    field = "is_snap_ineligible_student"
    dependencies = ("age",)

    # PE does not take the age of the children into acount, so we calculate this ourselves
    def value(self):
        return snap_ineligible_student(self.screen, self.member)


class TotalHoursWorkedDependency(Member):
    field = "weekly_hours_worked_before_lsr"
    dependencies = ("income_frequency",)

    minimum_wage = 7.25
    work_weeks_in_month = 4

    def value(self):
        hours = 0

        for income in self.member.income_streams.all():
            if income.frequency == "hourly":
                hours += int(income.hours_worked)
                continue

            # aproximate weekly hours using the minimum wage in MA
            hours += int(income.monthly()) / self.minimum_wage / self.work_weeks_in_month

        return hours


class MaTotalHoursWorkedDependency(TotalHoursWorkedDependency):
    minimum_wage = 15


class MaTanfCountableGrossEarnedIncomeDependency(Member):
    field = "ma_tcap_gross_earned_income"
    dependencies = (
        "income_type",
        "income_amount",
        "income_frequency",
    )

    def value(self):
        return int(self.member.calc_gross_income("yearly", ["earned"]))


class MaTanfCountableGrossUnearnedIncomeDependency(Member):
    field = "ma_tcap_gross_unearned_income"
    dependencies = (
        "income_type",
        "income_amount",
        "income_frequency",
    )

    def value(self):
        return int(self.member.calc_gross_income("yearly", ["unearned"], exclude=["cashAssistance"]))


class MaTapCharlieCardEligible(Member):
    field = "ma_mbta_tap_charlie_card_eligible"


class MaSeniorCharlieCardEligible(Member):
    field = "ma_mbta_senior_charlie_card_eligible"


class MaMbtaProgramsEligible(Member):
    field = "ma_mbta_enrolled_in_applicable_programs"


class MaMbtaAgeEligible(Member):
    field = "ma_mbta_income_eligible_reduced_fare_eligible"


class Ccdf(Member):
    field = "is_ccdf_eligible"


class CcdfReasonCareEligibleDependency(Member):
    field = "is_ccdf_reason_for_care_eligible"

    def value(self):
        return True


class MaStateSupplementProgram(Member):
    field = "ma_state_supplement"


class ChipCategory(Member):
    field = "chip_category"


class Chip(Member):
    field = "chip"


class IncomeDependency(Member):
    dependencies = (
        "income_type",
        "income_amount",
        "income_frequency",
    )
    income_types = []

    def value(self):
        return int(self.member.calc_gross_income("yearly", self.income_types))


class EmploymentIncomeDependency(IncomeDependency):
    field = "employment_income"
    income_types = ["wages"]


class SelfEmploymentIncomeDependency(IncomeDependency):
    field = "self_employment_income"
    income_types = ["selfEmployment"]


class RentalIncomeDependency(IncomeDependency):
    field = "rental_income"
    income_types = ["rental"]


class PensionIncomeDependency(IncomeDependency):
    field = "taxable_pension_income"
    income_types = ["pension", "veteran"]


class SocialSecurityIncomeDependency(IncomeDependency):
    field = "social_security"
    income_types = ["sSDisability", "sSSurvivor", "sSRetirement", "sSDependent"]


class InvestmentIncomeDependency(IncomeDependency):
    field = "capital_gains"
    income_types = ["investment"]


class MiscellaneousIncomeDependency(IncomeDependency):
    field = "miscellaneous_income"
    income_types = ["gifts"]


class UnemploymentIncomeDependency(IncomeDependency):
    field = "unemployment_compensation"
    income_types = ["unemployment"]


class WorkersCompensationDependency(IncomeDependency):
    field = "workers_compensation"
    income_types = ["workersComp"]


class AlimonyIncomeDependency(IncomeDependency):
    field = "alimony_income"
    income_types = ["alimony"]


class RetirementDistributionsDependency(IncomeDependency):
    field = "taxable_ira_distributions"
    income_types = ["deferredComp"]


class SsiEarnedIncomeDependency(IncomeDependency):
    field = "ssi_earned_income"
    income_types = ["earned"]


class SsiUnearnedIncomeDependency(IncomeDependency):
    field = "ssi_unearned_income"
    income_types = ["unearned"]


class IlAabd(Member):
    field = "il_aabd_person"


class RentDependency(Member):
    """
    Rent expense for PolicyEngine tax calculations.

    PE treats this as a person-level field for state tax calculations.
    We split the household's total rent between head and spouse only
    (the tax filers), not all adults, since this is used for tax filing purposes.
    """

    field = "rent"

    def value(self):
        # Only assign to head and spouse (tax filers)
        if not (self.member.is_head() or self.member.is_spouse()):
            return 0

        total_rent = self.screen.calc_expenses("yearly", ["rent"])

        # If married/joint filing, split between head and spouse
        if self.screen.is_joint():
            return int(total_rent / 2)

        return int(total_rent)


class IlHbwdEligible(Member):
    """Illinois HBWD eligibility determination (boolean)."""

    field = "il_hbwd_eligible"


class IlHbwdPremium(Member):
    """
    Illinois HBWD monthly premium amount (negative value).

    This represents the PREMIUM that the user will pay for HBWD insurance,
    not the value of the benefit itself. Will be a negative number.
    """

    field = "il_hbwd_person"


class HeadStart(Member):
    field = "head_start"


class EarlyHeadStart(Member):
    field = "early_head_start"


class IlBccFemaleDependency(Member):
    field = "is_female"

    def value(self):
        # We don't collect sex
        # Hardcode to True so that all households are shown the IBCCP program in results
        return True


class IlBccInsuranceEligibleDependency(Member):
    """
    Whether the member is insurance-eligible for IBCCP.
    Returns True if they DON'T have Medicaid, All Kids/CHP, or other HFS insurance.
    This matches PolicyEngine's il_bcc_insurance_eligible formula:
        ~(is_medicaid_eligible | has_bcc_qualifying_coverage)
    """

    field = "il_bcc_insurance_eligible"

    def value(self):
        # Return True if they DON'T have HFS insurance (i.e., eligible for IBCCP)
        has_hfs_insurance = self.member.has_insurance_types(("medicaid", "chp"))
        return not has_hfs_insurance


class IlBccEligible(Member):
    field = "il_bcc_eligible"


class IlFppEligible(Member):
    """Output dependency for IL Family Planning Program eligibility."""

    field = "il_fpp_eligible"


class IlMpeEligible(Member):
    field = "il_mpe_eligible"


class EmergencyMedicaidEligible(Member):
    """
    Federal Emergency Medicaid eligibility for undocumented immigrants.
    Based on 42 USC 1396b(v) - covers emergency medical conditions only.
    """

    field = "is_emergency_medicaid_eligible"


class HasEmergencyMedicalCondition(Member):
    """
    Input dependency for Emergency Medicaid - indicates whether a person
    has a qualifying emergency medical condition.

    For screening purposes, we assume True to show potential eligibility.
    Actual eligibility is determined at the point of care.
    """

    field = "has_emergency_medical_condition"

    def value(self):
        # Always return True for screening - the actual emergency condition
        # is verified at the healthcare provider, not during benefits screening
        return True

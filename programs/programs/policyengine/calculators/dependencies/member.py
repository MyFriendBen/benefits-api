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
        return self.member.disabled or self.member.long_term_disability


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
    field = "real_estate_taxes"
    dependencies = ["age"]

    def value(self):
        if self.member.age >= 18:
            return self.screen.calc_expenses("yearly", ["propertyTax"]) / self.screen.num_adults(18)

        return 0


class IsBlindDependency(Member):
    field = "is_blind"

    def value(self):
        return self.member.visually_impaired or False


class SsiReportedDependency(Member):
    field = "ssi_reported"

    def value(self):
        # Policy Engine uses this value for is_ssi_disabled, but it does not apply to MFB
        return 0


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


class SsiEarnedIncomeDependency(IncomeDependency):
    field = "ssi_earned_income"
    income_types = ["earned"]


class SsiUnearnedIncomeDependency(IncomeDependency):
    field = "ssi_unearned_income"
    income_types = ["unearned"]


class IlAabdGrossEarnedIncomeDependency(Member):
    field = "il_aabd_gross_earned_income"
    dependencies = (
        "income_type",
        "income_amount",
        "income_frequency",
    )

    def value(self):
        return int(self.member.calc_gross_income("yearly", ["earned"]))


class IlAabdGrossUnearnedIncomeDependency(Member):
    field = "il_aabd_gross_unearned_income"
    dependencies = (
        "income_type",
        "income_amount",
        "income_frequency",
    )

    def value(self):
        return int(self.member.calc_gross_income("yearly", ["unearned"], exclude=["cashAssistance"]))


class IlAabd(Member):
    field = "il_aabd_person"

class HeadStart(Member):
    field = "head_start"

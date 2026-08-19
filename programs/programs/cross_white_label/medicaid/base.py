"""Medicaid."""

from screener.models import HouseholdMember
from programs.framework.pe_base import PolicyEngineMembersCalculator
import programs.framework.pe_dependencies as dependency


class Medicaid(PolicyEngineMembersCalculator, abstract=True):
    pe_name = "medicaid"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.PregnancyDependency,
        dependency.member.SsiCountableResourcesDependency,
        dependency.member.IsDisabledDependency,
        *dependency.irs_gross_income,
        # medicaid_category has an SSI-recipient pathway, which must not fire off
        # simulated SSI.
        *dependency.receipt_contract,
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

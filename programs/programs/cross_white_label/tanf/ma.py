"""MaTafdc."""

from programs.framework.pe_base import PolicyEngineSpmCalulator
import programs.framework.pe_dependencies as dependency


class MaTafdc(PolicyEngineSpmCalulator):
    program_code = "ma_tafdc"
    pe_name = "ma_tafdc"
    pe_inputs = [
        dependency.spm.PreSubsidyChildcareExpensesDependency,
        dependency.member.MaTanfCountableGrossEarnedIncomeDependency,
        dependency.member.MaTanfCountableGrossUnearnedIncomeDependency,
        dependency.member.TaxUnitDependentDependency,
        dependency.member.MaTotalHoursWorkedDependency,
        dependency.member.AgeDependency,
        dependency.member.PregnancyDependency,
        dependency.member.MaTafdcPregnancyEligibleDependency,
        # ma_tafdc_age_limit and ma_tafdc_pregnancy_eligible both read
        # is_in_secondary_school, which has no PE default. Listed here rather than
        # inherited: ma_tafdc is a self-contained MA model (adds ma_tafdc_if_claimed,
        # defined_for ma_tafdc_exceeds_eaedc) that reads none of the federal chain the Tanf
        # base supplies — not is_person_demographic_tanf_eligible, nor any of the
        # SNAP/TANF receipt inputs — so subclassing it would send inert fields.
        dependency.member.InSecondarySchoolDependency,
        dependency.household.IsInPublicHousingDependency,
        dependency.household.MaStateCodeDependency,
    ]

    pe_outputs = [dependency.spm.MaTafdc]

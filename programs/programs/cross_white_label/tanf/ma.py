"""MaTafdc."""

from programs.framework.pe_base import PolicyEngineSpmCalulator
import programs.framework.pe_dependencies as dependency


class MaTafdc(PolicyEngineSpmCalulator):
    """
    Massachusetts TAFDC.

    Does not subclass ``Tanf``: ``ma_tafdc`` is a self-contained model that reads none of the
    federal chain the base supplies, so inheriting it would send inert fields. Inputs the
    base would have carried are therefore listed here.

    ``InSecondarySchoolDependency`` changes ``ma_tafdc_age_limit``, which had been reading the
    PE variable's absent default of False and so applied the non-student dependent limit to
    everyone. It does not affect ``ma_tafdc_pregnancy_eligible``, whose formula reads the same
    variable but is overridden by ``MaTafdcPregnancyEligibleDependency`` sending the output
    directly. No scenario in this suite covers the age-limit change.
    """

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
        dependency.member.InSecondarySchoolDependency,
        dependency.household.IsInPublicHousingDependency,
        dependency.household.MaStateCodeDependency,
    ]

    pe_outputs = [dependency.spm.MaTafdc]

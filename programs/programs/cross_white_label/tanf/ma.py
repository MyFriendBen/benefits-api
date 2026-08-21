"""MaTafdc."""

from programs.framework.pe_base import PolicyEngineSpmCalulator
import programs.framework.pe_dependencies as dependency


class MaTafdc(PolicyEngineSpmCalulator):
    """
    Massachusetts TAFDC.

    Does not subclass ``Tanf``: ``ma_tafdc`` is a self-contained model that reads none of the
    federal chain the base supplies, so inheriting it would send inert fields. Inputs the
    base would have carried are therefore listed here.

    ``InSecondarySchoolDependency`` changes two outcomes, because the PE variable it feeds had
    no default and so read False for everyone. ``ma_tafdc_age_limit`` now uses the student
    dependent limit, and ``ma_tafdc_pregnancy_eligible``'s teen branch becomes reachable — a
    pregnant 14-to-18-year-old qualifies from pregnancy month 1 rather than month 5. Both
    widen eligibility; neither has a scenario in this suite.
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

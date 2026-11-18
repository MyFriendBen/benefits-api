"""NC TANF."""

from programs.programs.cross_white_label.tanf.base import Tanf
import programs.framework.pe_dependencies as dependency


class NcTanf(Tanf):
    """
    North Carolina Work First, via PolicyEngine's ``nc_tanf``.

    Income is sent per person and PE derives ``nc_tanf_countable_earned_income`` and
    ``nc_tanf_countable_gross_unearned_income`` itself. That is what applies its exclusions
    for children's earnings, SSI recipients' income and 27.5% of gross earnings: PE skips them
    whenever those two aggregates are sent, so do not send them (MFB-2463).

    Child support received counts in full unless the household already receives Work First, which
    PE reads from the receipt contract.

    Gifts (``miscellaneous_income``) are deliberately not sent: PE counts it as unearned for
    NC, but we have always excluded gifts from NC countable income. SSI, ``cashAssistance``
    and COS disability are never sent, which keeps them out as before.
    """

    program_code = "nc_tanf"
    pe_name = "nc_tanf"
    pe_inputs = [
        *Tanf.pe_inputs,
        dependency.household.NcStateCodeDependency,
        *dependency.irs_gross_income,
        dependency.member.AlimonyIncomeDependency,
        dependency.member.ChildSupportReceivedDependency,
    ]

    pe_outputs = [dependency.spm.NcTanf]

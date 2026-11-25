"""NC TANF."""

from programs.programs.cross_white_label.tanf.base import Tanf
import programs.framework.pe_dependencies as dependency


class NcTanf(Tanf):
    """
    North Carolina Work First, via PolicyEngine's ``nc_tanf``.

    There is no NC spec yet, so each choice below records the reading it rests on (WF-114,
    "Income and Budgeting", January 2024 edition) for whoever writes one.

    Earned income goes to PE per person and PE derives ``nc_tanf_countable_earned_income``, which is
    what applies its exclusions: 27.5% of gross earnings, children's earnings, and SSI recipients'
    income. PE skips those exclusions if that aggregate is sent, so do not send it.

    Rental, boarder and roomer income is sent as ``self_employment_income`` because WF-114 counts it
    as earned. That field is shared by every program on the screen, so for a household with such
    income this program's value differs from the other NC programs' and the payload splits into an
    extra PolicyEngine request.

    Unearned income is sent as our own total (``NcTanfCountableGrossUnearnedIncomeDependency``),
    because PE's NC list omits types WF-114 counts: investment, retirement withdrawals, and workers'
    compensation. The total leaves out SSI recipients' income, General Assistance
    (``cashAssistanceOther``), and the household's own grant. Decisions it rests on:

    * Child support counts for every household. WF-114 lists it as unearned with no exception for
      households already on Work First; PE excludes it for those, and we do not.
    * All workers' compensation is unearned. WF-114 treats it as earned when it is fully employer
      funded and the person still works there, but the screener cannot tell which.
    * Retirement withdrawals count as unearned. WF-114 has no row for IRA or 401(k) withdrawals; the
      nearest is "Retirement benefits".
    * Gifts do not count, as before. WF-114 excludes only gifts for specific special occasions, which
      the screener cannot distinguish.
    * Someone who reports their own SSI amount is treated as an SSI recipient. A household that only
      ticks the SSI tile names no member, so no one is excluded. PolicyEngine removes the recipient
      from the Work First unit, not only their income, so the value is for the remaining members: a
      parent on SSI with one child returns the grant for a unit of 1, not a unit of 2.
    """

    program_code = "nc_tanf"
    pe_name = "nc_tanf"
    pe_inputs = [
        *Tanf.pe_inputs,
        dependency.household.NcStateCodeDependency,
        dependency.member.EmploymentIncomeDependency,
        dependency.member.SelfEmploymentWithRentalAndBoarderIncomeDependency,
        dependency.spm.NcTanfCountableGrossUnearnedIncomeDependency,
    ]

    pe_outputs = [dependency.spm.NcTanf]

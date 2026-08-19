"""SSI."""

from programs.framework.pe_base import PolicyEngineMembersCalculator
import programs.framework.pe_dependencies as dependency


class Ssi(PolicyEngineMembersCalculator):
    program_code = "ssi"
    # PolicyEngine gates `ssi` on the take-up flag, so it reads 0 for anyone reporting no SSI —
    # exactly the people this program should be recommended to — and for reporters it just
    # echoes back the amount they told us. Neither is the entitlement worth showing; the
    # ungated output is.
    pe_name = "ssi_if_takes_up"
    pe_inputs = [
        dependency.member.SsiCountableResourcesDependency,
        *dependency.receipt_contract,
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
    pe_outputs = [dependency.member.SsiIfTakesUp]

"""AidToTheNeedyAndDisabled."""

from programs.framework.pe_base import PolicyEngineMembersCalculator
import programs.framework.pe_dependencies as dependency


class AidToTheNeedyAndDisabled(PolicyEngineMembersCalculator):
    program_code = "andcs"
    pe_name = "co_state_supplement"
    pe_inputs = [
        dependency.member.SsiCountableResourcesDependency,
        # co_state_supplement tops up SSI, so it reads the `ssi` amount the receipt
        # contract supplies (reported where reported, simulated-and-suppressed otherwise).
        *dependency.receipt_contract,
        dependency.member.IsBlindDependency,
        dependency.member.IsDisabledDependency,
        dependency.member.SsiEarnedIncomeDependency,
        dependency.member.SsiUnearnedIncomeDependency,
        dependency.member.AgeDependency,
        dependency.member.TaxUnitSpouseDependency,
        dependency.member.TaxUnitHeadDependency,
        dependency.member.TaxUnitDependentDependency,
        dependency.household.CoStateCodeDependency,
    ]
    pe_outputs = [dependency.member.Andcs]

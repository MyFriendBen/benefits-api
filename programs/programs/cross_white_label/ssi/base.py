"""The PolicyEngine SSI input bundle."""

from programs.framework.pe_base import PolicyEngineMembersCalculator
import programs.framework.pe_dependencies as dependency


class Ssi(PolicyEngineMembersCalculator, abstract=True):
    """
    The inputs PolicyEngine needs to model SSI for a household, shared by the programs whose
    own formula reads PolicyEngine's SSI: Massachusetts' state supplement and EAEDC compose
    ``Ssi.pe_inputs`` into their requests. SSI itself is computed by ``FederalSsi``
    (``programs/programs/white_labels/federal/ssi``) and backs no PolicyEngine row, so this
    class is abstract.

    ``pe_name`` and ``pe_outputs`` name PolicyEngine's ungated SSI output: ``ssi`` is gated on
    the take-up flag, so it reads 0 for anyone reporting no SSI, while ``ssi_if_takes_up`` is
    the entitlement.
    """

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

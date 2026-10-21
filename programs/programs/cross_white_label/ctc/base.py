"""Shared PolicyEngine inputs for the state child tax credits."""

from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
import programs.framework.pe_dependencies as dependency


class Ctc(PolicyEngineTaxUnitCalulator, abstract=True):
    """
    The PolicyEngine inputs a child tax credit is computed from: each member's age, the
    tax unit's dependent and spouse structure, and every IRS gross income stream.

    Backs no program of its own. The federal credit is `FederalCtc`, an MFB calculator on
    the federal white label; this class remains for the state credits (`Coctc`, `Ilctc`)
    that compose their PolicyEngine payload from these inputs plus a state code.
    """

    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.TaxUnitDependentDependency,
        dependency.member.TaxUnitSpouseDependency,
        *dependency.irs_gross_income,
    ]

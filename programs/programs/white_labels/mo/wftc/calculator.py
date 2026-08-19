"""MoWftc."""

from programs.programs.cross_white_label.eitc.base import Eitc
from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
import programs.framework.pe_dependencies as dependency


class MoWftc(PolicyEngineTaxUnitCalulator):
    """
    Missouri Working Family Tax Credit — state EITC piggyback.

    A thin wrapper: PolicyEngine's ``mo_wftc`` models the whole credit, including the
    eligibility gate, the year-specific rate, and the liability cap net of the property
    tax credit. See ``programs/programs/mo/wftc/spec.md`` for the rules, the accepted
    approximations, and the screener gaps this does not block on.
    """

    program_code = "mo_wftc"

    pe_name = "mo_wftc"
    pe_inputs = [
        *Eitc.pe_inputs,
        # Not in the federal Eitc set, and the liability cap is computed after the
        # property tax credit, which PolicyEngine derives from real_estate_taxes.
        dependency.member.PropertyTaxExpenseDependency,
        dependency.household.MoStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.MoWftc]

"""MoWftc."""

from programs.programs.cross_white_label.eitc.base import Eitc
from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
import programs.framework.pe_dependencies as dependency


class MoWftc(PolicyEngineTaxUnitCalulator):
    """
    Missouri Working Family Tax Credit — state EITC piggyback.

    A thin wrapper: PolicyEngine's ``mo_wftc`` models the whole credit, including the
    eligibility gate, the year-specific rate, and the liability cap net of the property
    tax credit. See ``programs/programs/white_labels/mo/wftc/spec.md`` for the rules, the accepted
    approximations, and the screener gaps this does not block on.
    """

    program_code = "mo_wftc"

    pe_name = "mo_wftc"
    pe_inputs = [
        # The federal set, but with age on December 31 of the tax year rather than on the
        # screening date. A household files the year just ended, so a child who turned 19
        # since is still a qualifying child for it.
        *[dep for dep in Eitc.pe_inputs if dep is not dependency.member.AgeDependency],
        dependency.member.AgeAtEndOfClaimYearDependency,
        # Full-time students under 24 are qualifying children. The SNAP, TANF and Medicaid
        # inputs that also send it run on the current year, so it never reaches this
        # program's tax-year period unless declared here.
        dependency.member.FullTimeCollegeStudentDependency,
        # Not in the federal Eitc set, and the liability cap is computed after the
        # property tax credit, which PolicyEngine derives from real_estate_taxes and rent.
        dependency.member.PropertyTaxExpenseDependency,
        dependency.member.RentDependency,
        dependency.household.MoStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.MoWftc]

from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
import programs.framework.pe_dependencies as dependency
from programs.programs.cross_white_label.cdcc.base import Cdcc
from programs.programs.cross_white_label.eitc.base import Eitc
from programs.programs.cross_white_label.ctc.base import Ctc
from programs.programs.cross_white_label.aca.base import Aca


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


class MoPts(PolicyEngineTaxUnitCalulator):
    """
    Missouri Property Tax Credit, the "Circuit Breaker".

    See ``programs/programs/mo/pts/spec.md`` for the rule and the scenarios. PolicyEngine
    models it in full, so this supplies inputs and reads the result.

    Six inputs replace or supplement the usual ones, each because a shared dependency sends
    the right dollars to a PolicyEngine variable this formula does not read. The reason is
    on each dependency class; ``spec.md`` records which scenario caught it.

    The credit floors at $0 for a household that satisfies every eligibility gate, so the
    base class's ``value > 0`` reports such a household ineligible. That is the intended
    result: a $0 credit is filtered from the results page either way, and telling someone
    they qualify for nothing would only invite a pointless filing.
    """

    program_code = "mo_pts"

    pe_name = "mo_property_tax_credit"
    pe_inputs = [
        dependency.member.AgeAtEndOf2026Dependency,
        dependency.member.TaxUnitHeadDependency,
        dependency.member.TaxUnitSpouseDependency,
        dependency.member.TaxUnitDependentDependency,
        dependency.member.IsDisabledDependency,
        dependency.member.IsFullyDisabledServiceConnectedVeteranDependency,
        dependency.member.PropertyTaxExpenseDependency,
        dependency.member.RentDependency,
        dependency.member.Ssi,
        dependency.member.VeteransBenefitsDependency,
        dependency.member.PensionIncomeWithoutVeteranDependency,
        dependency.member.EmploymentIncomeDependency,
        dependency.member.SelfEmploymentIncomeDependency,
        dependency.member.RentalIncomeDependency,
        dependency.member.SocialSecurityIncomeDependency,
        dependency.member.SocialSecuritySurvivorsIncomeDependency,
        dependency.member.UnemploymentIncomeDependency,
        dependency.member.InvestmentIncomeDependency,
        dependency.member.RetirementDistributionsDependency,
        dependency.household.MoStateCodeDependency,
    ]
    pe_outputs = [
        dependency.tax.MoPropertyTaxCredit,
    ]

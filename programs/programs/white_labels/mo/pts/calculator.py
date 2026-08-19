"""MoPts."""

from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
import programs.framework.pe_dependencies as dependency


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

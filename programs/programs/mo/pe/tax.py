from programs.programs.federal.pe.tax import Aca
from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
import programs.framework.pe_dependencies as dependency
from programs.programs.cross_white_label.cdcc.base import Cdcc
from programs.programs.cross_white_label.eitc.base import Eitc
from programs.programs.cross_white_label.ctc.base import Ctc


class MoAca(Aca):
    """
    Missouri ACA Premium Tax Credit — the federal ``Aca`` PE calculator plus the two
    inputs Missouri's value depends on.

    Nothing about *whether* a Missouri household qualifies is state-specific: Missouri
    uses HealthCare.gov rather than a state-based exchange, so eligibility is federal end
    to end (26 U.S.C. 36B) and lives entirely in PolicyEngine. What varies is the dollar
    value, and it varies by county.

    Two inputs beyond the federal base class:

    - ``MoCountyDependency`` — the benchmark premium (SLCSP) is set per *rating area*, and
      PolicyEngine keys that off ``county_str``, not ``zip_code``. The federal base already
      sends ``zip_code``, but PE ignores it for this purpose: holding everything else
      constant, Jackson and Boone counties both return an SLCSP of $9,362 on zip alone.
      With county supplied they correctly diverge to $6,856 (Jackson) and $8,580 (Boone) —
      a $1,724/year swing in the benchmark, which is the whole of Missouri's state-specific
      variance. See ``MoCountyDependency`` for the St. Louis City special case.
    - ``HasEsiDependency`` — employer-sponsored coverage is a statutory disqualifier that
      PolicyEngine applies only if we tell it. Nothing else in our codebase wires the
      screener's health-insurance field to PE, so without this an applicant with job-based
      coverage is scored as PTC-eligible.

    Both gaps also affect ``TxAca``/``NcAca``/``IlAca``/``MaAca``, which pass neither input.
    Fixing them changes results for four already-shipped programs, so that is deliberately
    out of scope here and tracked separately.

    Known limitation, not corrected here: PolicyEngine's modeled SLCSP runs slightly below
    the CMS-filed benchmark (about 1.6% low in Jackson County, ~$110/year), and the credit
    is a benchmark-based *maximum* rather than the household's final legal credit — the
    statute caps it at the premium of the plan actually chosen. The program copy frames the
    result as an estimated maximum accordingly.
    """

    program_code = "mo_aca_ptc"

    pe_inputs = [
        *Aca.pe_inputs,
        dependency.household.MoStateCodeDependency,
        dependency.household.MoCountyDependency,
        dependency.member.HasEsiDependency,
    ]


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

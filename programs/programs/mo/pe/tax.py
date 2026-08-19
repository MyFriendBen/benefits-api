from programs.framework.base import Eligibility
from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
from programs.framework.pe_dependencies.constants import ALL_TAX_UNITS
from programs.programs.federal.pe.tax import Aca, Cdcc, Ctc, Eitc
import programs.framework.pe_dependencies as dependency


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


class MoCtc(Ctc):
    """
    Federal Child Tax Credit surfaced to Missouri users as ``mo_ctc``.

    Missouri has no state CTC, so this reads PolicyEngine's federal ``ctc_value``
    with no Missouri-specific input. Deliberately adds nothing: ``ctc_value`` is
    federal end to end (``min(ctc, ctc_limiting_tax_liability + refundable_ctc)``,
    and the limiting-liability term zeroes SALT), so sending a state code would
    add an input the formula never reads. Verified live against PolicyEngine
    1.786.5: identical values with no state code, MO, TX and CA.

    It exists as its own class so the registry maps one key to one calculator.
    Contrast ``il_ctc`` / ``coctc``, which read genuinely state-specific
    PolicyEngine variables and so do send a state code.
    """

    program_code = "mo_ctc"


class MoEitc(Eitc):
    """
    Federal EITC surfaced to Missouri users as ``mo_eitc``.

    Missouri has no state EITC. Same reasoning as ``MoCtc``: PolicyEngine's
    ``eitc`` is federal, so there is nothing state-specific to add.
    """

    program_code = "mo_eitc"


class MoCdccFederal(Cdcc):
    """
    Federal Child and Dependent Care Credit surfaced to Missouri users as
    ``mo_cdcc_federal``.

    Missouri has no state CDCC, so this reads PolicyEngine's federal ``cdcc``
    unchanged. Same reasoning as ``MoCtc``: the variable is federal, so there is
    no state-specific input to add. Exists as its own class so the registry maps
    one key to one calculator.
    """

    program_code = "mo_cdcc_federal"


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
    Missouri Property Tax Credit, the "Circuit Breaker" (RSMo §§135.010–135.030).

    An annual refundable credit against Missouri property tax or rent for a claimant who
    is 65 or older, disabled, a service-disabled veteran, or a 60-or-older surviving
    spouse receiving Social Security survivor benefits. PolicyEngine models the whole
    rule — the four filing-status/ownership income limits, the $2,800/$5,800 married
    offsets, the $14,300 minimum base, the $495 income and $25 payment increments, the
    1/16-point-per-increment phaseout capped at 2%, and the $1,055 renter / $1,550 owner
    caps — so this class supplies inputs and reads the result.

    Three things beyond a bare ``pe_name``/``pe_outputs`` registration:

    - ``eligible()`` is overridden to read ``mo_ptc_taxunit_eligible`` rather than infer
      eligibility from the credit amount. The credit is the payment-band midpoint less
      the phaseout, floored at $0, so a household near the top of its income tier with a
      small qualifying payment qualifies for the program and is awarded nothing. The base
      class's ``eligible = value > 0`` would report such a household as ineligible.

    - Veteran income is routed to ``veterans_benefits`` via
      ``VeteransBenefitsDependency``, with ``PensionIncomeWithoutVeteranDependency``
      replacing the shared ``PensionIncomeDependency`` so the stream is not counted
      twice. ``mo_ptc_gross_income`` excludes veterans' benefits by subtracting
      ``veterans_benefits`` specifically; the shared mapping delivers the same dollars
      under ``taxable_pension_income``, which reaches the formula through
      ``mo_adjusted_gross_income`` where the exclusion cannot reach it.

    - ``IsFullyDisabledServiceConnectedVeteranDependency`` sets the person-level flag the
      exclusion is gated on. PolicyEngine gives it no formula, so it is false unless
      sent. It is scoped to this calculator rather than a shared dependency list because
      it also drives ``military_disabled_head``/``military_disabled_spouse``,
      ``mi_exemptions``, and ``il_cta_military_service_pass_eligible``.

    The mapping and the flag are jointly required: with only one of the two, a
    veteran-income household's credit is computed off unexcluded income.

    Three further inputs depart from the usual set for the same reason — a shared
    dependency delivers the right dollars to the wrong PolicyEngine variable:

    - ``AgeAtEndOf2026Dependency`` replaces ``AgeDependency``. The statute measures age
      on December 31 of the claim year; ``AgeDependency`` measures it on the screening
      date, so a claimant born in September 1961 reads as 64 and fails the age-65
      pathway for most of the year in which they actually qualify.
    - ``SocialSecuritySurvivorsIncomeDependency`` accompanies
      ``SocialSecurityIncomeDependency``. The survivor pathway reads
      ``social_security_survivors``, but the shared dependency reports only the
      ``social_security`` total, which PolicyEngine defines as the sum of its
      components — setting the total leaves every component at zero.
    - ``Ssi`` replaces ``SsiReportedDependency``. ``mo_ptc_gross_income`` adds the ``ssi``
      variable, and ``ssi_reported`` no longer reaches it: it feeds only the deprecated
      ``applicable_ssi``, which no PolicyEngine program reads. ``Ssi`` sets ``ssi``
      directly from reported income and leaves it unset (PolicyEngine-simulated) when
      the household reports none.

    Data gaps carried by the inputs, all resolved inclusively: full-year Missouri
    residency and tax-year homestead location are not collected, so a current
    owned/rented residence stands in; ownership duration is not collected, so any
    homeowner is treated as a full-year owner; and the claimant's actual filing status is
    not collected, so PolicyEngine's filing status derived from spouse presence stands in.
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
        dependency.tax.MoPtcTaxUnitEligible,
    ]

    def eligible(self) -> Eligibility:
        e = super().eligible()

        e.eligible = self._pe_eligible()

        return e

    def _pe_eligible(self) -> bool:
        """True if PolicyEngine reports any tax unit eligible for the credit."""
        for unit in ALL_TAX_UNITS:
            try:
                if self.sim.value(
                    dependency.tax.MoPtcTaxUnitEligible.unit,
                    unit,
                    dependency.tax.MoPtcTaxUnitEligible.field,
                    self.pe_period,
                ):
                    return True
            except KeyError:
                # The secondary tax unit is omitted from the request when empty.
                continue

        return False

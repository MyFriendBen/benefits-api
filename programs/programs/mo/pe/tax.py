from programs.programs.federal.pe.tax import Aca, Cdcc, Ctc, Eitc
from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
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

    A thin wrapper around PolicyEngine's ``mo_wftc``. Missouri's credit is a
    percentage of the federal EITC (10% for TY2023, 20% from TY2024), capped at the
    filer's remaining Missouri tax liability after the property tax credit. PE models
    the whole chain: ``mo_wftc_eligible`` for the gate, ``mo_wftc_potential`` for the
    rate-multiplied amount, ``mo_wftc_liability_cap`` for the Form MO-WFTC Lines 7-9
    netting, and ``mo_wftc`` for the final smaller-of result.

    Inputs reuse the federal ``Eitc.pe_inputs`` set and add the MO state code so
    PolicyEngine applies the Missouri credit rather than the federal EITC alone.

    **Investment-income gate — a known approximation on both sides.** Missouri has two
    tests: most filers use a four-component measure (tax-exempt and taxable interest,
    ordinary dividends, and positive capital gain net income), but Form MO-WFTC routes
    filers with Schedule E, Form 4797, Form 8814, personal-property rental, or passive
    activity to IRS Pub. 596 Worksheet 1, which folds in rental and royalty amounts.
    The screener collects a single coarse ``rental`` total and cannot reconstruct
    Worksheet 1, so neither we nor PolicyEngine implement Missouri's real branching
    test. PE approximates with ``eitc_relevant_investment_income``, which counts rental
    dollar-for-dollar against the threshold. We accept that approximation rather than
    override the gate: it errs toward excluding a household whose true Worksheet 1
    result might have cleared the limit, and the Department of Revenue makes the actual
    determination. See ``spec.md`` criterion 5.

    Screener gaps the calculator does NOT block on, per spec.md:
      - Whether the filer will actually file a Missouri return for the year
      - Whether the filer is claimed as a dependent elsewhere (no screener field)
      - Married-filing-separately, which Missouri excludes but the screener cannot
        detect: spouses are treated as filing jointly, the most common case
    """

    program_code = "mo_wftc"

    pe_name = "mo_wftc"
    pe_inputs = [
        *Eitc.pe_inputs,
        # The credit is capped at Missouri liability *after* the property tax credit
        # (Form MO-WFTC Lines 7-9), and PolicyEngine computes that credit from
        # ``real_estate_taxes``. The federal Eitc input set does not send it, so
        # without this the property tax credit is always $0 and the cap is too high.
        dependency.member.PropertyTaxExpenseDependency,
        dependency.household.MoStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.MoWftc]

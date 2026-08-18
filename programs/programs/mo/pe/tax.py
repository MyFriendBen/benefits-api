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

    name_abbreviated = "mo_aca_ptc"

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

    name_abbreviated = "mo_ctc"


class MoEitc(Eitc):
    """
    Federal EITC surfaced to Missouri users as ``mo_eitc``.

    Missouri has no state EITC. Same reasoning as ``MoCtc``: PolicyEngine's
    ``eitc`` is federal, so there is nothing state-specific to add.
    """

    name_abbreviated = "mo_eitc"


class MoCdccFederal(Cdcc):
    """
    Federal Child and Dependent Care Credit surfaced to Missouri users as
    ``mo_cdcc_federal``.

    Missouri has no state CDCC, so this reads PolicyEngine's federal ``cdcc``
    unchanged. Same reasoning as ``MoCtc``: the variable is federal, so there is
    no state-specific input to add. Exists as its own class so the registry maps
    one key to one calculator.
    """

    name_abbreviated = "mo_cdcc_federal"

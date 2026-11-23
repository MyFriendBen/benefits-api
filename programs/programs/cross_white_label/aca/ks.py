"""KS ACA premium tax credit."""

from programs.programs.cross_white_label.aca.base import Aca
import programs.framework.pe_dependencies as dependency


class KsAca(Aca):
    """
    Kansas ACA Premium Tax Credit — the federal ``Aca`` PE calculator plus the three
    inputs Kansas's value depends on.

    Nothing about *whether* a Kansas household qualifies is state-specific: Kansas uses
    HealthCare.gov rather than a state-based exchange, so eligibility is federal end to end
    (26 U.S.C. 36B) and lives entirely in PolicyEngine. What varies is the dollar value, and
    it varies by county. Kansas is a non-expansion state, which makes this the only coverage
    subsidy available to childless adults between 100% and 138% FPL — the 100% FPL floor is
    federal and PolicyEngine already applies it.

    Three inputs beyond the federal base class, the same set ``MoAca`` sends:

    - ``KsStateCodeDependency`` — selects Kansas's rating-area table.
    - ``KsCountyDependency`` — the benchmark premium (SLCSP) is set per *rating area*, and
      PolicyEngine keys that off ``county_str``, not ``zip_code``. Kansas has 7 rating areas,
      so zip alone is not enough: holding age, income and household composition constant, a
      Wyandotte County household (Rating Area 1) scores $6,257/year and a Sedgwick County one
      (Rating Area 6) $7,599/year. Kansas has no independent cities, so the base normalizer
      resolves all 105 counties without a special case.
    - ``HasEsiDependency`` — employer-sponsored coverage is a statutory disqualifier that
      PolicyEngine applies only if we tell it. Without it the same Wyandotte household with
      job-based coverage is scored eligible for the full $6,257 instead of $0.

    ``TxAca``/``NcAca``/``MaAca`` still pass none of these, and ``IlAca`` passes no
    ``has_esi``. Fixing them changes results for already-shipped programs, so that stays out
    of scope here.

    Known limitation, not corrected here: the credit is a benchmark-based *maximum* rather
    than the household's final legal credit — the statute caps it at the premium of the plan
    actually chosen. The program copy frames the result as an estimate accordingly.
    """

    program_code = "ks_aca_ptc"

    pe_inputs = [
        *Aca.pe_inputs,
        dependency.household.KsStateCodeDependency,
        dependency.household.KsCountyDependency,
        dependency.member.HasEsiDependency,
    ]

"""MO SSI."""

from programs.programs.cross_white_label.ssi.base import Ssi
import programs.framework.pe_dependencies as dependency


class MoSsi(Ssi):
    """
    Missouri Supplemental Security Income — federal SSI applied to MO residents.

    A thin wrapper on the federal ``Ssi`` PolicyEngine calculator that adds only the MO
    state code, mirroring ``KsSsi`` / ``TxSsi`` / ``WaSsi``. SSI is federal end to end:
    PolicyEngine's ``ssi`` variable reads only ``gov.ssa.ssi.*`` parameters, with no state
    key anywhere in the formula, and PE models SSI *state supplements* for NM, SC, and TX
    only — there is no MO supplement module. So the output is the federal Benefit Rate
    (sourced from PE's parameters at calculation time, so it tracks SSA COLA updates
    automatically) minus PolicyEngine's countable income.

    Missouri's own state cash programs for this population — Blind Pension, Supplemental
    Aid to the Blind, and Supplemental Nursing Care — are deliberately out of scope here
    and tracked as a separate program.

    All eligibility math lives in PolicyEngine: the aged / blind / disabled categorical
    entry, the $20 general + $65 earned + 1/2 remainder exclusion stack, the SGA cutoff,
    in-kind support and maintenance, spousal and parental deeming, and the resource limit.
    The screener contributes only the per-member inputs inherited from ``Ssi.pe_inputs``
    plus the MO state code.

    Two of those inherited inputs are load-bearing rather than boilerplate:

    - ``MeetsSsiDisabilityCriteriaDependency`` — PE 1.715.2+ no longer infers SSI
      disability from ``is_disabled`` or reported receipt, so without it a disabled
      non-aged, non-blind applicant returns ``ssi: 0``. It is version-gated, so it only
      reaches models that define the field.
    - ``SsiCountableResourcesDependency`` — the resource limit is a hard cutoff, and this
      splits reported household assets across adults to approximate the per-person figure.

    Duplicate-enrollment filtering ("not already receiving SSI") happens a layer up via
    ``Screen.has_benefit("mo_ssi")``, which is why the config sets
    ``show_in_has_benefits_step: true``.
    """

    program_code = "mo_ssi"

    pe_inputs = [
        *Ssi.pe_inputs,
        dependency.household.MoStateCodeDependency,
    ]

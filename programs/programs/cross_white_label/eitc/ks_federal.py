"""KS federal Earned Income Tax Credit."""

from programs.programs.cross_white_label.eitc.base import Eitc


class KsEitcFederal(Eitc):
    """
    Federal Earned Income Tax Credit surfaced to Kansas users as
    ``ks_eitc_federal``.

    Distinct from ``ks_eitc``, which is Kansas's own credit and resolves to
    ``Kseitc``. That one reads ``ks_total_eitc`` and sends a state code; this one
    reads PolicyEngine's federal ``eitc`` unchanged and sends none, because
    nothing under ``gov/irs/credits/earned_income`` reads ``state_code``.

    Mirrors ``ks_cdcc_federal``/``ks_cdcc``, the other Kansas federal-and-state
    credit pair.
    """

    program_code = "ks_eitc_federal"

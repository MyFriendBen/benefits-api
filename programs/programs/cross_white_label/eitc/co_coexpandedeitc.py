"""CoExpandedEitc."""

from programs.programs.cross_white_label.eitc.co_coeitc import Coeitc


class CoExpandedEitc(Coeitc):
    """
    Colorado Expanded EITC (``co_expanded_eitc``).

    Currently identical to ``Coeitc``: both rows produce the same eligibility and
    value today. It exists as its own class so the registry maps one key to one
    calculator, and so the real divergence has somewhere to land — MFB-1093 gives
    this program a calculator that recognises the population it was created for
    (ITIN filers and childless filers under 25), which ``Coeitc`` excludes.

    Until then this deliberately overrides nothing.
    """

    program_code = "co_expanded_eitc"

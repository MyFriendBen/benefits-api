"""WA Child Tax Credit."""

from programs.programs.cross_white_label.ctc.base import Ctc


class WaCtc(Ctc):
    """
    Federal Child Tax Credit surfaced to Washington users as ``wa_ctc``.

    Washington has no state CTC. Reads PolicyEngine's federal ``ctc_value``
    unchanged; see ``MoCtc`` for why no state code is sent.

    Distinct from ``wa_wftc`` (Working Families Tax Credit), which is a real
    Washington credit with its own calculator.
    """

    program_code = "wa_ctc"

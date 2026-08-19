"""TX Child Tax Credit."""

from programs.programs.cross_white_label.ctc.base import Ctc


class TxCtc(Ctc):
    """
    Federal Child Tax Credit surfaced to Texas users as ``tx_ctc``.

    Texas has no state CTC and no state income tax, so this reads PolicyEngine's
    federal ``ctc_value`` unchanged. See ``MoCtc`` for why no state code is sent.
    """

    program_code = "tx_ctc"

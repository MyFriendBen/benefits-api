"""TX EITC."""

from programs.programs.cross_white_label.eitc.base import Eitc


class TxEitc(Eitc):
    """
    Federal EITC surfaced to Texas users as ``tx_eitc``.

    Texas has no state EITC. PolicyEngine's ``eitc`` is federal.
    """

    program_code = "tx_eitc"

"""KS Child Tax Credit."""

from programs.programs.cross_white_label.ctc.base import Ctc


class KsCtc(Ctc):
    """
    Federal Child Tax Credit surfaced to Kansas users as ``ks_ctc``.

    Kansas has no state CTC, so this reads PolicyEngine's federal ``ctc_value``
    unchanged. Note the asymmetry with ``ks_eitc``, which resolves to ``Kseitc``
    and does send a state code: that one reads ``ks_total_eitc``, a genuinely
    Kansas-specific PolicyEngine variable. State code follows the variable, not
    the key prefix.
    """

    program_code = "ks_ctc"

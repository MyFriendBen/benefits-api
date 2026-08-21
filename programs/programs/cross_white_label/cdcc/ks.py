"""KS Child and Dependent Care Credit."""

from programs.programs.cross_white_label.cdcc.base import Cdcc


class KsCdccFederal(Cdcc):
    """
    Federal Child and Dependent Care Credit surfaced to Kansas users as
    ``ks_cdcc_federal``.

    Distinct from ``ks_cdcc``, which is Kansas's own credit and has its own
    calculator (``KsCdcc``). This one reads PolicyEngine's federal ``cdcc``
    unchanged and exists so the registry maps one key to one calculator.
    """

    program_code = "ks_cdcc_federal"

"""MO Child and Dependent Care Credit."""

from programs.programs.cross_white_label.cdcc.base import Cdcc


class MoCdccFederal(Cdcc):
    """
    Federal Child and Dependent Care Credit surfaced to Missouri users as
    ``mo_cdcc_federal``.

    Missouri has no state CDCC, so this reads PolicyEngine's federal ``cdcc``
    unchanged. Same reasoning as ``MoCtc``: the variable is federal, so there is
    no state-specific input to add. Exists as its own class so the registry maps
    one key to one calculator.
    """

    program_code = "mo_cdcc_federal"

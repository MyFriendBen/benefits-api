"""MO EITC."""

from programs.programs.cross_white_label.eitc.base import Eitc


class MoEitc(Eitc):
    """
    Federal EITC surfaced to Missouri users as ``mo_eitc``.

    Missouri has no state EITC. PolicyEngine's ``eitc`` is federal, so there is
    nothing state-specific to add.
    """

    program_code = "mo_eitc"

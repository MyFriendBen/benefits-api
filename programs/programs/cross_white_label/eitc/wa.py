"""WA EITC."""

from programs.programs.cross_white_label.eitc.base import Eitc


class WaEitc(Eitc):
    """
    Federal EITC surfaced to Washington users as ``wa_eitc``.

    PolicyEngine's ``eitc`` is federal. Washington's own credit is the Working
    Families Tax Credit, handled separately.
    """

    program_code = "wa_eitc"

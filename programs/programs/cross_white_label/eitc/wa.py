"""WA EITC."""

from programs.programs.cross_white_label.eitc.base import Eitc


class WaEitc(Eitc):
    """
    Washington has no state EITC, so this reuses the federal calculation
    unchanged. It exists so the WA row resolves to a WA-named class.
    """

    program_code = "wa_eitc"

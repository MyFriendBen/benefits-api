"""MO Child Tax Credit."""

from programs.programs.cross_white_label.ctc.base import Ctc


class MoCtc(Ctc):
    """
    Federal Child Tax Credit surfaced to Missouri users as ``mo_ctc``.

    Missouri has no state CTC, so this reads PolicyEngine's federal ``ctc_value``
    with no Missouri-specific input. Deliberately adds nothing: ``ctc_value`` is
    federal end to end (``min(ctc, ctc_limiting_tax_liability + refundable_ctc)``,
    and the limiting-liability term zeroes SALT), so sending a state code would
    add an input the formula never reads. Verified live against PolicyEngine
    1.786.5: identical values with no state code, MO, TX and CA.

    It exists as its own class so the registry maps one key to one calculator.
    Contrast ``il_ctc`` / ``coctc``, which read genuinely state-specific
    PolicyEngine variables and so do send a state code.
    """

    program_code = "mo_ctc"

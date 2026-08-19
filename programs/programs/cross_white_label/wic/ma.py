"""MA WIC."""

from programs.programs.cross_white_label.wic.base import Wic
import programs.framework.pe_dependencies as dependency


class MaWic(Wic):
    program_code = "ma_wic"
    wic_categories = {
        "NONE": 0,
        "INFANT": 186,
        "CHILD": 77,
        "PREGNANT": 107,
        # NOTE: guesses based off Colorado
        "POSTPARTUM": 91,
        "BREASTFEEDING": 124,
    }
    # WIC's FPG table branches on AK/HI vs. contiguous US, so the state code is
    # load-bearing. This was the only WIC subclass not sending one — it worked only
    # because a sibling MA program put the state in the shared payload.
    pe_inputs = [
        *Wic.pe_inputs,
        dependency.household.MaStateCodeDependency,
    ]

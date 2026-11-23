"""MO CSFP."""

from programs.programs.cross_white_label.csfp.base import CommoditySupplementalFoodProgram
import programs.framework.pe_dependencies as dependency


class MoCsfp(CommoditySupplementalFoodProgram):
    """
    Missouri CSFP, via PolicyEngine's ``commodity_supplemental_food_program``.

    Eligibility and value are PolicyEngine's; see specs/mo.md for the rules. Notes here cover
    only why each input is sent.

    ``MoStateCodeDependency`` is declared so this program's answer doesn't depend on which
    sibling Missouri programs share the request. PolicyEngine has no Missouri county gate, so
    no county is sent. Its Kansas categorical route is ``defined_for`` Kansas and never fires
    here, so the receipt contract isn't needed either: the countable-income total is supplied
    directly and PolicyEngine's simulated SSI and SNAP never enter.
    """

    program_code = "mo_csfp"

    pe_inputs = [
        *CommoditySupplementalFoodProgram.pe_inputs,
        dependency.household.MoStateCodeDependency,
    ]

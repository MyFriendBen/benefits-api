"""KS CSFP."""

from programs.programs.cross_white_label.csfp.base import CommoditySupplementalFoodProgram
from programs.programs.cross_white_label.msp.base import Msp
import programs.framework.pe_dependencies as dependency


class KsCsfp(CommoditySupplementalFoodProgram):
    """
    Kansas CSFP, via PolicyEngine's ``commodity_supplemental_food_program``.

    Eligibility and value are PolicyEngine's; see specs/ks.md for the rules. Notes here cover
    only why each input is sent.

    ``KsCountyDependency`` is load-bearing: PolicyEngine's Kansas branch ANDs in
    ``ks_dcf_csfp_county_eligible``, and with no county sent it defaults the household to a
    county with no distribution site, returning $0 statewide. It also makes ``can_calc()`` skip
    the program when county is unknown rather than report an affirmative ineligible.

    ``Msp.pe_inputs`` feed ``ks_dcf_csfp_categorically_eligible``, which ORs a positive
    ``ssi``, ``snap`` or ``msp`` into the income test. All three are amounts PolicyEngine
    computes, so without the household's real income and reported receipt it computes them on
    $0 income and makes every covered-county senior categorically eligible. ``receipt_contract``
    (inside ``Msp.pe_inputs``) holds SSI and SNAP to reported receipt; MSP has no receipt input,
    so its income, asset and Medicare inputs are what keep the computed ``msp`` honest.
    """

    program_code = "ks_csfp"

    pe_inputs = [
        *CommoditySupplementalFoodProgram.pe_inputs,
        dependency.household.KsStateCodeDependency,
        dependency.household.KsCountyDependency,
        *Msp.pe_inputs,
    ]

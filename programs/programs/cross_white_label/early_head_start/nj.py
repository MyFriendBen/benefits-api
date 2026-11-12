"""NJ Early Head Start."""

from decimal import Decimal

from programs.programs.cross_white_label.early_head_start.mfb_base import MfbEarlyHeadStart


class NjEarlyHeadStart(MfbEarlyHeadStart):
    """
    New Jersey Early Head Start. Inherits every federal rule from ``MfbEarlyHeadStart``; NJ
    sets only the value and its public assistance program.

    - The value prices a year at NJ's maximum child care payment rates for full-time care at
      a licensed center (effective April 1, 2026), by NJ's age bands: infants birth to 17
      months 367.59 a week, toddlers 18 to 29 months 327.38, and 30 months and over 292.30.
      The year is the 46 weeks that 1,380 annual hours make at that table's 30-hour
      full-time week. A pregnant woman is priced as an infant.
    - Public assistance reads ``federal_ssi`` and ``nj_tanf``, which NJ households see. NJ
      has no SNAP calculator yet, so SNAP is read only from reported benefits.

    The spec is ``programs/cross_white_label/early_head_start/nj/early_head_start_nj_spec.md``
    in program-ops.
    """

    program_code = "nj_early_head_start"

    weekly_prices = (
        (0, Decimal("367.59")),
        (18, Decimal("327.38")),
        (30, Decimal("292.30")),
    )
    program_weeks = 1_380 // 30
    gates_on_any = ("federal_ssi", "nj_tanf")

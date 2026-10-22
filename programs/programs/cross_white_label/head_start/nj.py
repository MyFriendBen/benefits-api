"""NJ Head Start."""

from programs.programs.cross_white_label.head_start.mfb_base import MfbHeadStart


class NjHeadStart(MfbHeadStart):
    """
    New Jersey Head Start Preschool. Inherits every federal rule from ``MfbHeadStart``; NJ
    sets only its school-age dates and the value.

    - A child must be 3 by October 1 and under 6, NJ's compulsory school age, so NJ's
      5-year-olds, for whom kindergarten isn't compulsory, still qualify.
    - The value prices a year at NJ's maximum child care payment rate for full-time
      preschool at a licensed center ($292.30/week, effective April 1, 2026) over the
      34 weeks that 1,020 annual hours make at that table's 30-hour full-time week.

    NJ has no SNAP, TANF or SSI calculator yet, so ``gates_on_any`` stays empty and public
    assistance is read only from reported benefits and income.

    The spec is ``programs/cross_white_label/head_start/nj/head_start_nj_spec.md`` in
    program-ops.
    """

    program_code = "nj_head_start"

    school_eligibility_cutoff_date = (10, 1)
    compulsory_school_age = 6
    weekly_price = 292.30
    program_weeks = 34

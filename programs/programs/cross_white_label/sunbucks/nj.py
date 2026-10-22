"""NJ SUN Bucks (Summer EBT)."""

from datetime import date

from programs.programs.cross_white_label.sunbucks.base import FOSTER_CHILD, SNAP, TANF, SunBucks


class NjSunBucks(SunBucks):
    """
    New Jersey SUN Bucks. Inherits every federal rule from ``SunBucks``; NJ sets its school
    ages and who it enrolls automatically.

    - A child must have been 6 to 16 at some point between July 1, 2025 and August 31, 2026.
      The window moves each year with the summer it pays for.
    - NJ enrolls children in SNAP or TANF households, and foster children, with no
      application, so none of them is shown the program. A foster child's siblings still are.

    NJ also counts a child with Medicaid whose household income is under the limit, which the
    base's income route already admits. The value is the federal $120.

    The spec is ``programs/cross_white_label/sunbucks/nj/sunbucks_nj_spec.md`` in program-ops.
    """

    program_code = "nj_sunbucks"

    min_school_age = 6
    max_school_age = 16
    school_age_window = (date(2025, 7, 1), date(2026, 8, 31))
    enrolled_automatically = (SNAP, TANF, FOSTER_CHILD)

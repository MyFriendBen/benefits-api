"""NJ SUN Bucks (Summer EBT)."""

from programs.programs.cross_white_label.sunbucks.base import FOSTER_CHILD, SNAP, TANF, SunBucks


class NjSunBucks(SunBucks):
    """
    New Jersey SUN Bucks. Inherits every federal rule from ``SunBucks``; NJ sets its school
    ages and who it enrolls automatically.

    - A child must be 6 to 16 at some point between July 1 and August 31 of the next year: the
      school year and the summer it pays for. NJ published the 2025-26 dates; the window rolls
      to the next year on September 1.
    - NJ enrolls children in SNAP or TANF households, and foster children, with no
      application, so none of them is shown the program. A foster child's siblings still are.

    NJ also counts a child with Medicaid whose household income is under the limit, which the
    base's income route already admits. The value is the federal $120.

    The spec is ``programs/cross_white_label/sunbucks/nj/sunbucks_nj_spec.md`` in program-ops.
    """

    program_code = "nj_sunbucks"

    min_school_age = 6
    max_school_age = 16
    school_age_window = ((7, 1), (8, 31))
    enrolled_automatically = (SNAP, TANF, FOSTER_CHILD)

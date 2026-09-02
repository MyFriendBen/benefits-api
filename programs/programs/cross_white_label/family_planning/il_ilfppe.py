"""IlFppe."""

from programs.programs.cross_white_label.family_planning.il_base import IlFamilyPlanningProgram


class IlFppe(IlFamilyPlanningProgram):
    """
    Family Planning Presumptive Eligibility (``il_fppe``).

    No immigration-status requirement, unlike ``il_hfs_fpp``. Same situation:
    both share ``il_fpp_eligible`` today, so this overrides nothing.
    """

    program_code = "il_fppe"

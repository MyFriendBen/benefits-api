"""IlHfsFpp."""

from programs.programs.cross_white_label.family_planning.il_base import IlFamilyPlanningProgram


class IlHfsFpp(IlFamilyPlanningProgram):
    """
    HFS Family Planning Program (``il_hfs_fpp``).

    Requires qualified immigration status, unlike ``il_fppe``. That distinction is
    not yet modelled: PolicyEngine resolves both rows through the same
    ``il_fpp_eligible`` variable, so this currently overrides nothing and exists
    so the registry maps one key to one calculator. If the immigration-status
    requirement is ever modelled, it belongs here.
    """

    program_code = "il_hfs_fpp"

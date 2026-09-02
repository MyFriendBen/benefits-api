"""MA SNAP."""

from programs.programs.cross_white_label.snap.base import SNAP_HOURS_INPUT, Snap
import programs.framework.pe_dependencies as dependency


class MaSnap(Snap):
    program_code = "ma_snap"
    # Swaps the hours class rather than adding one: MA TAFDC and EAEDC are on the same
    # screen sending MaTotalHoursWorkedDependency, which approximates at the $15 state
    # minimum wage where the base class uses the $7.25 federal floor. Above the assumed
    # 40-hour floor those disagree (a $2,000/mo salary reads 33 hours in MA, 69 federally),
    # and two dependencies writing different values to one field and period raise
    # DependencyError inside pe_input() -- which runs outside calc_pe_eligibility's
    # try/except, so the whole screen 500s rather than losing one program (MFB-1637).
    pe_inputs = [
        *(dep for dep in Snap.pe_inputs if dep is not SNAP_HOURS_INPUT),
        dependency.member.MaTotalHoursWorkedDependency,
        dependency.household.MaStateCodeDependency,
    ]

"""NC National School Lunch Program."""

from programs.programs.cross_white_label.nslp.base import SchoolLunch
import programs.framework.pe_dependencies as dependency


class NcNslp(SchoolLunch):
    """
    North Carolina National School Lunch Program (NSLP) calculator.

    Inherits the federal SchoolLunch eligibility/value logic and adds the NC
    state code so PolicyEngine resolves state_has_universal_free_school_meals
    correctly. Without a state code, PE defaults to universal-free behavior,
    which is wrong for NC (see MFB-1683) but coincidentally correct for the
    bare-key CO/MA rows, which are genuinely universal-free.
    """

    program_code = "nc_nslp"

    pe_inputs = [
        *SchoolLunch.pe_inputs,
        dependency.household.NcStateCodeDependency,
    ]

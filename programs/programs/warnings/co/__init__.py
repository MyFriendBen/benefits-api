from programs.programs.warnings.base import WarningCalculator
from programs.programs.warnings.co.snap_student import SnapStudentWarning
from programs.programs.warnings.co.universal_preschool import UniversalPreschool

co_warning_calculators: dict[str, type[WarningCalculator]] = {
    "co_snap_student": SnapStudentWarning,
    "co_upk": UniversalPreschool,
}

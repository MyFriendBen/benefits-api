from programs.programs.warnings.base import WarningCalculator
from .senior_snap_application import MaSeniorSnapApplication

ma_warning_calculators: dict[str, type[WarningCalculator]] = {
    "ma_senior_snap_application": MaSeniorSnapApplication,
}

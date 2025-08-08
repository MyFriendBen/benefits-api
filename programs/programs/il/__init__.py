from .medicaid.family_care.calculator import FamilyCare
from ..calc import ProgramCalculator

il_calculators: dict[str, type[ProgramCalculator]] = {
    "il_family_care": FamilyCare,
}

from .medicaid.family_care.calculator import FamilyCare
from .medicaid.moms_and_babies.calculator import MomsAndBabies
from ..calc import ProgramCalculator

il_calculators: dict[str, type[ProgramCalculator]] = {
    "il_family_care": FamilyCare,
    "il_moms_and_babies": MomsAndBabies,
}

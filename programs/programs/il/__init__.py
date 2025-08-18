from .medicaid.family_care.calculator import FamilyCare
from .medicaid.moms_and_babies.calculator import MomsAndBabies
from .medicaid.aca_adults.calculator import AcaAdults
from .medicaid.all_kids.calculator import AllKids
from ..calc import ProgramCalculator

il_calculators: dict[str, type[ProgramCalculator]] = {
    "il_family_care": FamilyCare,
    "il_moms_and_babies": MomsAndBabies,
    "il_aca_adults": AcaAdults,
    "il_all_kids": AllKids,
}

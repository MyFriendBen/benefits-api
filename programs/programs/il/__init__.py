from .medicaid.family_care.calculator import FamilyCare
from .medicaid.moms_and_babies.calculator import MomsAndBabies
from .medicaid.aca_adults.calculator import AcaAdults
from .medicaid.all_kids.calculator import AllKids
from .pe.member import IlBreastCervicalCancerProgram
from .bap.calculator import IlBenefitAccess
from .transit_reduced_fare.calculator import IlTransitReducedFare
from .commodity_supplemental_food_program.calculator import IlCommoditySupplementalFoodProgram
from .ccap.calculator import IlChildCareAssistanceProgram
from ..calc import ProgramCalculator

il_calculators: dict[str, type[ProgramCalculator]] = {
    "il_family_care": FamilyCare,
    "il_moms_and_babies": MomsAndBabies,
    "il_aca_adults": AcaAdults,
    "il_all_kids": AllKids,
    "il_ibccp": IlBreastCervicalCancerProgram,
    "il_bap": IlBenefitAccess,
    "il_transit_reduced_fare": IlTransitReducedFare,
    "il_csfp": IlCommoditySupplementalFoodProgram,
    "il_ccap": IlChildCareAssistanceProgram,
}

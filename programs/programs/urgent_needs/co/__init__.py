from ..base import UrgentNeedFunction
from .util import LivesInDenver, Child, HasRentOrMortgage
from .meal_in_counties import MealInCounties
from .helpkitchen_zipcode import HelpkitchenZipcode
from .bia_food_delivery import BiaFoodDelivery
from .trua import Trua
from .foreclosure_fin_assist_program import ForeclosureFinAssistProgram
from .eoc import Eoc
from .co_legal_services import CoLegalServices
from .co_emergency_mortgage_assistance import CoEmergencyMortgageAssistance
from .child_first import ChildFirst
from .early_childhood_mental_health_support import EarlyChildhoodMentalHealthSupport
from .parents_of_preschool_youngsters import ParentsOfPreschoolYoungsters
from .parents_as_teacher import ParentsAsTeacher
from .snap_employment import SnapEmployment
from .early_intervention import EarlyIntervention
from .denver_emergency_assistance import DenverEmergencyAssistance
from .diaper_banks import FamilyResourceCenterAssociation, NationalDiaperBank
from .first_step_savings import FirstStepSavings, FirstStepSavingsNotifiable

co_urgent_need_functions: dict[str, type[UrgentNeedFunction]] = {
    "denver": LivesInDenver,
    "child": Child,
    "has_rent_or_mtg": HasRentOrMortgage,
    "meal": MealInCounties,
    "helpkitchen_zipcode": HelpkitchenZipcode,
    "bia_food_delivery": BiaFoodDelivery,
    "trua": Trua,
    "ffap": ForeclosureFinAssistProgram,
    "eoc": Eoc,
    "co_legal_services": CoLegalServices,
    "co_emergency_mortgage": CoEmergencyMortgageAssistance,
    "child_first": ChildFirst,
    "ecmh": EarlyChildhoodMentalHealthSupport,
    "hippy": ParentsOfPreschoolYoungsters,
    "pat": ParentsAsTeacher,
    "snap_employment": SnapEmployment,
    "eic": EarlyIntervention,
    "deap": DenverEmergencyAssistance,
    "frca": FamilyResourceCenterAssociation,
    "diaper_bank": NationalDiaperBank,
    "first_step": FirstStepSavings,
    "first_step_notifiable": FirstStepSavingsNotifiable,
}

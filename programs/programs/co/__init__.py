from .nurse_family_partnership.calculator import CoNurseFamilyPartnership
from .rtdlive.calculator import RtdLive
from .child_care_assistance.calculator import ChildCareAssistance
from .mydenver.calculator import MyDenver
from .cash_back.calculator import CashBack
from .energy_assistance.calculator import EnergyAssistance
from .energy_resource_center.calculator import EnergyResourceCenter
from .omnisalud.calculator import OmniSalud
from .dental_health_care_seniors.calculator import DentalHealthCareSeniors
from .reproductive_health_care.calculator import ReproductiveHealthCare
from .connect_for_health.calculator import ConnectForHealth
from .medicaid.family_planning_services.calculator import FamilyPlanningServices
from .denver_preschool_program.calculator import DenverPreschoolProgram
from .property_credit_rebate.calculator import PropertyCreditRebate
from .universal_preschool.calculator import UniversalPreschool
from .my_spark.calculator import MySpark
from .low_wage_covid_relief.calculator import LowWageCovidRelief
from .medicaid.child_with_disability.calculator import MedicaidChildWithDisability
from .medicaid.adult_with_disability.calculator import MedicaidAdultWithDisability
from .medicaid.emergency.calculator import EmergencyMedicaid
from .basic_cash_assistance.calculator import BasicCashAssistance
from .weatherization_assistance.calculator import WeatherizationAssistance
from .tabor.calculator import Tabor
from .trua.calculator import Trua
from .utility_bill_pay.calculator import UtilityBillPay
from .rental_assistance_grant.calculator import RentalAssistanceGrant
from .emergency_rental_assistance.calculator import EmergencyRentalAssistance
from .denver_trash_rebate.calculator import DenverTrashRebate
from .denver_property_tax_relief.calculator import DenverPropertyTaxRelief
from .nurturing_futures.calculator import NurturingFutures
from .energy_calculator import co_energy_calculators
from .denver_sidewalk_rebate.calculator import DenverSidewalkRebate
from .senior_housing_tax_credit.calculator import SeniorHousingIncomeTaxCredit
from .jeffco_student_benefits.calculator import JeffcoStudentBenefits
from ..calc import ProgramCalculator

co_calculators: dict[str, type[ProgramCalculator]] = {
    "rtdlive": RtdLive,
    "cccap": ChildCareAssistance,
    "mydenver": MyDenver,
    "cocb": CashBack,
    "leap": EnergyAssistance,
    "erc": EnergyResourceCenter,
    "omnisalud": OmniSalud,
    "cdhcs": DentalHealthCareSeniors,
    "rhc": ReproductiveHealthCare,
    "cfhc": ConnectForHealth,
    "fps": FamilyPlanningServices,
    "dpp": DenverPreschoolProgram,
    "cpcr": PropertyCreditRebate,
    "upk": UniversalPreschool,
    "myspark": MySpark,
    "lwcr": LowWageCovidRelief,
    "cwd_medicaid": MedicaidChildWithDisability,
    "awd_medicaid": MedicaidAdultWithDisability,
    "emergency_medicaid": EmergencyMedicaid,
    "bca": BasicCashAssistance,
    "cowap": WeatherizationAssistance,
    "tabor": Tabor,
    "trua": Trua,
    "ubp": UtilityBillPay,
    "rag": RentalAssistanceGrant,
    "erap": EmergencyRentalAssistance,
    "nfp": CoNurseFamilyPartnership,
    "dtr": DenverTrashRebate,
    "dptr": DenverPropertyTaxRelief,
    "nf": NurturingFutures,
    "dsr": DenverSidewalkRebate,
    "shitc": SeniorHousingIncomeTaxCredit,
    "jeffco_student_benefits": JeffcoStudentBenefits,
    **co_energy_calculators,
}

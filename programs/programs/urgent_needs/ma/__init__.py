from .community_support_line import CommunitySupportLine
from .cicrf import Cicrf
from ..base import UrgentNeedFunction
from .healthy_baby_healthy_child import HealthyBabyHealthyChild
from .lawyers_clearinghouse import LawyersClearinghouse
from .early_intervention import EarlyIntervention
from .chapter_115_veteran import Chapter115Veteran
from .family_shelter import FamilyShelter
from .family_support_centers import FamilySupportCenters
from .good_neighbor_energy import GoodNeighborEnergy
from .heartwap import Heartwap
from .alternative_housing_voucher import AlternativeHousingVoucher
from .raft import Raft
from .rental_voucher import RentalVoucher
from .affordable_housing_services import AffordableHousingServices
from .baby_university import BabyUniversity
from .senior_center import CambridgeSeniorCenter
from .career_training import CareerTrainingAndWorkforce
from .college_and_fafsa_support import CollegeAndFafsaSupport
from .journey_to_hope import JourneyToHopeCEOC
from .center_for_families import CenterForFamilies
from .multi_service_center import MultiServiceCenter
from .snap_application_assistance import SNAPApplicationAssistance
from .free_tax_help import FreeTaxHelp

ma_urgent_need_functions: dict[str, type[UrgentNeedFunction]] = {
    "ma_family_shelter": FamilyShelter,
    "ma_chapter_115_veteran": Chapter115Veteran,
    "ma_lawyers_clearinghouse": LawyersClearinghouse,
    "ma_early_intervention": EarlyIntervention,
    "ma_family_support_centers": FamilySupportCenters,
    "ma_healthy_baby_healthy_child": HealthyBabyHealthyChild,
    "ma_good_neighbor_energy": GoodNeighborEnergy,
    "ma_heartwap": Heartwap,
    "ma_alternative_housing_voucher": AlternativeHousingVoucher,
    "ma_raft": Raft,
    "ma_rental_voucher": RentalVoucher,
    "ma_community_support_line": CommunitySupportLine,
    "ma_cicrf": Cicrf,
    "ma_affordable_housing_services": AffordableHousingServices,
    "ma_baby_university": BabyUniversity,
    "ma_cambridge_senior_center": CambridgeSeniorCenter,
    "ma_career_training_and_workforce": CareerTrainingAndWorkforce,
    "ma_college_and_fafsa_support": CollegeAndFafsaSupport,
    "ma_journey_to_hope": JourneyToHopeCEOC,
    "ma_center_for_families": CenterForFamilies,
    "ma_multi_service_center": MultiServiceCenter,
    "ma_snap_application_assistance": SNAPApplicationAssistance,
    "ma_free_tax_help": FreeTaxHelp,
}

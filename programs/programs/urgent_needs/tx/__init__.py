from ..base import UrgentNeedFunction
from .early_intervention import EarlyIntervention
from .workforce_solutions import WorkforceSolutions
from .here_for_texas import HereForTexas
from .law_help import LawHelp
from .central_foodbank import CentralFoodbank
from .feeding_texas import FeedingTexas
from .rewiring_america import RewiringAmerica
from .diaper_bank import NationalDiaperBankNetwork
from .snap_employment import SnapEmploymentTraining
from .find_a_dentist import FindADentist
from .salvation_army import SalvationArmy
from .tdhca_help_for_texans import TdhcaHelpForTexans
from .north_texas_food_bank import NorthTexasFoodBank
from .serve_southern_dallas import ServeSouthernDallas
from .double_up_food_bucks import DoubleUpFoodBucks
from .claim_it_texas import ClaimItTexas
from .wic import Wic
from .arete_health_shield import AreteHealthShield
from .oak_cliff_veggie_project import OakCliffVeggieProject
from .west_dallas_multipurpose_center import WestDallasMultipurposeCenter
from .grocery_clearance_outlet import GroceryClearanceOutlet
from .do_more_good_store import DoMoreGoodStore
from .dallas_college_red_bird import DallasCollegeRedBird
from .workforce_solutions_greater_dallas import WorkforceSolutionsGreaterDallas
from .oak_cliff_lena import OakCliffLena
from .books_beginning_at_birth import BooksBeginningAtBirth
from .harmony_community_development import HarmonyCommunityDevelopment
from .dallas_eviction_advocacy import DallasEvictionAdvocacy
from .hippy import Hippy
from .trust_her import TrustHer
from .legal_aid_northwest_texas import LegalAidNorthwestTexas
from .crossroads_community_services import CrossroadsCommunitySvcs

tx_urgent_need_functions: dict[str, type[UrgentNeedFunction]] = {
    "tx_early_intervention": EarlyIntervention,
    "tx_workforce_solutions": WorkforceSolutions,
    "tx_here_for_texas": HereForTexas,
    "tx_law_help": LawHelp,
    "tx_central_foodbank": CentralFoodbank,
    "tx_feeding_texas": FeedingTexas,
    "tx_rewiring_america": RewiringAmerica,
    "tx_diaper_bank": NationalDiaperBankNetwork,
    "tx_snap_employment": SnapEmploymentTraining,
    "tx_find_a_dentist": FindADentist,
    "tx_salvation_army": SalvationArmy,
    "tx_tdhca_help_for_texans": TdhcaHelpForTexans,
    "tx_north_texas_food_bank": NorthTexasFoodBank,
    "tx_serve_southern_dallas": ServeSouthernDallas,
    "tx_double_up_food_bucks": DoubleUpFoodBucks,
    "tx_claim_it_texas": ClaimItTexas,
    "tx_wic": Wic,
    "tx_arete_health_shield": AreteHealthShield,
    "tx_oak_cliff_veggie_project": OakCliffVeggieProject,
    "tx_west_dallas_multipurpose_center": WestDallasMultipurposeCenter,
    "tx_grocery_clearance_outlet": GroceryClearanceOutlet,
    "tx_do_more_good_store": DoMoreGoodStore,
    "tx_dallas_college_red_bird": DallasCollegeRedBird,
    "tx_workforce_solutions_greater_dallas": WorkforceSolutionsGreaterDallas,
    "tx_oak_cliff_lena": OakCliffLena,
    "tx_books_beginning_at_birth": BooksBeginningAtBirth,
    "tx_harmony_community_development": HarmonyCommunityDevelopment,
    "tx_dallas_eviction_advocacy": DallasEvictionAdvocacy,
    "tx_hippy": Hippy,
    "tx_trust_her": TrustHer,
    "tx_legal_aid_northwest_texas": LegalAidNorthwestTexas,
    "tx_crossroads_community_services": CrossroadsCommunitySvcs,
}

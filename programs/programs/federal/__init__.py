from .ssdi.calculator import Ssdi
from .medicare_savings.calculator import MedicareSavings
from .trump_account.calculator import TrumpAccount
from ..calc import ProgramCalculator

federal_calculators: dict[str, type[ProgramCalculator]] = {
    "ssdi": Ssdi,
    "medicare_savings": MedicareSavings,
    "trump_account": TrumpAccount,
}

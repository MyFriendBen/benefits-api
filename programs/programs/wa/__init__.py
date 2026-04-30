from ..calc import ProgramCalculator
from .ssdi.calculator import WaSsdi

wa_calculators: dict[str, type[ProgramCalculator]] = {
    "wa_ssdi": WaSsdi,
}

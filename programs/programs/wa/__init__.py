from ..calc import ProgramCalculator
from .ssi.calculator import WaSsi

wa_calculators: dict[str, type[ProgramCalculator]] = {
    "wa_ssi": WaSsi,
}

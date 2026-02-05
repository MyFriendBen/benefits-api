from programs.programs.translation_overrides.dont_show import DontShow
from programs.programs.translation_overrides.energy import CoEnergyCalculatorRenter
from programs.programs.translation_overrides.ma import MaSeniorSnapApplication
from .base import TranslationOverrideCalculator

general_calculators: dict[str, type[TranslationOverrideCalculator]] = {
    "_show": TranslationOverrideCalculator,
    "_dont_show": DontShow,
}

specific_calculators: dict[str, type[TranslationOverrideCalculator]] = {
    "ma_senior_snap_application": MaSeniorSnapApplication,
    "cesn_renter": CoEnergyCalculatorRenter,
}

warning_calculators: dict[str, type[TranslationOverrideCalculator]] = {**general_calculators, **specific_calculators}

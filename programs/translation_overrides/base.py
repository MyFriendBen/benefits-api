from programs.util import Dependencies
from screener.models import Screen
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from programs.models import TranslationOverride


class TranslationOverrideCalculator:
    dependencies = tuple()

    def __init__(self, screen: Screen, translation_override: "TranslationOverride", missing_dependencies: Dependencies):
        self.screen = screen
        self.translation_override = translation_override
        self.missing_dependencies = missing_dependencies

    def calc(self) -> bool:
        """
        Return if the translation should be overridden
        """
        if not self.can_calc():
            return False

        return self.eligible() and self.county_eligible()

    def eligible(self) -> bool:
        """
        Custom requirement for whether or not to override the Translation
        """
        return True

    def can_calc(self) -> bool:
        """
        Returns whether or not we can calculate if a translation can be overriden
        """
        return not self.missing_dependencies.has(*self.dependencies)

    def county_eligible(self) -> bool:
        """
        Returns True if the override should be applied based on county
        """
        county = self.screen.county
        translation_override_counties = self.translation_override.county_names
        if len(translation_override_counties) > 0:
            return county in translation_override_counties
        return True

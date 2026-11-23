from programs.translation_overrides.base import TranslationOverrideCalculator


class DontShow(TranslationOverrideCalculator):
    def eligible(self) -> bool:
        """
        Never use this override
        """
        return False

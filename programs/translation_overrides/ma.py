from programs.translation_overrides.base import TranslationOverrideCalculator


class MaSeniorSnapApplication(TranslationOverrideCalculator):
    min_age = 60
    ineligible_age = 18
    dependencies = ["age"]

    def eligible(self) -> bool:
        """
        Show for people 60+ without any other adults not 60+
        """
        senior_count = self.screen.num_adults(self.min_age)
        other_adult_count = self.screen.num_adults(self.ineligible_age)
        return senior_count > 0 and senior_count == other_adult_count

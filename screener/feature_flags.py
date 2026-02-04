from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class FeatureFlagConfig:
    label: str
    description: str
    scope: Literal["frontend", "backend", "both"]
    default: bool = False


WHITELABEL_FEATURE_FLAGS: dict[str, FeatureFlagConfig] = {
    "nps_survey": FeatureFlagConfig(
        label="NPS Survey",
        description="Show Net Promoter Score survey to users after completing a screen.",
        scope="frontend",
    ),
    "eligibility_tags": FeatureFlagConfig(
        label="Eligibility Tags",
        description="Display member-level eligibility status tags on program cards in results.",
        scope="frontend",
    ),
}

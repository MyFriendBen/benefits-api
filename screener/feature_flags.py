"""
Feature Flags for WhiteLabel-level feature toggles.

To add a new flag:
    1. Add an entry to WHITELABEL_FEATURE_FLAGS below
    2. Run `python manage.py sync_feature_flags` (runs automatically on deploy)
    3. Toggle in Admin > General Settings > Feature Flags

To remove a flag:
    1. Remove the entry from WHITELABEL_FEATURE_FLAGS
    2. Run `python manage.py sync_feature_flags` (runs automatically on deploy)

Use `--dry-run` to preview changes without modifying the database.

Scope:
    - "frontend": Returned via /api/config endpoint for use in benefits-calculator
    - "backend": Only available server-side via method white_label.has_feature()
    - "both": Available in both frontend and backend

Usage Example:
    Backend:  white_label.has_feature("nps_survey")
    Frontend: config.feature_flags.nps_survey
"""

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

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from configuration.models import (
    Configuration,
)
from configuration.white_labels import white_label_config
from configuration.white_labels.base import ConfigurationData
from programs.models import FormOption, Icon
from screener.models import NPSScore, WhiteLabel
from translations.models import Translation
import argparse

# Lucide icon rendered when a config _icon key is missing or has no mapping. Mirrors the
# frontend's `OPTION_CARD_ICON_MAP[icon._icon] ?? 'circle-dot'` fallback so a missing/unmapped
# icon renders identically whether resolved on the frontend or served from the DB.
FALLBACK_LUCIDE_NAME = "circle-dot"


# Backend copy of the frontend OPTION_CARD_ICON_MAP (benefits-calculator
# src/Components/Config/configHook.tsx) plus the three energy-calculator icons resolved in
# transformItemIcon's switch. This is the canonical _icon -> Lucide-name vocabulary used to
# seed the Icon table. Re-verify against the frontend after benefits-calculator PR #2142
# (MFB-1245) merges.
ICON_LUCIDE_MAP = {
    # Health insurance
    "None": "ban",
    "Employer": "briefcase",
    "PrivateInsurance": "circle-user-round",
    "Medicaid": "heart-pulse",
    "Medicare": "stethoscope",
    "Chp": "baby",
    "Emergency_medicaid": "ambulance",
    "Family_planning": "heart-handshake",
    "VA": "shield-plus",
    # Conditions
    "Student": "graduation-cap",
    "Pregnant": "sprout",
    "BlindOrVisuallyImpaired": "glasses",
    "Disabled": "accessibility",
    "LongTermDisability": "calendar-clock",
    # Acute needs
    "Food": "apple",
    "Baby_supplies": "baby",
    "Housing": "house",
    "Support": "messages-square",
    "Child_development": "shapes",
    "Job_resources": "briefcase-business",
    "Dental_care": "smile",
    "Legal_services": "scale",
    "Savings": "piggy-bank",
    "Military": "shield",
    "Aging": "tree-deciduous",
    "Youth_development": "shapes",
    # Energy-calculator icons (resolved in transformItemIcon's switch, per PR #2142)
    "SurvivingSpouse": "user-round",
    "Wheelchair": "accessibility",
    "HeartRate": "square-activity",
}

# (config attribute, FormOption.option_type, has you/them split). Person-less sections use
# the "all" sentinel.
FORM_OPTION_SECTIONS = [
    ("acute_condition", False),
    ("health_insurance", True),
    ("condition", True),
]


class Command(BaseCommand):
    help = "Create and add config data to database"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("white_labels", nargs="*", type=str, help="The list of states to update the config for")
        parser.add_argument(
            "-a",
            "--all",
            action=argparse.BooleanOptionalAction,
            help="Update all states",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Fail (and roll back) if any config _icon key has no Lucide mapping, instead of "
            "defaulting it to circle-dot. Intended for CI / pre-merge checks.",
        )

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        # Config _icon keys encountered with no ICON_LUCIDE_MAP entry, collected across all white
        # labels for a single end-of-run summary (and to drive --strict).
        self._unmapped_icons: set[str] = set()

        # Icons and translations are otherwise re-resolved for every option on every white label,
        # but the icon vocabulary is a small fixed set and many labels recur across sections/white
        # labels. Cache both across the run so each is resolved with at most one DB round-trip
        # instead of one per option — the seed's main source of N+1 queries.
        self._icon_cache: dict[str, Icon] = {}
        self._translation_cache: dict[str, Translation] = {}

        white_labels_to_update = white_label_config.keys() if options["all"] else options["white_labels"]

        if len(white_labels_to_update) == 0:
            self.stdout.write(
                self.style.ERROR(
                    "No white labels selected. Use --all to select all white labels, or list them individually"
                )
            )
            return

        for white_label_code in white_labels_to_update:
            if white_label_code not in white_label_config:
                self.stdout.write(self.style.WARNING(f'White label for "{white_label_code}" does not exist'))
                continue

            WhiteLabelData = white_label_config[white_label_code]

            try:
                white_label = WhiteLabelData.get_white_label()
            except ObjectDoesNotExist:
                self.stdout.write(self.style.WARNING(f'White label for "{white_label_code}" is not in the database'))
                continue

            # Save referrer_data to database
            Configuration.objects.update_or_create(
                name="referrer_data",
                white_label=white_label,
                defaults={"data": WhiteLabelData.referrer_data, "active": True},
            )

            # Save experiments to database (with validation)
            experiments_data = WhiteLabelData.experiments

            Configuration.objects.update_or_create(
                name="experiments",
                white_label=white_label,
                defaults={"data": experiments_data, "active": True},
            )

            # Save footer_data to database
            Configuration.objects.update_or_create(
                name="footer_data",
                white_label=white_label,
                defaults={"data": WhiteLabelData.footer_data, "active": True},
            )

            # Save language_options to database
            Configuration.objects.update_or_create(
                name="language_options",
                white_label=white_label,
                defaults={"data": WhiteLabelData.language_options, "active": True},
            )

            # Save feedback_links to database
            Configuration.objects.update_or_create(
                name="feedback_links",
                white_label=white_label,
                defaults={"data": WhiteLabelData.feedback_links, "active": True},
            )

            # Save override_text to database
            Configuration.objects.update_or_create(
                name="override_text",
                white_label=white_label,
                defaults={"data": WhiteLabelData.override_text, "active": True},
            )

            if WhiteLabelData.is_default:
                continue

            # Save state to database
            Configuration.objects.update_or_create(
                name="state",
                white_label=white_label,
                defaults={"data": WhiteLabelData.state, "active": True},
            )

            # Save banner_messages to database
            Configuration.objects.update_or_create(
                name="banner_messages",
                white_label=white_label,
                defaults={"data": WhiteLabelData.banner_messages, "active": True},
            )

            # Save acute_condition_options to database
            Configuration.objects.update_or_create(
                name="public_charge_rule",
                white_label=white_label,
                defaults={"data": WhiteLabelData.public_charge_rule, "active": True},
            )

            # Save acute_condition_options to database
            Configuration.objects.update_or_create(
                name="more_help_options",
                white_label=white_label,
                defaults={"data": WhiteLabelData.more_help_options, "active": True},
            )

            # Save acute_condition_options to database
            Configuration.objects.update_or_create(
                name="acute_condition_options",
                white_label=white_label,
                defaults={"data": WhiteLabelData.acute_condition_options, "active": True},
            )

            # Save sign_up_options to database
            Configuration.objects.update_or_create(
                name="sign_up_options",
                white_label=white_label,
                defaults={"data": WhiteLabelData.sign_up_options, "active": True},
            )

            # Save relationship_options to database
            Configuration.objects.update_or_create(
                name="relationship_options",
                white_label=white_label,
                defaults={"data": WhiteLabelData.relationship_options, "active": True},
            )

            # Save income_categories to database
            Configuration.objects.update_or_create(
                name="income_categories",
                white_label=white_label,
                defaults={"data": WhiteLabelData.income_categories, "active": True},
            )

            # Save income_options_by_category to database (nested by category)
            Configuration.objects.update_or_create(
                name="income_options_by_category",
                white_label=white_label,
                defaults={"data": WhiteLabelData.income_options_by_category, "active": True},
            )

            # Save health_insurance_options to database
            Configuration.objects.update_or_create(
                name="health_insurance_options",
                white_label=white_label,
                defaults={"data": WhiteLabelData.health_insurance_options, "active": True},
            )

            # Save frequency_options to database
            Configuration.objects.update_or_create(
                name="frequency_options",
                white_label=white_label,
                defaults={"data": WhiteLabelData.frequency_options, "active": True},
            )

            # Save expense_categories to database
            Configuration.objects.update_or_create(
                name="expense_categories",
                white_label=white_label,
                defaults={"data": WhiteLabelData.expense_categories, "active": True},
            )

            # Save expense_options_by_category to database
            Configuration.objects.update_or_create(
                name="expense_options_by_category",
                white_label=white_label,
                defaults={"data": WhiteLabelData.expense_options_by_category, "active": True},
            )

            # Save condition_options to database
            Configuration.objects.update_or_create(
                name="condition_options",
                white_label=white_label,
                defaults={"data": WhiteLabelData.condition_options, "active": True},
            )

            # Dual-write the you/them/all form options into the FormOption / Icon tables
            # (MFB-1200). The Configuration rows above remain the source of truth consumed by
            # the frontend until the unified endpoint (MFB-1247) and its consumer (MFB-1248)
            # ship; this keeps the new tables in sync in the meantime. Placed after the
            # is_default guard so _default is skipped, matching the Configuration rows above.
            self._seed_form_options(white_label, WhiteLabelData)

            # Save counties_by_zipcode to database
            Configuration.objects.update_or_create(
                name="counties_by_zipcode",
                white_label=white_label,
                defaults={"data": WhiteLabelData.counties_by_zipcode, "active": True},
            )

            # Save category_benefits to database
            Configuration.objects.update_or_create(
                name="category_benefits",
                white_label=white_label,
                defaults={"data": WhiteLabelData.category_benefits, "active": True},
            )

            # Save consent_to_contact to database
            Configuration.objects.update_or_create(
                name="consent_to_contact",
                white_label=white_label,
                defaults={"data": WhiteLabelData.consent_to_contact, "active": True},
            )

            # Save privacy_policy to database
            Configuration.objects.update_or_create(
                name="privacy_policy",
                white_label=white_label,
                defaults={"data": WhiteLabelData.privacy_policy, "active": True},
            )

            # Save current_benefits to database
            Configuration.objects.update_or_create(
                name="current_benefits",
                white_label=white_label,
                defaults={"data": WhiteLabelData.current_benefits, "active": True},
            )

            # Save communications to database
            Configuration.objects.update_or_create(
                name="communications",
                white_label=white_label,
                defaults={"data": WhiteLabelData.communications, "active": True},
            )

        # Surface any icon drift once, rather than one easy-to-miss warning per occurrence.
        if self._unmapped_icons:
            unmapped = ", ".join(sorted(self._unmapped_icons))
            message = (
                f"{len(self._unmapped_icons)} config icon(s) had no Lucide mapping and "
                f'defaulted to "{FALLBACK_LUCIDE_NAME}": {unmapped}. '
                "Add them to ICON_LUCIDE_MAP (and the frontend OPTION_CARD_ICON_MAP)."
            )
            if options["strict"]:
                # Raising inside the atomic handle rolls back the whole seed.
                raise CommandError(message)
            self.stdout.write(self.style.WARNING(message))

    def _seed_form_options(self, white_label: WhiteLabel, WhiteLabelData: type[ConfigurationData]) -> None:
        """Mirror the Python-config form options into the FormOption / Icon tables (MFB-1200)."""
        for option_type, is_person_split in FORM_OPTION_SECTIONS:
            selector = f"{option_type}_options"
            section = getattr(WhiteLabelData, selector, {}) or {}

            if is_person_split:
                person_groups = [(person, section.get(person, {})) for person in ("you", "them")]
            else:
                person_groups = [("all", section)]

            seeded_ids = []
            for person, options in person_groups:
                for order, (value, entry) in enumerate(options.items()):
                    icon = self._get_or_create_icon(entry.get("icon", {}).get("_icon"))
                    text = self._get_or_create_translation(entry.get("text", {}))
                    form_option, _ = FormOption.objects.update_or_create(
                        white_label=white_label,
                        option_type=option_type,
                        person=person,
                        value=value,
                        defaults={"icon": icon, "text": text, "order": order, "active": True},
                    )
                    seeded_ids.append(form_option.id)

            # Reconcile: drop rows for this white label + option type that are no longer in the
            # Python config, so the table converges to the config on every run (mirroring how a
            # Configuration JSON blob drops removed keys when it is overwritten). The Translation
            # a pruned row pointed at is intentionally left in place — translations are long-lived
            # and may be shared; only the FormOption link is removed.
            FormOption.objects.filter(white_label=white_label, option_type=option_type).exclude(
                id__in=seeded_ids
            ).delete()

    def _get_or_create_icon(self, icon_name: str | None) -> Icon:
        """Upsert an Icon row for the config _icon key, resolving its Lucide name from the map.
        A missing _icon or one with no mapping both fall back to circle-dot, so the API never
        serves a null icon and both cases render like the frontend's own fallback. lucide_name is
        frontend-derived, so overwriting it to match the map on each run is intended."""
        if not icon_name:
            icon_name = FALLBACK_LUCIDE_NAME
            lucide_name = FALLBACK_LUCIDE_NAME
        else:
            lucide_name = ICON_LUCIDE_MAP.get(icon_name)
            if lucide_name is None:
                lucide_name = FALLBACK_LUCIDE_NAME
                self._unmapped_icons.add(icon_name)

        cached = self._icon_cache.get(icon_name)
        if cached is not None:
            return cached

        icon, _ = Icon.objects.update_or_create(name=icon_name, defaults={"lucide_name": lucide_name})
        self._icon_cache[icon_name] = icon
        return icon

    def _get_or_create_translation(self, text: dict) -> Translation:
        """Reuse an existing Translation by label (do not clobber human/auto translations);
        create it from the config default message only when missing (MFB-1200 decision)."""
        label = text.get("_label")
        if not label:
            # Every audited config entry has a text._label; fail loudly rather than silently
            # seeding a null-label translation if that assumption is ever violated.
            raise CommandError(f"Form option config entry is missing text._label (entry: {text!r}).")

        cached = self._translation_cache.get(label)
        if cached is not None:
            return cached

        translation = Translation.objects.filter(label=label).first()
        if translation is None:
            translation = Translation.objects.add_translation(label, default_message=text.get("_default_message", ""))
        self._translation_cache[label] = translation
        return translation

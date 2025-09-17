from django.core.management.base import BaseCommand
from django.conf import settings
from decouple import config
from hubspot import HubSpot
from hubspot.crm.contacts.exceptions import ForbiddenException
from authentication.models import User
from integrations.models import Link
from programs.models import Document, Navigator, Program, TranslationOverride, UrgentNeed, WarningMessage
from screener.models import WhiteLabel
from translations.models import BLANK_TRANSLATION_PLACEHOLDER, Translation
from configuration.models import Configuration
import argparse
import json


class Command(BaseCommand):
    help = "Check that we can't read from HubSpot, and there is no PII in the database"

    HUB_SPOT_TEXT = "Can't read Hub Spot"
    PII_IN_DB_TEXT = "PII not in the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "white_label",
            nargs=None,
            help="What white label to check",
        )
        parser.add_argument(
            "-s",
            "--strict",
            action=argparse.BooleanOptionalAction,
            help="Compare the website hashes to the stored hashes",
        )
        parser.add_argument(
            "--skip-links",
            action=argparse.BooleanOptionalAction,
            help="Skip the link check",
        )

    def handle(self, *args, **options):
        self.stdout.write("")

        if not options["skip_links"]:
            self._check_links(options["white_label"], options["strict"])
            self.stdout.write("")

        self._output_condition(self._cant_read_hubspot(), self.HUB_SPOT_TEXT)
        self._output_condition(self._no_pii_in_db(), self.PII_IN_DB_TEXT)

    def _cant_read_hubspot(self) -> bool:
        client = HubSpot(access_token=config("HUBSPOT_CENTRAL"))

        try:
            client.crm.contacts.basic_api.get_page(limit=1, archived=False)
            return False
        except ForbiddenException as e:
            return True
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Exception when calling basic_api->get_page: {e}"))
            return False

    def _no_pii_in_db(self) -> bool:
        users = User.objects.filter(is_staff=False, external_id__isnull=True, auth_token__isnull=True)

        if len(users) > 0:
            return False
        return True

    def _check_links(self, white_label: str, strict: bool = False) -> bool:
        links = self._get_links(white_label)

        Link.objects.filter(white_label__code=white_label).update(in_use=False)

        white_label = WhiteLabel.objects.get(code=white_label)

        for link in links:
            if link == BLANK_TRANSLATION_PLACEHOLDER or link == "":
                continue

            try:
                link_model: Link = Link.objects.get(link=link)
                link_model.in_use = True
                link_model.save()
            except Link.DoesNotExist:
                link_model: Link = Link.objects.create(link=link, validated=False, in_use=True, white_label=white_label)

            link_model.validate()

            if strict:
                valid = link_model.validated
            else:
                valid = Link.good_status_code(link_model.status_code)

            self._output_condition(valid, f"{link} {link_model.status_code}")

    def _get_links(self, white_label: str) -> list[str]:
        program_links = [
            p.apply_button_link for p in Program.objects.filter(active=True, white_label__code=white_label)
        ]
        urgent_need_links = [u.link for u in UrgentNeed.objects.filter(active=True, white_label__code=white_label)]
        navigator_links = [
            n.assistance_link
            for n in Navigator.objects.filter(programs_sorted__isnull=False, white_label__code=white_label)
        ]
        translation_override_links = [
            o.translation
            for o in TranslationOverride.objects.filter(
                field__in=["apply_button_link", "learn_more_link"], white_label__code=white_label
            )
        ]
        document_links = [
            p.link_url for p in Document.objects.filter(program_documents__isnull=False, white_label__code=white_label)
        ]
        warning_message_links = [
            p.link_url for p in WarningMessage.objects.filter(programs__isnull=False, white_label__code=white_label)
        ]

        public_charge_links = [
            json.loads(c.data)["link"]
            for c in Configuration.objects.filter(name="public_charge_rule", white_label__code=white_label)
        ]

        more_help_option_links = []
        for config in Configuration.objects.filter(name="more_help_options", white_label__code=white_label):
            more_help_option_links.extend(
                [o["link"] for o in json.loads(config.data)["moreHelpOptions"] if "link" in o]
            )

        privacy_policy_links = []
        for config in Configuration.objects.filter(name="privacy_policy", white_label__code=white_label):
            privacy_policy_links.extend(json.loads(config.data).values())

        consent_to_contact_links = []
        for config in Configuration.objects.filter(name="consent_to_contact", white_label__code=white_label):
            consent_to_contact_links.extend(json.loads(config.data).values())

        feedback_links = []
        for config in Configuration.objects.filter(name="feedback_links", white_label__code=white_label):
            feedback_links.extend(json.loads(config.data).values())

        config_links = [*public_charge_links, *more_help_option_links, *privacy_policy_links, *consent_to_contact_links]

        links = {
            *self._get_translation_links(program_links),
            *self._get_translation_links(urgent_need_links),
            *self._get_translation_links(navigator_links),
            *self._get_translation_links(translation_override_links),
            *self._get_translation_links(document_links),
            *self._get_translation_links(warning_message_links),
            *config_links,
        }

        links = list(links)
        links.sort()

        return links

    def _get_translation_links(self, translations: list[Translation]) -> list[str]:
        links = set()
        for translation in translations:
            for lang_setting in settings.LANGUAGES:
                lang = lang_setting[0]
                translation.set_current_language(lang)

                links.add(translation.text)

        return list(links)

    def _output_condition(self, validated: bool, message: str):
        text = f"{message}: {'VALIDATED' if validated else 'FAILED'}"

        if validated:
            self.stdout.write(self.style.SUCCESS(text))
        else:
            self.stdout.write(self.style.ERROR(text))

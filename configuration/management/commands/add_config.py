from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.db import transaction
from configuration.models import (
    Configuration,
)
from configuration.white_labels import white_label_config
import argparse


class Command(BaseCommand):
    help = "Create and add config data to database"

    def add_arguments(self, parser):
        parser.add_argument("white_labels", nargs="*", type=str, help="The list of states to update the config for")
        parser.add_argument(
            "-a",
            "--all",
            action=argparse.BooleanOptionalAction,
            help="Update all states",
        )

    @transaction.atomic
    def handle(self, *args, **options):
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

            # Save referral_options to database
            Configuration.objects.update_or_create(
                name="referral_options",
                white_label=white_label,
                defaults={"data": WhiteLabelData.referral_options, "active": True},
            )

            # Save income_options to database
            Configuration.objects.update_or_create(
                name="income_options",
                white_label=white_label,
                defaults={"data": WhiteLabelData.income_options, "active": True},
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

            # Save expense_options to database
            Configuration.objects.update_or_create(
                name="expense_options",
                white_label=white_label,
                defaults={"data": WhiteLabelData.expense_options, "active": True},
            )

            # Save condition_options to database
            Configuration.objects.update_or_create(
                name="condition_options",
                white_label=white_label,
                defaults={"data": WhiteLabelData.condition_options, "active": True},
            )

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

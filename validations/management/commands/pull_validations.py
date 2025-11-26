from django.core.management.base import BaseCommand
from decouple import config
from getpass import getpass
from django.db import transaction
from screener.models import Screen
from screener.serializers import ScreenSerializer
from validations.models import Validation
from validations.serializers import ValidationSerializer
import requests


class Command(BaseCommand):
    help = "Pull the validations from target environment"

    def add_arguments(self, parser):
        parser.add_argument(
            "domain",
            nargs=None,
            help="Domain of the environment to pull from",
        )
        parser.add_argument(
            "--no-bypass",
            action="store_true",
            help="Do not use the environment variable for the API key; prompt for it instead.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        domain = options["domain"]
        if options["no_bypass"]:
            api_key = getpass("API key: ")
        else:
            api_key = config("DEV_API_KEY", "")
            if not api_key:
                api_key = getpass("API key: ")

        response = requests.get(f"{domain}/api/validations", timeout=120)

        validations = response.json()

        updated_screens = set()
        for data in validations:
            screen_uuid = data["screen_uuid"]

            if screen_uuid not in updated_screens:
                self._upsert_screen(screen_uuid, domain, api_key)
                updated_screens.add(screen_uuid)

            self._upsert_validation(data)

    def _upsert_screen(self, uuid: str, domain: str, api_key: str):
        remote_screen = self._get_screen_from_remote(uuid, domain, api_key)

        try:
            # update
            screen = Screen.objects.get(uuid=uuid)
            serializer = ScreenSerializer(screen, data=remote_screen, force=True)
        except Screen.DoesNotExist:
            # create
            serializer = ScreenSerializer(data=remote_screen)

        serializer.is_valid(raise_exception=True)

        screen = serializer.save()

        screen.uuid = uuid
        screen.save()

        return screen

    def _upsert_validation(self, data):
        try:
            # update
            validation = Validation.objects.get(screen__uuid=data["screen_uuid"], program_name=data["program_name"])
            serializer = ValidationSerializer(validation, data=data)
        except Validation.DoesNotExist:
            # create
            serializer = ValidationSerializer(data=data)

        serializer.is_valid(raise_exception=True)
        return serializer.save()

    def _get_screen_from_remote(self, uuid: str, domain: str, api_key: str):
        header = {
            "Authorization": f"Token {api_key}",
        }
        response = requests.get(f"{domain}/api/screens/{uuid}", headers=header, timeout=120)

        return response.json()

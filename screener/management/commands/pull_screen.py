from django.core.management.base import BaseCommand
from decouple import config
from getpass import getpass

from django.db import transaction
from screener.models import Screen
from screener.serializers import ScreenSerializer
import requests


class Command(BaseCommand):
    help = "Pull a single screen from a remote environment into the local database"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "domain",
            nargs=None,
            help="Domain of the environment to pull from",
        )
        parser.add_argument(
            "uuid",
            nargs=None,
            help="UUID of the screen to pull",
        )
        parser.add_argument(
            "--no-bypass",
            action="store_true",
            help="Do not use the environment variable for the API key; prompt for it instead.",
        )

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        domain = options["domain"]
        uuid = options["uuid"]

        if options["no_bypass"]:
            api_key = getpass("API key: ")
        else:
            api_key = config("DEV_API_KEY", "")
            if not api_key:
                api_key = getpass("API key: ")

        remote_screen = self._get_screen_from_remote(uuid, domain, api_key)

        remote_screen.pop("user", None)

        self._upsert_screen(uuid, remote_screen)

    def _upsert_screen(self, uuid: str, remote_screen: dict) -> None:
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

        white_label = remote_screen.get("white_label", screen.white_label)
        results_url = f"http://localhost:3000/{white_label}/{uuid}/results/benefits"

        self.stdout.write(f"Screen pulled successfully. Results: {results_url}")

    def _get_screen_from_remote(self, uuid: str, domain: str, api_key: str):
        header = {
            "Authorization": f"Token {api_key}",
        }
        response = requests.get(f"{domain}/api/screens/{uuid}", headers=header)

        if response.status_code != 200:
            self.stderr.write(f"Failed to fetch screen with UUID {uuid} from {domain}.")
            self.stderr.write(f"Response: {response.status_code} - {response.text}")

        return response.json()

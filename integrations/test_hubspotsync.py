"""Tests for the legacy Colorado-only hubspotsync command."""

from io import StringIO
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from integrations.management.commands.hubspotsync import Command

MODULE = "integrations.management.commands.hubspotsync"


class TestHubspotSyncFailures(SimpleTestCase):
    def _run_with_failing_integration(self) -> tuple[Command, dict]:
        user = MagicMock(id=7)
        command = Command()

        with (
            patch(f"{MODULE}.User") as user_model,
            patch(f"{MODULE}.Screen") as screen_model,
            patch(f"{MODULE}.CoHubSpotIntegration") as integration,
            patch(f"{MODULE}.time.sleep"),
        ):
            user_model.objects.filter.return_value.filter.return_value.filter.return_value = [user]
            screen_model.objects.filter.return_value.order_by.return_value.first.return_value = MagicMock()
            integration.return_value.add.side_effect = RuntimeError("Email address person@example.com is invalid")

            status = command.sync_mfb_hubspot_users(limit=5)

        return command, status

    def test_failure_is_recorded_with_the_exception_type_not_an_unbound_variable(self) -> None:
        _, status = self._run_with_failing_integration()

        self.assertEqual(status["completed"], [])
        self.assertEqual(status["failed"], [(7, "RuntimeError")])

    def test_failure_does_not_record_the_error_message(self) -> None:
        # HubSpot error text can include the rejected value, such as an email address.
        _, status = self._run_with_failing_integration()

        self.assertNotIn("person@example.com", str(status))

    def test_failures_are_reported_as_failures(self) -> None:
        command = Command()
        command.stdout = StringIO()
        status = {"processed": 1, "completed": [], "failed": [(7, "ApiException")]}

        with patch.object(Command, "sync_mfb_hubspot_users", return_value=status):
            command.handle(limit=1)

        output = command.stdout.getvalue()
        self.assertIn("Failed to sync 1 users", output)
        self.assertIn("Failed to sync user 7: ApiException", output)
        self.assertNotIn("Successfully synced user", output)

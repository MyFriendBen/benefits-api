from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from screener.models import HouseholdMember, IncomeStream, Screen, WhiteLabel


class TestBatchSnapshots(TestCase):
    def test_screens_reach_eligibility_prefetched(self):
        """Calculators re-read members and incomes thousands of times per screen; they must come from the prefetch."""
        white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        user = get_user_model().objects.create(email_or_cell="batch@example.com")
        screen = Screen.objects.create(
            white_label=white_label,
            zipcode="78701",
            household_size=1,
            completed=True,
            agree_to_tos=True,
            is_test=False,
            is_test_data=False,
            user=user,
        )
        member = HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=40)
        IncomeStream.objects.create(
            screen=screen, household_member=member, type="wages", amount=100, frequency="monthly"
        )

        seen = []

        # Records the query count rather than asserting inside: the command catches every
        # exception per screen, so a failed assertion here would be swallowed.
        def fake_eligibility(s, batch=False):
            with CaptureQueriesContext(connection) as queries:
                counts = [len(m.income_streams.all()) for m in s.household_members.all()] + [len(s.expenses.all())]
            seen.append((counts, len(queries)))

        with patch(
            "screener.management.commands.batch_snapshots.eligibility_results", side_effect=fake_eligibility
        ), patch("screener.management.commands.batch_snapshots.time.sleep"):
            call_command("batch_snapshots", white_label="test")

        self.assertEqual(seen, [([1, 0], 0)])

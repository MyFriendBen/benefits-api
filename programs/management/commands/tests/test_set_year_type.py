from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from programs.models import FederalPoveryLimit, Program
from screener.models import WhiteLabel


class SetYearTypeCommandTests(TestCase):
    """set_year_type saves per-instance so it goes through Program.save() and keeps
    `year` in sync with `year_type`, rather than a bulk .update() that would only
    set year_type and leave `year` to drift (MFB-564 finding #3/#9)."""

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        # 0171_seed_dynamic_fpl_rows already seeds these into every migrated DB
        # (including the test DB), so get_or_create rather than assuming a clean
        # slate -- same reason that migration itself uses get_or_create.
        self.calendar_fpl, _ = FederalPoveryLimit.objects.get_or_create(
            year="THIS_YEAR_CALENDAR", defaults={"period": "2026"}
        )
        self.fiscal_fpl, _ = FederalPoveryLimit.objects.get_or_create(
            year="THIS_YEAR_FISCAL", defaults={"period": "2025"}
        )
        self.co_snap = Program.objects.new_program(self.white_label.code, "snap", external_name="co_snap")
        self.co_medicaid = Program.objects.new_program(self.white_label.code, "medicaid", external_name="co_medicaid")

    def test_programs_flag_updates_year_type_and_year_together(self):
        call_command("set_year_type", "fiscal_year", "--programs", "co_snap")
        self.co_snap.refresh_from_db()
        self.assertEqual(self.co_snap.year_type, "fiscal_year")
        self.assertEqual(self.co_snap.year_id, self.fiscal_fpl.id)

        # untouched
        self.co_medicaid.refresh_from_db()
        self.assertEqual(self.co_medicaid.year_type, "hardcoded")
        self.assertIsNone(self.co_medicaid.year_id)

    def test_all_flag_updates_every_program(self):
        call_command("set_year_type", "calendar_year", "--all")
        self.co_snap.refresh_from_db()
        self.co_medicaid.refresh_from_db()
        for program in (self.co_snap, self.co_medicaid):
            self.assertEqual(program.year_type, "calendar_year")
            self.assertEqual(program.year_id, self.calendar_fpl.id)

    def test_dry_run_makes_no_changes(self):
        call_command("set_year_type", "calendar_year", "--all", "--dry-run")
        self.co_snap.refresh_from_db()
        self.assertEqual(self.co_snap.year_type, "hardcoded")
        self.assertIsNone(self.co_snap.year_id)

    def test_all_and_programs_together_is_rejected(self):
        with self.assertRaises(CommandError):
            call_command("set_year_type", "calendar_year", "--all", "--programs", "co_snap")

    def test_neither_all_nor_programs_is_rejected(self):
        with self.assertRaises(CommandError):
            call_command("set_year_type", "calendar_year")

from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from programs.models import FederalPoveryLimit, Program
from screener.models import WhiteLabel


class RollProgramYearsCommandTests(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.fpl_2025, _ = FederalPoveryLimit.objects.get_or_create(year="2025", defaults={"period": "2025"})

    def _program(self, abbr, fpl, year_type="prior_tax_year", flip_month=1, year_offset=-1):
        program = Program.objects.new_program(self.white_label.code, abbr)
        program.year = fpl
        program.year_type = year_type
        program.flip_month = flip_month
        program.year_offset = year_offset
        program.save(update_fields=["year", "year_type", "flip_month", "year_offset"])
        return program

    def test_rolls_programs_past_flip_month(self):
        program = self._program("federal_ctc", self.fpl_2025, flip_month=1)
        # today.month=11 >= flip_month=1, so it should roll to 2026 + (-1) = 2025
        # Use year=2026 as target so period becomes 2025
        call_command("roll_program_years", "--year", "2026", "--all")
        program.refresh_from_db()
        self.assertEqual(program.year.period, "2025")

    def test_skips_programs_before_flip_month(self):
        program = self._program("federal_ctc", self.fpl_2025, flip_month=12)
        # Patch today to November so flip_month=12 hasn't arrived yet
        with patch("programs.management.commands.roll_program_years.date") as mock_date:
            mock_date.today.return_value = mock_date.today.return_value.__class__(2026, 11, 1)
            from datetime import date as real_date

            mock_date.today.return_value = real_date(2026, 11, 1)
            call_command("roll_program_years", "--year", "2026", "--all")
        program.refresh_from_db()
        self.assertEqual(program.year_id, self.fpl_2025.id)

    def test_respects_year_offset(self):
        program = self._program("mo_wftc", self.fpl_2025, flip_month=1, year_offset=-1)
        call_command("roll_program_years", "--year", "2026", "--all")
        program.refresh_from_db()
        self.assertEqual(program.year.period, "2025")

    def test_dry_run_makes_no_changes(self):
        program = self._program("federal_ctc", self.fpl_2025, flip_month=1)
        call_command("roll_program_years", "--year", "2026", "--all", "--dry-run")
        program.refresh_from_db()
        self.assertEqual(program.year_id, self.fpl_2025.id)

    def test_missing_fpl_data_raises_error(self):
        with self.assertRaises(CommandError):
            call_command("roll_program_years", "--year", "2099", "--all")

    def test_skips_hardcoded_programs(self):
        program = self._program("snap", self.fpl_2025, year_type="hardcoded", year_offset=0)
        call_command("roll_program_years", "--year", "2026", "--all")
        program.refresh_from_db()
        self.assertEqual(program.year_id, self.fpl_2025.id)

    def test_skips_sentinel_programs(self):
        calendar_fpl, _ = FederalPoveryLimit.objects.get_or_create(
            year="THIS_YEAR_CALENDAR", defaults={"period": "2026"}
        )
        program = self._program("medicaid", calendar_fpl, year_type="calendar_year", year_offset=0)
        call_command("roll_program_years", "--year", "2026", "--all")
        program.refresh_from_db()
        self.assertEqual(program.year_id, calendar_fpl.id)

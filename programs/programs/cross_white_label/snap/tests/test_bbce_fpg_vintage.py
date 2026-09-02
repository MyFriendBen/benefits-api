"""SNAP reads its monthly output at today's month, so the BBCE limit tracks today's rules.

States re-base their broad-based categorical eligibility gross income limit onto the
current year's poverty guidelines on their own schedule, and PolicyEngine reads that
schedule off the month asked about. See `Snap.pe_period_month`.
"""

from datetime import date
from unittest.mock import patch

from django.test import TestCase

from programs.models import FederalPoveryLimit, Program
from programs.programs.cross_white_label.snap.base import Snap
from programs.programs.cross_white_label.snap.co import CoSnap
from programs.programs.cross_white_label.snap.il import IlSnap
from programs.programs.cross_white_label.snap.ks import KsSnap
from programs.programs.cross_white_label.snap.ma import MaSnap
from programs.programs.cross_white_label.snap.mo import MoSnap
from programs.programs.cross_white_label.snap.nc import NcSnap
from programs.programs.cross_white_label.snap.tx import TxSnap
from programs.programs.cross_white_label.snap.wa import WaFap, WaSnap
from screener.models import Screen, WhiteLabel

SNAP_VARIANTS = (Snap, CoSnap, IlSnap, KsSnap, MaSnap, MoSnap, NcSnap, TxSnap, WaSnap, WaFap)


class SnapMonthTestCase(TestCase):
    def setUp(self):
        self._programs = {}
        self.white_label, _ = WhiteLabel.objects.get_or_create(
            code="co", defaults={"name": "Colorado", "state_code": "CO"}
        )
        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="80504", county="Boulder County", household_size=1, completed=False
        )

    def calculator(self, period, calculator=CoSnap):
        fpl, _ = FederalPoveryLimit.objects.get_or_create(year=period, defaults={"period": period})
        program = self._programs.get(calculator.program_code)
        if program is None:
            program = Program.objects.filter(
                white_label=self.white_label, name_abbreviated=calculator.program_code
            ).first()
            if program is None:
                program = Program.objects.new_program(self.white_label.code, calculator.program_code)
            self._programs[calculator.program_code] = program
        program.year = fpl
        program.save()
        return calculator(self.screen, program, {})


class TestMonthFollowsToday(SnapMonthTestCase):
    def test_current_year_reads_the_current_month(self):
        """In September we ask PolicyEngine about September."""
        with patch("programs.programs.cross_white_label.snap.base.date") as mock_date:
            mock_date.today.return_value = date(2026, 9, 2)
            self.assertEqual(self.calculator("2026").pe_period_month, "09")

    def test_the_month_is_zero_padded(self):
        """`YYYY-MM` is a string PolicyEngine parses -- "2026-9" is not a period."""
        with patch("programs.programs.cross_white_label.snap.base.date") as mock_date:
            mock_date.today.return_value = date(2026, 1, 15)
            calculator = self.calculator("2026")
            self.assertEqual(calculator.pe_period_month, "01")
            self.assertEqual(calculator.pe_month_period, "2026-01")

    def test_every_month_of_the_current_year_is_reachable(self):
        """No month is skipped or clamped away while the configured year is the current one."""
        for month in range(1, 13):
            with self.subTest(month=month):
                with patch("programs.programs.cross_white_label.snap.base.date") as mock_date:
                    mock_date.today.return_value = date(2026, month, 1)
                    self.assertEqual(self.calculator("2026").pe_period_month, f"{month:02d}")

    def test_october_reads_october_so_a_fiscal_year_state_re_bases(self):
        """Colorado's BBCE limit moves to the new guidelines on Oct 1."""
        with patch("programs.programs.cross_white_label.snap.base.date") as mock_date:
            mock_date.today.return_value = date(2026, 10, 1)
            self.assertEqual(self.calculator("2026").pe_period_month, "10")


class TestMonthStaysInsideTheRequestedYear(SnapMonthTestCase):
    """`pe_period` comes from the program's configured FPL row, which may lag or lead
    today. The month still has to name one the requested year actually had."""

    def test_a_past_year_reads_december(self):
        with patch("programs.programs.cross_white_label.snap.base.date") as mock_date:
            mock_date.today.return_value = date(2026, 9, 2)
            self.assertEqual(self.calculator("2025").pe_period_month, "12")

    def test_a_future_year_reads_january(self):
        with patch("programs.programs.cross_white_label.snap.base.date") as mock_date:
            mock_date.today.return_value = date(2026, 9, 2)
            self.assertEqual(self.calculator("2027").pe_period_month, "01")

    def test_a_past_year_does_not_borrow_a_month_from_today(self):
        """December is the state a finished year ended in; today's month is meaningless."""
        with patch("programs.programs.cross_white_label.snap.base.date") as mock_date:
            mock_date.today.return_value = date(2026, 3, 15)
            self.assertNotEqual(self.calculator("2024").pe_period_month, "03")
            self.assertEqual(self.calculator("2024").pe_period_month, "12")

    def test_a_non_numeric_period_falls_back_rather_than_raising(self):
        """Defensive: misconfiguration degrades to a month and warns, rather than raising
        inside eligibility calculation and taking down every program on the screen."""
        with patch("programs.programs.cross_white_label.snap.base.date") as mock_date:
            mock_date.today.return_value = date(2026, 9, 2)
            with self.assertLogs("programs.programs.cross_white_label.snap.base", "WARNING"):
                self.assertEqual(self.calculator("not-a-year").pe_period_month, "01")


class TestEveryVariantInherits(SnapMonthTestCase):
    def test_all_snap_variants_read_the_same_month(self):
        """One screen carries every program, and the month is part of the period key a
        monthly output is read back at, so the variants must not disagree."""
        with patch("programs.programs.cross_white_label.snap.base.date") as mock_date:
            mock_date.today.return_value = date(2026, 9, 2)
            for calculator in SNAP_VARIANTS:
                with self.subTest(calculator=calculator.__name__):
                    self.assertEqual(self.calculator("2026", calculator).pe_period_month, "09")

    def test_no_variant_hardcodes_its_own_month(self):
        """A subclass overriding with a constant would silently stop tracking today."""
        for calculator in SNAP_VARIANTS:
            with self.subTest(calculator=calculator.__name__):
                self.assertIsInstance(calculator.pe_period_month, property)

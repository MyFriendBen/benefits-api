"""Migration 0193 moves "already has this benefit" rows from the state federal-CDCC copies
onto `federal_cdcc`, run against real rows the way the vintage migration tests do."""

import importlib

from django.apps import apps as django_apps
from django.test import TestCase

from programs.models import Program
from screener.models import CurrentBenefit, Screen, WhiteLabel

MIGRATION = "programs.migrations.0193_move_state_cdcc_current_benefits"


class TestMoveStateCdccCurrentBenefits(TestCase):
    def setUp(self):
        self.ks = WhiteLabel.objects.create(name="Kansas", code="ks", state_code="KS")
        self.mo = WhiteLabel.objects.create(name="Missouri", code="mo", state_code="MO")
        self.federal = WhiteLabel.objects.create(name="Federal Programs", code="federal")
        self.ks_federal = Program.objects.new_program(white_label="ks", name_abbreviated="ks_cdcc_federal")
        self.mo_federal = Program.objects.new_program(white_label="mo", name_abbreviated="mo_cdcc_federal")
        self.ks_cdcc = Program.objects.new_program(white_label="ks", name_abbreviated="ks_cdcc")
        # Migration module names start with a digit, so they can only be imported by string.
        self.migration = importlib.import_module(MIGRATION)

    def _federal_row(self) -> Program:
        return Program.objects.new_program(white_label="federal", name_abbreviated="federal_cdcc")

    def _screen(self, white_label: WhiteLabel, *programs: Program) -> Screen:
        screen = Screen.objects.create(white_label=white_label, zipcode="66101", household_size=1, completed=False)
        for program in programs:
            CurrentBenefit.objects.create(screen=screen, program=program)
        return screen

    def _names(self, screen: Screen) -> list[str]:
        return sorted(cb.program.name_abbreviated for cb in screen.current_benefits.select_related("program"))

    def test_rows_on_both_state_copies_move_to_the_federal_row(self):
        federal = self._federal_row()
        ks_screen = self._screen(self.ks, self.ks_federal)
        mo_screen = self._screen(self.mo, self.mo_federal)

        self.migration.forwards(django_apps, None)

        self.assertEqual(self._names(ks_screen), ["federal_cdcc"])
        self.assertEqual(self._names(mo_screen), ["federal_cdcc"])
        self.assertEqual(CurrentBenefit.objects.filter(program=federal).count(), 2)
        self.assertFalse(CurrentBenefit.objects.filter(program__in=[self.ks_federal, self.mo_federal]).exists())

    def test_a_screen_already_holding_the_federal_row_keeps_one_row(self):
        federal = self._federal_row()
        screen = self._screen(self.ks, self.ks_federal, federal)

        self.migration.forwards(django_apps, None)

        self.assertEqual(self._names(screen), ["federal_cdcc"])
        self.assertEqual(screen.current_benefits.count(), 1)

    def test_without_a_federal_row_nothing_is_touched(self):
        screen = self._screen(self.ks, self.ks_federal)

        with self.assertLogs(MIGRATION, level="WARNING") as logs:
            self.migration.forwards(django_apps, None)

        self.assertEqual(self._names(screen), ["ks_cdcc_federal"])
        self.assertIn("does not exist", logs.output[0])

    def test_kansas_own_credit_is_not_moved(self):
        """`ks_cdcc` is Kansas's state credit, not a copy of the federal one."""
        self._federal_row()
        screen = self._screen(self.ks, self.ks_cdcc, self.ks_federal)

        self.migration.forwards(django_apps, None)

        self.assertEqual(self._names(screen), ["federal_cdcc", "ks_cdcc"])

    def test_running_twice_changes_nothing_more(self):
        self._federal_row()
        screen = self._screen(self.mo, self.mo_federal)

        self.migration.forwards(django_apps, None)
        self.migration.forwards(django_apps, None)

        self.assertEqual(self._names(screen), ["federal_cdcc"])
        self.assertEqual(screen.current_benefits.count(), 1)

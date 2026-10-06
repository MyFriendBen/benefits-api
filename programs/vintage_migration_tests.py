"""The edition-correcting migrations agree with the vintage map, and actually move the rows.

`vintage_tests.py` keeps the map coherent without touching the database. These cover the
other half: that 0179/0180 move each program to the edition the map records, and that no
PolicyEngine CSFP calculator is left without an entry -- CO's `ede` (Everyday Eats) was, for
no reason but an abbreviation that doesn't say "csfp".
"""

import importlib

from django.apps import apps as django_apps
from django.test import SimpleTestCase, TestCase

from programs.models import FederalPoveryLimit, Program
from programs.vintage import PROGRAM_VINTAGE
from screener.models import WhiteLabel

CORRECTING_MIGRATIONS = (
    "programs.migrations.0179_correct_aca_coverage_year",
    "programs.migrations.0180_ssi_msp_csfp_current_edition",
)


def _migration(name):
    # Migration module names start with a digit, so they can only be imported by string.
    return importlib.import_module(name)


class TestCorrectionsMatchTheMap(SimpleTestCase):
    def test_every_correction_lands_on_the_recorded_edition(self):
        mismatches = []
        for name in CORRECTING_MIGRATIONS:
            for white_label, abbr, _from, to in _migration(name).CORRECTIONS:
                intent = PROGRAM_VINTAGE.get((white_label, abbr))
                if intent is None or intent.edition != to:
                    recorded = intent.edition if intent else "no entry"
                    mismatches.append(f"{name}: {white_label}/{abbr} -> {to}, map says {recorded}")

        self.assertEqual(mismatches, [], "\n  ".join(mismatches))

    def test_every_policyengine_csfp_calculator_has_a_vintage_entry(self):
        from integrations.clients.policyengine.registry import all_calculators
        from programs.programs.cross_white_label.csfp.base import CommoditySupplementalFoodProgram

        family = {
            code
            for code, cls in all_calculators.items()
            if issubclass(cls, CommoditySupplementalFoodProgram) and cls is not CommoditySupplementalFoodProgram
        }
        recorded = {abbr for _white_label, abbr in PROGRAM_VINTAGE}

        self.assertIn("ede", family, "Everyday Eats should be discovered as a CSFP calculator")
        self.assertEqual(family - recorded, set(), "CSFP calculators with no recorded edition")


class TestCsfpMigrationMovesEveryDayEats(TestCase):
    """Run 0180's forwards/backwards against real rows, matched the way it matches them."""

    def setUp(self):
        self.fpl_2025 = FederalPoveryLimit.objects.create(year="2025", period="2025")
        self.fpl_2026 = FederalPoveryLimit.objects.create(year="2026", period="2026")
        WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")
        self.migration = _migration("programs.migrations.0180_ssi_msp_csfp_current_edition")

    def _program(self, abbr, fpl):
        program = Program.objects.new_program(white_label="co", name_abbreviated=abbr)
        program.year = fpl
        program.save()
        return program

    def test_forwards_moves_ede_to_2026_and_backwards_restores_2025(self):
        ede = self._program("ede", self.fpl_2025)

        self.migration.forwards(django_apps, None)
        ede.refresh_from_db()
        self.assertEqual(ede.year.period, "2026")

        self.migration.backwards(django_apps, None)
        ede.refresh_from_db()
        self.assertEqual(ede.year.period, "2025")

    def test_forwards_leaves_ede_alone_when_it_is_not_on_2025(self):
        # Already corrected by hand, or moved somewhere unexpected: reported, not forced.
        ede = self._program("ede", self.fpl_2026)
        fpl_2024 = FederalPoveryLimit.objects.create(year="2024", period="2024")

        self.migration.forwards(django_apps, None)
        ede.refresh_from_db()
        self.assertEqual(ede.year.period, "2026")

        ede.year = fpl_2024
        ede.save()
        self.migration.forwards(django_apps, None)
        ede.refresh_from_db()
        self.assertEqual(ede.year.period, "2024")

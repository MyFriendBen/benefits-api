"""
Guards on the immigration labels declared in program config JSON.

`legal_status_required` is the only place immigration eligibility is expressed — calculators are
immigration-blind and the API just passes the list through to the frontend filter. A wrong label
here is a wrong eligibility answer tied to someone's immigration status, and two of the failure
modes are silent: the importer drops an unknown label with a warning nobody reads, and two programs
sharing a PolicyEngine variable double-count if their status lists overlap.
"""

import importlib.util
import json
from pathlib import Path

from django.test import SimpleTestCase

DATA_DIR = Path(__file__).resolve().parent.parent / "import_program_config_data" / "data"

# The labels the frontend understands, from `CitizenLabels` in
# benefits-calculator/src/Components/Results/Filter/citizenshipFilterConfig.tsx. The six
# user-selected statuses are the filter buttons; the rest are derived from household data. A label
# outside this set is dropped on import (LegalStatus.DoesNotExist) and silently never matches.
USER_SELECTED = {
    "citizen",
    "non_citizen",
    "gc_5plus",
    "gc_5less",
    "refugee",
    "otherWithWorkPermission",
}
CALCULATED = {
    "gc_18plus_no5",
    "gc_under18_no5",
    "otherHealthCarePregnant",
    "otherHealthCareUnder19",
    "otherHealthCareUnder21",
    "notPregnantOrUnder19ForOmniSalud",
    "notPregnantOrUnder19ForEmergencyMedicaid",
    "notPregnantForMassHealthLimited",
    "notPregnantOrChildForMassHealthLimited",
}
KNOWN_LABELS = USER_SELECTED | CALCULATED

# Programs subject to the five-year bar, with the statuses each should declare.
#
# SNAP exempts LPRs under 18 from the bar regardless of the status they adjusted from, so
# `gc_under18_no5` replaces bare `gc_5less`. TANF has no age-based exemption, so `gc_5less` simply
# comes off. `refugee` is not a federal-SNAP status — eligibility runs to citizens, LPRs,
# Cuban/Haitian entrants and COFA citizens — which is why it sits on state-funded wa_fap and on no
# SNAP program. The bar's exemption for people who adjusted to LPR *from* refugee status is a
# different thing: they hold a green card now, and expressing it needs a filter we do not have.
BAR_SUBJECT_PROGRAMS = {
    "wa_snap": {"citizen", "gc_5plus", "gc_under18_no5"},
    "wa_fap": {"gc_18plus_no5", "otherWithWorkPermission", "refugee"},
    "ks_snap": {"citizen", "gc_5plus", "gc_under18_no5"},
    "tx_snap": {"citizen", "gc_5plus", "gc_under18_no5"},
    "wa_tanf": {"citizen", "gc_5plus", "refugee", "otherWithWorkPermission"},
    "mo_tanf": {"citizen", "gc_5plus", "refugee", "otherWithWorkPermission"},
}

# Federal SNAP does not reach refugee or asylee status. Washington serves that group through
# state-funded FAP instead, which is itself evidence federal SNAP does not: a state would not fund
# a program for a population federal SNAP already covered.
SNAP_PROGRAMS_WITHOUT_REFUGEE = ("wa_snap", "ks_snap", "tx_snap")


def config_files():
    return sorted(DATA_DIR.glob("*_initial_config.json"))


def load_program(name):
    """Return the program section of the config declaring `name_abbreviated == name`."""
    for path in config_files():
        config = json.loads(path.read_text())
        if (config.get("program") or {}).get("name_abbreviated") == name:
            return config
    raise AssertionError(f"no config declares program '{name}'")


class LegalStatusLabelsAreKnownTest(SimpleTestCase):
    def test_every_declared_label_is_one_the_frontend_understands(self):
        unknown = {}

        for path in config_files():
            config = json.loads(path.read_text())

            declared = set((config.get("program") or {}).get("legal_status_required") or [])
            warnings = config.get("warning_messages") or []
            if "warning_message" in config:
                warnings = [*warnings, config["warning_message"]]
            for warning in warnings:
                declared |= set(warning.get("legal_statuses") or [])

            if declared - KNOWN_LABELS:
                unknown[path.name] = sorted(declared - KNOWN_LABELS)

        self.assertEqual(unknown, {}, f"unknown legal status labels are dropped on import: {unknown}")


class WarningMessageShapeTest(SimpleTestCase):
    def test_no_config_declares_both_warning_shapes(self):
        """
        `_warning_message_configs` accepts either "warning_message" (object) or "warning_messages"
        (array) and raises a CommandError when both are present. Adding a second warning to a
        config that used the singular shape means converting it, not appending alongside it.
        """
        both = [
            path.name
            for path in config_files()
            if {"warning_message", "warning_messages"} <= set(json.loads(path.read_text()))
        ]

        self.assertEqual(both, [], f"configs declaring both warning shapes fail to import: {both}")


class FiveYearBarProgramsTest(SimpleTestCase):
    def test_bar_subject_programs_declare_the_expected_statuses(self):
        for name, expected in BAR_SUBJECT_PROGRAMS.items():
            with self.subTest(program=name):
                config = load_program(name)
                self.assertEqual(set(config["program"]["legal_status_required"]), expected)

    def test_no_snap_program_claims_refugee(self):
        for name in SNAP_PROGRAMS_WITHOUT_REFUGEE:
            with self.subTest(program=name):
                self.assertNotIn("refugee", load_program(name)["program"]["legal_status_required"])

    def test_bare_gc_5less_is_not_claimed_by_a_bar_subject_program(self):
        """
        `gc_5less` on a bar-subject program claims every LPR under five years, which is the
        reported bug. The exempt subsets are expressed with the age and pregnancy labels instead.
        """
        for name in BAR_SUBJECT_PROGRAMS:
            with self.subTest(program=name):
                config = load_program(name)
                self.assertNotIn("gc_5less", config["program"]["legal_status_required"])


class WaFoodProgramsAreDisjointTest(SimpleTestCase):
    def test_wa_snap_and_wa_fap_share_no_status(self):
        """
        WaFap subclasses Snap and resolves the same PolicyEngine `snap` variable, so a household
        matching both programs has one benefit counted twice in its estimated total.
        """
        snap = set(load_program("wa_snap")["program"]["legal_status_required"])
        fap = set(load_program("wa_fap")["program"]["legal_status_required"])

        self.assertEqual(snap & fap, set())

    def test_neither_wa_food_program_serves_undocumented_immigrants(self):
        for name in ("wa_snap", "wa_fap"):
            with self.subTest(program=name):
                self.assertNotIn("non_citizen", load_program(name)["program"]["legal_status_required"])


class MigrationLabelsTest(SimpleTestCase):
    """
    The config guards above cannot see the programs that predate the config-import system and have
    no JSON file at all. Three of them need a change here — nc_snap, nc_medicaid and mo_snap — and
    for those the migrations are the only declaration, so the migrations are what to assert against.
    co_snap, il_snap and ma_snap are config-less too but are deliberately absent from the
    migrations: each already declares `citizen, gc_5plus, gc_under18_no5`, the state the other SNAP
    programs are being moved to, so there is nothing to correct.

    This also catches a typo before deploy: `LegalStatus.status` has no unique constraint, so a
    misspelled label would otherwise reach an environment as a lookup failure.
    """

    @staticmethod
    def _migration(number, name):
        path = Path(__file__).resolve().parents[3] / "migrations" / f"{number}_{name}.py"
        spec = importlib.util.spec_from_file_location(f"m{number}", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bar = cls._migration("0168", "fix_five_year_bar_legal_statuses")
        cls.mo_snap = cls._migration("0169", "drop_refugee_from_mo_snap")

    def test_every_label_named_in_a_migration_is_known(self):
        named = {self.mo_snap.STATUS}
        for _, to_add, to_remove in self.bar.CHANGES:
            named |= set(to_add) | set(to_remove)

        self.assertEqual(named - KNOWN_LABELS, set())

    def test_config_less_programs_are_covered_by_a_migration(self):
        """Without a config file, a program left out of the migrations gets no fix at all."""
        touched = {name for name, _, _ in self.bar.CHANGES}
        touched.add(self.mo_snap.PROGRAM)

        for name in ("nc_snap", "nc_medicaid", "mo_snap"):
            with self.subTest(program=name):
                self.assertIn(name, touched)

    def test_no_migration_adds_a_label_linked_to_undocumented_to_a_full_scope_program(self):
        """
        `otherHealthCarePregnant` and `otherHealthCareUnder19` are linked to `non_citizen` in
        citizenshipFilterConfig.tsx, so putting either on a full-scope Medicaid program makes it
        visible to undocumented households. On NC that also double-counts, since
        nc_emergency_medicaid gates on `program_eligible("nc_medicaid")` and neither program
        declares `excludes_programs`.
        """
        linked_to_undocumented = {"otherHealthCarePregnant", "otherHealthCareUnder19"}
        full_scope_medicaid = {"nc_medicaid", "wa_apple_health_medicaid", "il_medicaid"}

        for name, to_add, _ in self.bar.CHANGES:
            if name in full_scope_medicaid:
                with self.subTest(program=name):
                    self.assertEqual(set(to_add) & linked_to_undocumented, set())


class WarningMessagesAreReachableTest(SimpleTestCase):
    def test_a_warning_is_scoped_to_a_status_its_program_serves(self):
        """
        Warnings render only on ProgramPage, which is reachable only for programs that survive the
        legal-status filter. A warning scoped to a status the program does not declare can never
        be shown, so it is dead copy that reads like delivered mitigation.
        """
        unreachable = {}

        for path in config_files():
            config = json.loads(path.read_text())
            declared = set((config.get("program") or {}).get("legal_status_required") or [])
            if not declared:
                continue

            warnings = config.get("warning_messages") or []
            if "warning_message" in config:
                warnings = [*warnings, config["warning_message"]]

            for warning in warnings:
                scope = set(warning.get("legal_statuses") or [])
                # An unscoped warning shows to everyone, which is always reachable.
                if scope and not scope & declared:
                    unreachable[f"{path.name}:{warning.get('external_name')}"] = sorted(scope)

        self.assertEqual(unreachable, {}, f"warnings scoped to statuses their program never serves: {unreachable}")

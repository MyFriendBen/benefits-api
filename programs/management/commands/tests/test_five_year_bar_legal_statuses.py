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

# Programs pinned to the exact statuses each should declare — plus wa_fap, which the wa_snap edit
# has to stay disjoint from. Pinning the whole set is what stops a later config pass from quietly
# re-adding `gc_5less` to any of them.
#
# SNAP exempts LPRs under 18 from the bar regardless of the status they adjusted from, so
# `gc_under18_no5` replaces bare `gc_5less`. TANF has no age-based exemption, so `gc_5less` simply
# comes off. `refugee` is not a federal-SNAP status — eligibility runs to citizens, LPRs,
# Cuban/Haitian entrants and COFA citizens — which is why it sits on state-funded wa_fap and on no
# SNAP program. The bar's exemption for people who adjusted to LPR *from* refugee status is a
# different thing: they hold a green card now, and expressing it needs a filter we do not have.
EDITED_PROGRAMS = {
    "wa_snap": {"citizen", "gc_5plus", "gc_under18_no5"},
    "wa_fap": {"gc_18plus_no5", "otherWithWorkPermission", "refugee"},
    "ks_snap": {"citizen", "gc_5plus", "gc_under18_no5"},
    "tx_snap": {"citizen", "gc_5plus", "gc_under18_no5"},
    "mo_snap": {"citizen", "gc_5plus", "gc_under18_no5"},
    "wa_tanf": {"citizen", "gc_5plus", "refugee", "otherWithWorkPermission"},
    "mo_tanf": {"citizen", "gc_5plus", "refugee", "otherWithWorkPermission"},
    "ks_tanf": {"citizen", "non_citizen", "gc_5plus", "refugee", "otherWithWorkPermission"},
    "wa_apple_health_medicaid": {
        "citizen",
        "non_citizen",
        "gc_5plus",
        "refugee",
        "otherWithWorkPermission",
    },
    "tx_medicaid_for_pregnant_women": {"citizen", "gc_5plus", "refugee"},
    "il_mpe": {"citizen", "gc_5plus", "gc_5less", "refugee", "otherWithWorkPermission"},
    # Lifeline, every white label. DOJ's Office of Legal Counsel concluded PRWORA reaches Lifeline
    # as both a federal public benefit and a federal means-tested public benefit, so `non_citizen`
    # comes off under the first finding and `gc_5less` under the second. `otherWithWorkPermission`
    # stays: the bucket mixes qualified aliens subject only to the five-year clock with lawfully
    # present statuses that never clear the qualified-alien gate at all, so removing it would
    # over-exclude. A scoped warning banner carries that distinction instead.
    "co_lifeline": {"citizen", "gc_5plus", "refugee", "otherWithWorkPermission"},
    "il_lifeline": {"citizen", "gc_5plus", "refugee", "otherWithWorkPermission"},
    "ks_lifeline": {"citizen", "gc_5plus", "refugee", "otherWithWorkPermission"},
    "ma_lifeline": {"citizen", "gc_5plus", "refugee", "otherWithWorkPermission"},
    "mo_lifeline": {"citizen", "gc_5plus", "refugee", "otherWithWorkPermission"},
    "nc_lifeline": {"citizen", "gc_5plus", "refugee", "otherWithWorkPermission"},
    "tx_lifeline": {"citizen", "gc_5plus", "refugee", "otherWithWorkPermission"},
    "wa_lifeline": {"citizen", "gc_5plus", "refugee", "otherWithWorkPermission"},
}

# The subset this change narrows for the bar, where bare `gc_5less` is the reported bug.
#
# il_mpe and tx_medicaid_for_pregnant_women are out of this set on purpose: neither is narrowed
# here. Their config edits dropped `other` and `gc_under5`, labels with no LegalStatus row, so
# whether presumptive-eligibility and pregnancy coverage reach LPRs inside the window was never in
# scope. EDITED_PROGRAMS still pins both, so a change to either has to be deliberate.
BAR_SUBJECT_PROGRAMS = (
    "wa_snap",
    "ks_snap",
    "tx_snap",
    "mo_snap",
    "wa_tanf",
    "mo_tanf",
    "ks_tanf",
    "wa_apple_health_medicaid",
    # Lifeline is means-tested under PRWORA §403, so the bar applies. The age-split labels are not
    # an exempt subset here the way they are for SNAP — they are `gc_5less` proxies via
    # `linkedFilters`, so leaving either on would re-admit the population `gc_5less` removal
    # excludes. None of the eight declares them.
    "co_lifeline",
    "il_lifeline",
    "ks_lifeline",
    "ma_lifeline",
    "mo_lifeline",
    "nc_lifeline",
    "tx_lifeline",
    "wa_lifeline",
)

# Federal SNAP does not reach refugee or asylee status. Washington serves that group through
# state-funded FAP instead, which is itself evidence federal SNAP does not: a state would not fund
# a program for a population federal SNAP already covered.
SNAP_PROGRAMS_WITHOUT_REFUGEE = ("wa_snap", "ks_snap", "tx_snap", "mo_snap")


def config_files():
    return sorted(DATA_DIR.glob("*_initial_config.json"))


def find_program(name):
    """Return the config declaring `name_abbreviated == name`, or None if no config declares it."""
    for path in config_files():
        config = json.loads(path.read_text())
        if (config.get("program") or {}).get("name_abbreviated") == name:
            return config
    return None


def load_program(name):
    """Return the config declaring `name_abbreviated == name`, failing if there is none."""
    config = find_program(name)
    if config is None:
        raise AssertionError(f"no config declares program '{name}'")
    return config


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
    def test_edited_programs_declare_the_expected_statuses(self):
        for name, expected in EDITED_PROGRAMS.items():
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

    def test_every_bar_subject_program_is_pinned(self):
        """A program narrowed for the bar but left out of EDITED_PROGRAMS has no exact-set guard."""
        self.assertEqual(set(BAR_SUBJECT_PROGRAMS) - set(EDITED_PROGRAMS), set())


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
    no JSON file at all. Two of them need a change here — nc_snap and nc_medicaid — and for those
    the migrations are the only declaration, so the migrations are what to assert against. co_snap,
    il_snap and ma_snap are config-less too but are deliberately absent from the migrations: each
    already declares `citizen, gc_5plus, gc_under18_no5`, the state the other SNAP programs are
    being moved to, so there is nothing to correct.

    mo_snap does have a config, and 0169 still has to carry the `refugee` removal: the importer
    applies `legal_status_required` with `.add()` and skips programs that already exist, so editing
    the config cannot narrow a live program. That split is why the two declarations can drift,
    which the agreement tests below are for.

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
        named = {self.mo_snap.STATUS} | set(self.bar.SEEDABLE)
        for _, to_add, to_remove in self.bar.CHANGES:
            named |= set(to_add) | set(to_remove)

        self.assertEqual(named - KNOWN_LABELS, set())

    def test_every_label_a_migration_adds_may_be_seeded(self):
        """
        0129 seeded only the six user-selected statuses, and the config importer resolves labels
        with `.get()` and merely warns on a miss, so no migration has ever created a calculated
        label. An addition outside `SEEDABLE` falls through to a bare `.get()`, which raises inside
        `RunPython` on any environment built from migrations alone — failing the deploy's `migrate`
        step and rolling back every pending migration, not just this one.
        """
        added = {status for _, to_add, _ in self.bar.CHANGES for status in to_add}

        self.assertEqual(added - set(self.bar.SEEDABLE) - USER_SELECTED, set())

    def test_programs_needing_a_narrowing_are_covered_by_a_migration(self):
        """
        The importer cannot narrow a live program, so a program left out of the migrations gets no
        fix at all — and for the config-less ones there is nowhere else the change could land.
        """
        touched = {name for name, _, _ in self.bar.CHANGES}
        touched.add(self.mo_snap.PROGRAM)

        for name in ("nc_snap", "nc_medicaid", "mo_snap"):
            with self.subTest(program=name):
                self.assertIn(name, touched)

    def test_no_config_declares_a_status_a_migration_removes(self):
        """
        The importer applies `legal_status_required` with `.add()`, so a config still declaring a
        status a migration removed re-adds it — on the next `--override` import, on any fresh
        environment, and on every new white label seeded from that config — silently undoing the
        migration and leaving the JSON as the wrong source of truth.
        """
        removed = {name: set(to_remove) for name, _, to_remove in self.bar.CHANGES}
        removed.setdefault(self.mo_snap.PROGRAM, set()).add(self.mo_snap.STATUS)

        contradictions = {}
        for name, statuses in removed.items():
            config = find_program(name)
            if config is None:
                continue  # config-less: the migration is the only declaration

            still_declared = set(config["program"]["legal_status_required"]) & statuses
            if still_declared:
                contradictions[name] = sorted(still_declared)

        self.assertEqual(contradictions, {}, f"configs contradict a migration: {contradictions}")

    def test_every_config_declares_the_statuses_its_migration_adds(self):
        """
        The mirror of the above: a config missing a status its migration adds narrows nothing on its
        own, but it leaves the JSON disagreeing with the database and the next reader unable to tell
        which one is right.
        """
        missing = {}
        for name, to_add, _ in self.bar.CHANGES:
            config = find_program(name)
            if config is None:
                continue

            absent = set(to_add) - set(config["program"]["legal_status_required"])
            if absent:
                missing[name] = sorted(absent)

        self.assertEqual(missing, {}, f"configs missing a status their migration adds: {missing}")

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

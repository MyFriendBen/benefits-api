"""
check_pe_support — does PolicyEngine expose data for a program we're considering?

This is a *discovery* command, not a check against calculators already defined in our
system. Given a program concept (e.g. "Colorado childcare credit", "WIC", "liheap"),
it searches PolicyEngine's variable catalog to tell us whether PE has a variable we
could pull from — i.e. whether building a new PE calculator on our end is even an
option — and, when it is, what the calculator config would look like.

PolicyEngine has no per-variable endpoint, so the source of truth is the full
metadata blob (~66 MB). We download it once and cache it on disk; subsequent runs
reuse the cache until it goes stale.

    https://api.policyengine.org/us/metadata  ->  result.variables{ <name>: {...} }

Usage
-----
    # Fuzzy search by concept — every term must appear in the variable name or label.
    python manage.py check_pe_support childcare colorado
    python manage.py check_pe_support liheap

    # Exact variable-name lookup (when you already know the pe_name).
    python manage.py check_pe_support --exact co_tanf

    # Narrow the search.
    python manage.py check_pe_support credit --state co      # module under gov.states.co.*
    python manage.py check_pe_support snap --computed-only    # hide raw input variables
    python manage.py check_pe_support credit --state co --entity tax_unit

    # Cache control.
    python manage.py check_pe_support --refresh wic           # force a fresh download

For each match it prints: support verdict, the entity (mapped to the calculator base
class you'd subclass in policyengine/calculators/base.py), the definition period,
whether it's a computed output vs. an input you'd have to supply, and the PE module
(jurisdiction sanity-check).
"""

import json
import os
import tempfile
import time
import urllib.request

from django.core.management.base import BaseCommand, CommandError

METADATA_URL = "https://api.policyengine.org/us/metadata"
CACHE_PATH = os.path.join(tempfile.gettempdir(), "pe_metadata_us.json")
CACHE_TTL_SECONDS = 60 * 60 * 24  # 24h — PE ships updates, but not within a work session.

# PolicyEngine entity -> the calculator base class you'd subclass in base.py.
ENTITY_TO_BASE_CLASS = {
    "spm_unit": "PolicyEngineSpmCalulator",
    "tax_unit": "PolicyEngineTaxUnitCalulator",
    "person": "PolicyEngineMembersCalculator",
    "household": "PolicyEngineCalulator (household-level; no dedicated subclass)",
    "family": "PolicyEngineCalulator (family-level; no dedicated subclass)",
    "marital_unit": "PolicyEngineCalulator (marital-unit-level; no dedicated subclass)",
}


class Command(BaseCommand):
    help = "Discover whether PolicyEngine exposes a variable for a program we're considering building."

    def add_arguments(self, parser):
        parser.add_argument("terms", nargs="*", help="Search terms (all must match the variable name or label).")
        parser.add_argument("--exact", metavar="NAME", help="Exact variable-name lookup (a known pe_name).")
        parser.add_argument("--state", metavar="XX", help="Filter to a state module, e.g. co, ma, tx.")
        parser.add_argument(
            "--entity", choices=sorted(ENTITY_TO_BASE_CLASS), help="Filter by PolicyEngine entity."
        )
        parser.add_argument(
            "--computed-only",
            action="store_true",
            help="Hide raw input variables; show benefit outputs only.",
        )
        parser.add_argument("--limit", type=int, default=40, help="Max results to print (default 40).")
        parser.add_argument("--refresh", action="store_true", help="Force a fresh metadata download.")

    def handle(self, *args, **options):
        terms = options["terms"]
        exact = options["exact"]
        if not terms and not exact:
            raise CommandError("provide search terms or --exact NAME")

        variables = self._load_metadata(refresh=options["refresh"])
        self.stderr.write(f"PolicyEngine catalog: {len(variables)} variables")

        if exact:
            self._handle_exact(variables, exact)
            return

        self._handle_search(
            variables,
            terms=terms,
            state=options["state"],
            entity=options["entity"],
            computed_only=options["computed_only"],
            limit=options["limit"],
        )

    # --- data ---------------------------------------------------------------

    def _load_metadata(self, refresh=False):
        """Return PE's variables map, downloading + caching the metadata blob as needed."""
        fresh = (
            not refresh
            and os.path.exists(CACHE_PATH)
            and (time.time() - os.path.getmtime(CACHE_PATH)) < CACHE_TTL_SECONDS
        )
        if fresh:
            age_min = int((time.time() - os.path.getmtime(CACHE_PATH)) / 60)
            self.stderr.write(f"Using cached metadata ({age_min} min old) at {CACHE_PATH}")
        else:
            self.stderr.write(f"Downloading PolicyEngine metadata (~66 MB) from {METADATA_URL} ...")
            try:
                with urllib.request.urlopen(METADATA_URL, timeout=120) as resp:
                    raw = resp.read()
            except Exception as e:  # noqa: BLE001 - surface any network/HTTP failure plainly
                raise CommandError(f"Failed to download metadata: {e}")
            # Write atomically so an interrupted download can't poison the cache.
            tmp = CACHE_PATH + ".part"
            with open(tmp, "wb") as f:
                f.write(raw)
            os.replace(tmp, CACHE_PATH)
            self.stderr.write(f"Cached to {CACHE_PATH}")

        with open(CACHE_PATH, "rb") as f:
            data = json.load(f)
        variables = data.get("result", {}).get("variables")
        if not variables:
            raise CommandError(
                "Metadata had no 'result.variables' — cache may be corrupt; rerun with --refresh."
            )
        return variables

    # --- handlers -----------------------------------------------------------

    def _handle_exact(self, variables, name):
        entry = variables.get(name)
        if entry is None:
            raise CommandError(
                f"{name!r}: NOT in PolicyEngine — no data available; a PE calculator is not an option."
            )
        self.stdout.write(self.style.SUCCESS(f"PolicyEngine supports {name!r}:\n"))
        self.stdout.write(self._describe(name, entry))

    def _handle_search(self, variables, terms, state, entity, computed_only, limit):
        matches = self._search(variables, terms, state, entity, computed_only)
        query = " ".join(terms)
        if not matches:
            self.stdout.write(self.style.WARNING(f"No PolicyEngine variables match: {query!r}"))
            self.stdout.write(
                "   PE may still cover it under different wording — try a broader/single term,\n"
                "   or drop --state/--computed-only. If nothing turns up, PE has no data for it."
            )
            return

        shown = matches[:limit]
        more = len(matches) - len(shown)
        suffix = f" (showing {len(shown)})" if more else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"Found {len(matches)} PolicyEngine variable(s) matching {query!r}{suffix}:\n"
            )
        )
        for name, entry in shown:
            self.stdout.write(self._describe(name, entry))
            self.stdout.write("")
        if more:
            self.stdout.write(
                f"... {more} more. Narrow with --state / --entity / --computed-only or more terms."
            )

    # --- helpers ------------------------------------------------------------

    @staticmethod
    def _search(variables, terms, state, entity, computed_only):
        terms = [t.lower() for t in terms]
        state = state.lower() if state else None
        results = []
        for name, entry in variables.items():
            if not isinstance(entry, dict):
                continue
            haystack = f"{name} {entry.get('label') or ''}".lower()
            if not all(t in haystack for t in terms):
                continue
            if state and f"gov.states.{state}." not in (entry.get("moduleName") or "").lower():
                continue
            if entity and entry.get("entity") != entity:
                continue
            if computed_only and entry.get("isInputVariable", False):
                continue
            results.append((name, entry))
        # Exact name match first, then alphabetical.
        results.sort(key=lambda kv: (not any(kv[0].lower() == t for t in terms), kv[0]))
        return results

    @staticmethod
    def _describe(name, entry):
        """One-line, copy-into-a-PR description of a supported variable."""
        entity = entry.get("entity", "?")
        base = ENTITY_TO_BASE_CLASS.get(entity, f"(unmapped entity: {entity})")
        computed = not entry.get("isInputVariable", False)
        kind = "computed output" if computed else "INPUT (must be supplied, not a benefit value)"
        label = entry.get("label") or "(no label)"
        period = entry.get("definitionPeriod", "?")
        unit = entry.get("unit") or "?"
        module = entry.get("moduleName") or "?"
        return (
            f"  {name}  —  {label}\n"
            f"       entity={entity}  ->  subclass {base}\n"
            f"       period={period}   unit={unit}   {kind}\n"
            f"       module={module}"
        )

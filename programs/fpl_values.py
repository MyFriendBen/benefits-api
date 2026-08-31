"""Materialize the FPL table into the database so SQL-only consumers can read it.

The thresholds themselves live in `_FPL_DEFAULTS`, a module constant in
programs.models, and `FederalPoveryLimit` stores only a year and a period that
point into it. That is fine for the calculators, which go through
`FederalPoveryLimit.get_limit()` in Python, but it leaves anything that can only
read the database with no way to compute a percent-of-FPL figure -- the analytics
pipeline (dbt over Postgres, feeding Metabase) among them.

This module writes `get_limit()`'s output to `FederalPovertyLimitValue`, one row
per (period, household size). It is deliberately a mirror, not a new source of
truth: the constant stays authoritative, the calculators keep reading it, and a
test asserts the two agree so they cannot drift silently.

Sizes above `MAX_DEFINED_SIZE` are extrapolated exactly as `get_limit()` does,
up to `MAX_MATERIALIZED_SIZE`, so a consumer joining on household size never has
to reimplement the per-additional-person arithmetic.
"""

from typing import Optional, Type

# Imported lazily inside the functions so a data migration can hand in its own
# historical model class via apps.get_model().
MAX_MATERIALIZED_SIZE = 20


def limits_for_period(table: dict, max_size: int = MAX_MATERIALIZED_SIZE) -> dict[int, int]:
    """Expand one year's FPL table to a flat {household_size: annual_limit} map.

    Mirrors FederalPoveryLimit.get_limit(): sizes past the last defined one add
    the per-additional-person amount once per extra member.
    """
    defined = sorted(size for size in table if isinstance(size, int))
    largest_defined = defined[-1]

    limits = {size: table[size] for size in defined}
    for size in range(largest_defined + 1, max_size + 1):
        limits[size] = table[largest_defined] + table["additional"] * (size - largest_defined)

    return limits


def sync_fpl_values(
    value_model: Optional[Type] = None,
    fpl_table: Optional[dict] = None,
    max_size: int = MAX_MATERIALIZED_SIZE,
) -> dict[str, int]:
    """Upsert one row per (period, household size). Idempotent.

    Returns a {created, updated, deleted} count so the management command and the
    migration can report what they did.

    `value_model` and `fpl_table` are injectable so a data migration can pass the
    historical model from apps.get_model() rather than importing the live one.
    """
    if value_model is None:
        from programs.models import FederalPovertyLimitValue

        value_model = FederalPovertyLimitValue

    if fpl_table is None:
        from programs.models import _get_fpl_data

        fpl_table = _get_fpl_data()

    wanted: dict[tuple[str, int], int] = {}
    for period, table in fpl_table.items():
        for household_size, annual_limit in limits_for_period(table, max_size).items():
            wanted[(period, household_size)] = annual_limit

    existing = {(row.period, row.household_size): row for row in value_model.objects.all()}

    created = 0
    updated = 0

    for (period, household_size), annual_limit in wanted.items():
        row = existing.get((period, household_size))
        if row is None:
            value_model.objects.create(
                period=period,
                household_size=household_size,
                annual_limit=annual_limit,
            )
            created += 1
        elif row.annual_limit != annual_limit:
            row.annual_limit = annual_limit
            row.save(update_fields=["annual_limit"])
            updated += 1

    # Drop rows for periods or sizes the constant no longer defines, so a removed
    # year cannot linger and be joined against.
    stale = [row.pk for key, row in existing.items() if key not in wanted]
    deleted = len(stale)
    if stale:
        value_model.objects.filter(pk__in=stale).delete()

    return {"created": created, "updated": updated, "deleted": deleted}

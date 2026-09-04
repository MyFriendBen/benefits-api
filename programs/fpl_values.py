"""Sync the FederalPovertyLimitValue mirror from the _FPL_DEFAULTS constant.

See the FederalPovertyLimitValue docstring in programs/models.py for why the
mirror exists and what it guarantees to consumers.
"""

from typing import Optional, Type

# Largest household size given a row. Consumers must clamp to this; see the
# CONTRACT WITH CONSUMERS note on the model.
MAX_MATERIALIZED_SIZE = 20


def limits_for_period(table: dict, max_size: int = MAX_MATERIALIZED_SIZE) -> dict[int, int]:
    """Expand one year's FPL table to a flat {household_size: annual_limit} map.

    Mirrors FederalPoveryLimit.get_limit(): sizes past the last defined one add
    the per-additional-person amount once per extra member.
    """
    defined = sorted(size for size in table if isinstance(size, int))
    if not defined:
        raise ValueError("FPL table defines no household sizes; cannot expand it.")
    largest_defined = defined[-1]

    limits = {size: table[size] for size in defined}
    for size in range(largest_defined + 1, max_size + 1):
        limits[size] = table[largest_defined] + table["additional"] * (size - largest_defined)

    return limits


def sync_fpl_values(
    value_model: Optional[Type] = None,
    fpl_table: Optional[dict] = None,
    max_size: int = MAX_MATERIALIZED_SIZE,
    dry_run: bool = False,
) -> dict[str, int]:
    """Upsert one row per (period, household size). Idempotent.

    Returns a {created, updated, deleted} count so the management command and the
    migration can report what they did.

    `dry_run` returns the same counts without writing. The diff is computed once
    either way -- a separate preview implementation would drift from the real one
    and start lying about what a sync would do.

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
            created += 1
            if not dry_run:
                value_model.objects.create(
                    period=period,
                    household_size=household_size,
                    annual_limit=annual_limit,
                )
        elif row.annual_limit != annual_limit:
            updated += 1
            if not dry_run:
                row.annual_limit = annual_limit
                row.save(update_fields=["annual_limit"])

    # Drop rows for periods or sizes the constant no longer defines, so a removed
    # year cannot linger and be joined against.
    stale = [row.pk for key, row in existing.items() if key not in wanted]
    deleted = len(stale)
    if stale and not dry_run:
        value_model.objects.filter(pk__in=stale).delete()

    return {"created": created, "updated": updated, "deleted": deleted}

from django.core.management.base import BaseCommand
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from programs.models import County
from screener.models import WhiteLabel, Screen
from configuration.white_labels import white_label_config

# White labels whose canonical county convention is the suffixed form ("X County"),
# i.e. their ZIP->county map emits qualified names. il/ma/tx are bare/city by convention
# and are intentionally NOT eligible for this canonicalization.
DEFAULT_WHITE_LABELS = ["wa", "co", "ks", "mo"]

SUFFIX = " County"


def suffixed_county_names(code):
    """Set of real suffixed county names from a white label's ZIP->county map.

    Used as a guard so we only append " County" to a bare row when a genuine
    "X County" exists — protecting independent cities (e.g. MO "St. Louis City").
    Returns None if the white label config is unavailable (guard is then skipped).
    """
    data = white_label_config.get(code)
    if data is None:
        return None
    names = set()
    for county_map in data.counties_by_zipcode.values():
        names.update(county_map.keys())
    return names


# County m2m reverse accessors on the County model.
RELATED_ACCESSORS = ("urgent_need", "navigator", "warning_messages", "translation_overrides")


class Command(BaseCommand):
    help = (
        "Canonicalize bare county names (e.g. 'Snohomish') to the suffixed form "
        "('Snohomish County') for suffixed-convention white labels. Merges a bare row "
        "into its existing suffixed twin (re-pointing links) or renames it if no twin exists. "
        "Optionally migrates historical Screen.county values (white-label-scoped)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "white_labels",
            nargs="*",
            default=DEFAULT_WHITE_LABELS,
            help=f"White label codes to process (default: {' '.join(DEFAULT_WHITE_LABELS)})",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing anything.",
        )
        parser.add_argument(
            "--include-screens",
            action="store_true",
            help="Also migrate historical Screen.county bare values to the suffixed form (scoped to the given white labels).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        white_labels = options["white_labels"]
        dry_run = options["dry_run"]
        include_screens = options["include_screens"]

        mode = "DRY-RUN (no writes)" if dry_run else "APPLYING CHANGES"
        self.stdout.write(self.style.MIGRATE_HEADING(f"canonicalize_county_names — {mode}"))
        self.stdout.write(f"White labels: {', '.join(white_labels)}")
        self.stdout.write(f"Include screens: {include_screens}\n")

        total_merged = 0
        total_renamed = 0
        total_skipped = 0
        total_screens = 0

        for code in white_labels:
            try:
                wl = WhiteLabel.objects.get(code=code)
            except ObjectDoesNotExist:
                self.stdout.write(self.style.WARNING(f"  [{code}] white label not in database — skipping"))
                continue

            valid_suffixed = suffixed_county_names(code)  # None => guard unavailable
            bare_rows = list(County.objects.filter(white_label=wl).exclude(name__endswith=SUFFIX).order_by("name"))

            self.stdout.write(self.style.MIGRATE_LABEL(f"  [{code}] {len(bare_rows)} bare county row(s)"))

            for c in bare_rows:
                target_name = c.name + SUFFIX
                twin = County.objects.filter(white_label=wl, name=target_name).first()

                if twin:
                    link_count = sum(getattr(c, acc).count() for acc in RELATED_ACCESSORS)
                    self.stdout.write(
                        f"    MERGE  {c.name!r} (id={c.id}, {link_count} link(s)) -> {target_name!r} (id={twin.id})"
                    )
                    if not dry_run:
                        for acc in RELATED_ACCESSORS:
                            for obj in getattr(c, acc).all():
                                obj.counties.add(twin)  # idempotent; leaves twin linked
                        c.delete()  # cascade removes the bare row's through-table entries
                    total_merged += 1
                elif valid_suffixed is not None and target_name not in valid_suffixed:
                    # No real "X County" in the ZIP map — likely an independent city
                    # (e.g. MO "St. Louis City"). Leave it alone.
                    self.stdout.write(
                        self.style.WARNING(f"    SKIP   {c.name!r} (id={c.id}) — no {target_name!r} in ZIP map")
                    )
                    total_skipped += 1
                else:
                    self.stdout.write(f"    RENAME {c.name!r} (id={c.id}) -> {target_name!r}")
                    if not dry_run:
                        c.name = target_name
                        c.save(update_fields=["name"])
                    total_renamed += 1

            if include_screens:
                # Canonicalize every historical bare Screen.county whose "X County" is a
                # real county in this white label's ZIP map. Independent cities and
                # out-of-state values (e.g. MO "St. Louis City", a WA "Multnomah") have no
                # such counterpart and are left untouched. Idempotent and white-label-scoped.
                bare_screen_counties = (
                    Screen.objects.filter(white_label=wl)
                    .exclude(county__isnull=True)
                    .exclude(county="")
                    .exclude(county__endswith=SUFFIX)
                    .values_list("county", flat=True)
                    .distinct()
                )
                for name in bare_screen_counties:
                    target = name + SUFFIX
                    if valid_suffixed is None or target not in valid_suffixed:
                        continue
                    qs = Screen.objects.filter(white_label=wl, county=name)
                    n = qs.count()
                    if n:
                        self.stdout.write(f"    SCREENS {n} row(s): county {name!r} -> {target!r}")
                        if not dry_run:
                            qs.update(county=target)
                        total_screens += n

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Summary: merged={total_merged} renamed={total_renamed} skipped={total_skipped} screens_updated={total_screens}"
            )
        )

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — rolling back (no changes committed)."))
            transaction.set_rollback(True)

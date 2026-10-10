"""Report programs whose configured FPL edition disagrees with the recorded intent.

A unit test can check the vintage map against the config JSONs, but it cannot see a live
database -- and the database is where most of this lives: 72 of the 112 rows found behind
an edition have no config JSON at all. This is the part that can only run against a real
environment.

Modelled on `sync_fpl_values`: `--check` exits non-zero so it can be wired up as a drift
alarm rather than something somebody has to remember to read.
"""

import inspect
from datetime import date

from django.core.management.base import BaseCommand

from programs.models import Program, _get_fpl_data
from programs.vintage import PROGRAM_VINTAGE, Status

#: Severity order, worst first. A null year on a PolicyEngine program is not a lesser form
#: of staleness: `pe_base.pe_period` raises a bare Exception, `can_calc()` does not filter
#: the program out, and the raise escapes both handlers in `calc_pe_eligibility` to reach an
#: unguarded `screener/views.py`. One such program takes down eligibility for every program
#: on the screen, so it is reported apart from, and above, a row that is merely behind.
NO_YEAR_PE = "no year set, PolicyEngine program (500s the whole eligibility response)"
NO_YEAR_CUSTOM = "no year set, custom calculator reads it"
DISAGREES = "disagrees with the recorded intent"
STALE_FPL = "FPL table has no current-year guideline"
UNVERIFIED = "recorded as production has it, not verified"
NO_INTENT = "no recorded intent"

SEVERITIES = (NO_YEAR_PE, NO_YEAR_CUSTOM, DISAGREES, STALE_FPL, UNVERIFIED, NO_INTENT)

#: Printed as warnings. UNVERIFIED also never fails `--check`: it is a known open question,
#: and failing on it would block every deploy until the question is answered.
WARNINGS = (UNVERIFIED, NO_INTENT)
ADVISORY = (UNVERIFIED,)

#: HHS publishes the new guidelines in mid-to-late January. Until this (month, day) a table
#: that has not caught up is expected and only warned about; from it on, it is a finding.
FPL_GRACE_ENDS = (3, 1)


def _period_matters() -> tuple[dict[str, type], set[str]]:
    """Which calculators care about the configured period, and how.

    Imported lazily: the PolicyEngine registry pulls in every calculator module, which
    reaches back into `programs.models`.
    """
    from integrations.clients.policyengine.registry import all_calculators as pe_calculators
    from programs.programs import calculators as custom_calculators

    reads_year = set()
    for abbr, calculator in custom_calculators.items():
        for klass in calculator.__mro__:
            try:
                source = inspect.getsource(klass)
            except (OSError, TypeError):
                continue
            if "program.year" in source:
                reads_year.add(abbr)
                break

    return pe_calculators, reads_year


class Command(BaseCommand):
    help = (
        "Report active programs whose FPL edition disagrees with programs/vintage.py, have "
        "no year set, or have no recorded intent. --check exits 1 if anything is reported, "
        "so it can run as a deploy-time drift alarm."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--check",
            action="store_true",
            help="Exit 1 if anything is reported, instead of only printing.",
        )
        parser.add_argument(
            "--ignore-unmapped",
            action="store_true",
            help=(
                "Skip programs with no vintage.py entry. Useful while the map is still "
                "being filled in, since an unresearched program is a gap rather than a "
                "regression."
            ),
        )

    def handle(self, *args, **options):
        pe_calculators, reads_year = _period_matters()
        findings: dict[str, list[str]] = {severity: [] for severity in SEVERITIES}

        programs = Program.objects.filter(active=True).select_related("year", "white_label")

        for program in programs:
            abbr = program.name_abbreviated
            is_pe = abbr in pe_calculators
            if not is_pe and abbr not in reads_year:
                # The period has no effect on this program, so it has nothing to drift.
                continue

            key = (program.white_label.code, abbr)
            label = f"{program.white_label.code}/{abbr}"
            period = program.year.period if program.year else None

            if period is None:
                bucket = NO_YEAR_PE if is_pe else NO_YEAR_CUSTOM
                # A null year can be the recorded state rather than a gap: ks_k40h is
                # pinned to one booklet year in four places, and the unset row lands it
                # there consistently. Still reported -- a null is fragile however it got
                # there -- but with the reason attached so it reads as known, not as
                # something nobody has looked at.
                intent = PROGRAM_VINTAGE.get(key)
                if intent is not None:
                    findings[bucket].append(f"{label} — recorded: {intent.rule}")
                else:
                    findings[bucket].append(label)
                continue

            intent = PROGRAM_VINTAGE.get(key)
            if intent is None:
                if not options["ignore_unmapped"]:
                    findings[NO_INTENT].append(f"{label} (on {period})")
                continue

            if intent.edition != period:
                findings[DISAGREES].append(
                    f"{label}: on {period}, recorded as {intent.edition} " f"({intent.status.value}) — {intent.rule}"
                )
            elif intent.status is Status.UNVERIFIED:
                # Matching production proves nothing when the entry was copied from it.
                findings[UNVERIFIED].append(f"{label} (on {period})")

        self._check_fpl_table(findings)

        return self._report(findings, options["check"])

    def _check_fpl_table(self, findings):
        """Whether `_FPL_DEFAULTS` has the current year's guideline.

        Without it no program can be moved to the current edition, and the map silently caps
        out a year behind -- the original defect. This is a fact about today, so it lives
        here rather than in a unit test that would fail every build until HHS publishes.
        """
        today = date.today()
        latest = max(_get_fpl_data(), key=int)
        if int(latest) >= today.year:
            return

        message = (
            f"_FPL_DEFAULTS stops at {latest}; add the {today.year} HHS guideline "
            "(programs/models.py) before anything can move to the current edition"
        )
        if (today.month, today.day) >= FPL_GRACE_ENDS:
            findings[STALE_FPL].append(message)
        else:
            self.stdout.write(self.style.WARNING(f"{message} (expected until HHS publishes)."))

    def _report(self, findings, check):
        total = sum(len(rows) for rows in findings.values())

        if not total:
            self.stdout.write(self.style.SUCCESS("Every program's edition matches its recorded intent."))
            return

        for severity in SEVERITIES:
            rows = findings[severity]
            if not rows:
                continue
            style = self.style.WARNING if severity in WARNINGS else self.style.ERROR
            self.stdout.write(style(f"\n{severity} ({len(rows)}):"))
            for row in sorted(rows):
                self.stdout.write(f"  {row}")

        summary = ", ".join(f"{len(findings[s])} {s.split(',')[0]}" for s in SEVERITIES if findings[s])
        self.stdout.write("")

        if check and any(findings[s] for s in SEVERITIES if s not in ADVISORY):
            # Non-zero so a deploy step or a cron can act on it. A wrong edition is a wrong
            # benefit estimate with nothing else to catch it -- no test sees a live database,
            # and the failure is silent in the direction that matters: a household is shown
            # less than it qualifies for, or nothing at all, and never finds out.
            self.stderr.write(self.style.ERROR(f"Program vintages need attention: {summary}."))
            raise SystemExit(1)

        self.stdout.write(self.style.WARNING(f"Program vintages need attention: {summary}."))

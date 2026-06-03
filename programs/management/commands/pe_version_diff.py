"""
MFB-1103 regression-diff harness for the PolicyEngine frontier migration.

Runs representative in-memory test households through the PolicyEngine eligibility
calc at two model versions (default/current vs a pinned version, default 1.715.2)
and reports every program whose eligibility or value changed. Surfaces both the
*expected* frontier shifts and any *unexpected* ones.

Both sides are real PolicyEngine API responses, so this needs network + PE creds.
Test screens are created in a transaction and rolled back — nothing persists.

Usage:
    python manage.py pe_version_diff
    python manage.py pe_version_diff --version 1.715.2
    python manage.py pe_version_diff --scenario disabled_ssi_co
"""

import json

from django.core.management.base import BaseCommand
from django.db import transaction

from programs.models import Program
from programs.programs.policyengine.calculators.registry import all_calculators
from programs.programs.policyengine.policy_engine import calc_pe_eligibility
from screener.models import Screen, HouseholdMember, Expense, IncomeStream, WhiteLabel
from screener.serializers import ScreenSerializer


def _calculators_for(screen):
    """Mirror eligibility_results(): build the active PE calculators for a screen."""
    programs = Program.objects.filter(active=True, white_label=screen.white_label)
    missing = screen.missing_fields()
    calcs = {}
    for name, Calc in all_calculators.items():
        program = next((p for p in programs if p.name_abbreviated == name), None)
        if program is not None:
            calcs[name] = Calc(screen, program, missing)
    return calcs


def _run(screen, version):
    """Return {program_abbr: (eligible, value)} for a screen at a given PE version."""
    result = calc_pe_eligibility(screen, _calculators_for(screen), pe_version=version)
    return {abbr: (e.eligible, round(e.value, 2)) for abbr, e in result["eligibility"].items()}


# --- Scenario builders -------------------------------------------------------
# Each returns a freshly-created Screen (inside the caller's rolled-back txn).
# Keyed by name so a single scenario can be run with --scenario.


def _screen(wl_code, **kw):
    wl = WhiteLabel.objects.filter(code=wl_code).first()
    if wl is None:
        return None
    defaults = dict(completed=False, is_test=True, agree_to_tos=True, household_assets=0)
    defaults.update(kw)
    return Screen.objects.create(white_label=wl, **defaults)


def disabled_ssi_co():
    s = _screen("co", zipcode="80202", county="Denver County", household_size=1)
    if s:
        HouseholdMember.objects.create(
            screen=s, relationship="headOfHousehold", age=45, disabled=True, has_income=False
        )
    return s


def asset_near_limit_snap_co():
    # Assets just over the standard SNAP resource limit ($2,750 in 2024 for non-elderly/
    # disabled). The stock-period fix changed how assets compare in categorical
    # eligibility — sit right at the boundary so a flip would show.
    s = _screen("co", zipcode="80202", county="Denver County", household_size=2, household_assets=2800)
    if s:
        HouseholdMember.objects.create(screen=s, relationship="headOfHousehold", age=40, has_income=False)
        HouseholdMember.objects.create(screen=s, relationship="child", age=8)
    return s


def snap_abawd_mix_co():
    # Two genuinely ABAWD adults (18-52, no children, able-bodied), BOTH non-compliant
    # (zero work hours). Pre-frontier the whole unit zeroes out; per-person ABAWD should
    # now produce partial SNAP. No child, so neither adult is exempt as a caretaker.
    s = _screen("co", zipcode="80202", county="Denver County", household_size=2, household_assets=0)
    if s:
        HouseholdMember.objects.create(screen=s, relationship="headOfHousehold", age=30, has_income=False)
        HouseholdMember.objects.create(screen=s, relationship="other", age=28, has_income=False)
    return s


def snap_abawd_partial_co():
    # One compliant ABAWD adult (working 30 hrs/wk) + one non-compliant (0 hrs), no kids.
    # Pre-frontier: whole unit excluded -> $0. Frontier: non-compliant excluded per-person,
    # compliant adult still counted -> partial SNAP. This is the headline ABAWD improvement.
    s = _screen("co", zipcode="80202", county="Denver County", household_size=2, household_assets=0)
    if s:
        a = HouseholdMember.objects.create(screen=s, relationship="headOfHousehold", age=35, has_income=True)
        IncomeStream.objects.create(
            screen=s, household_member=a, type="wages", amount=15, frequency="hourly", hours_worked=30
        )
        HouseholdMember.objects.create(screen=s, relationship="other", age=40, has_income=False)
    return s


def tx_ccs_childcare():
    s = _screen("tx", zipcode="78701", county="Travis County", household_size=2, household_assets=0)
    if s:
        p = HouseholdMember.objects.create(screen=s, relationship="headOfHousehold", age=30, has_income=True)
        IncomeStream.objects.create(screen=s, household_member=p, type="wages", amount=2000, frequency="monthly")
        HouseholdMember.objects.create(screen=s, relationship="child", age=3)
        Expense.objects.create(screen=s, type="childCare", amount=800, frequency="monthly")
    return s


def ma_eaedc_eligible():
    s = _screen("ma", zipcode="02108", county="Suffolk County", household_size=1, household_assets=0)
    if s:
        HouseholdMember.objects.create(
            screen=s, relationship="headOfHousehold", age=45, disabled=True, has_income=False
        )
    return s


def eitc_se_loss_co():
    # Wages + a LARGE self-employment loss. The frontier fix changes how an SE loss nets
    # against earned income for EITC — a loss big enough to pull earned income into a
    # different EITC bracket should move the credit. One qualifying child maximizes EITC
    # sensitivity to earned-income changes.
    s = _screen("co", zipcode="80202", county="Denver County", household_size=2, household_assets=0)
    if s:
        p = HouseholdMember.objects.create(screen=s, relationship="headOfHousehold", age=35, has_income=True)
        IncomeStream.objects.create(screen=s, household_member=p, type="wages", amount=2000, frequency="monthly")
        IncomeStream.objects.create(
            screen=s, household_member=p, type="selfEmployment", amount=-1500, frequency="monthly"
        )
        HouseholdMember.objects.create(screen=s, relationship="child", age=6)
    return s


SCENARIOS = {
    "disabled_ssi_co": disabled_ssi_co,
    "asset_near_limit_snap_co": asset_near_limit_snap_co,
    "snap_abawd_mix_co": snap_abawd_mix_co,
    "snap_abawd_partial_co": snap_abawd_partial_co,
    "tx_ccs_childcare": tx_ccs_childcare,
    "ma_eaedc_eligible": ma_eaedc_eligible,
    "eitc_se_loss_co": eitc_se_loss_co,
}


class Command(BaseCommand):
    help = "Diff PolicyEngine eligibility output between two model versions (MFB-1103)."

    def add_arguments(self, parser):
        parser.add_argument("--pe-version", default="1.715.2", help="Pinned PE version to compare against current.")
        parser.add_argument("--scenario", default=None, help="Run a single scenario by name.")
        parser.add_argument(
            "--validation-file",
            default=None,
            help="Path to a validations data JSON; diff each household's expected program at both versions.",
        )

    def handle(self, *args, **opts):
        version = opts["pe_version"]

        if opts["validation_file"]:
            self._diff_validation_file(opts["validation_file"], version)
            return

        names = [opts["scenario"]] if opts["scenario"] else list(SCENARIOS)

        for name in names:
            builder = SCENARIOS.get(name)
            if builder is None:
                self.stderr.write(f"Unknown scenario: {name}")
                continue

            # Build + diff inside a transaction we always roll back, so no test data persists.
            try:
                with transaction.atomic():
                    screen = builder()
                    if screen is None:
                        self.stdout.write(f"\n[{name}] SKIPPED — white label not seeded locally")
                        raise _Rollback()

                    base = _run(screen, None)
                    pinned = _run(screen, version)
                    self._report(name, version, base, pinned)
                    raise _Rollback()
            except _Rollback:
                pass

    def _diff_validation_file(self, path, version):
        """For each scenario in a validations data file, diff the expected program's
        (eligible, value) at current vs the pinned version, and flag whether the
        frontier value still matches the file's hardcoded expected value."""
        with open(path) as f:
            scenarios = json.load(f)

        self.stdout.write(f"\n=== validation diff: {path} (current vs {version}) ===")
        for sc in scenarios:
            household = sc["household"]
            er = sc.get("expected_results", {})
            prog = er.get("program_name")
            expected_value = er.get("value")
            notes = sc.get("notes", "")[:65]

            try:
                with transaction.atomic():
                    serializer = ScreenSerializer(data=household)
                    serializer.is_valid(raise_exception=True)
                    screen = serializer.save()

                    base = _run(screen, None)
                    pinned = _run(screen, version)
                    b = base.get(prog)
                    p = pinned.get(prog)

                    flag = ""
                    if p is not None and expected_value is not None and p[0]:
                        if round(float(expected_value), 2) != p[1]:
                            flag = f"  ⚠️ stored expected={expected_value} != frontier {p[1]}"
                    moved = "  (changed)" if b != p else ""
                    self.stdout.write(f"  [{prog}] {notes}")
                    self.stdout.write(f"      current={b}  frontier={p}{moved}{flag}")
                    raise _Rollback()
            except _Rollback:
                pass

    def _report(self, name, version, base, pinned):
        self.stdout.write(f"\n=== {name} (current vs {version}) ===")
        all_progs = sorted(set(base) | set(pinned))
        changed = [p for p in all_progs if base.get(p) != pinned.get(p)]
        if not changed:
            self.stdout.write("  no program changed")
            return
        for p in changed:
            b = base.get(p, "(absent)")
            f = pinned.get(p, "(absent)")
            self.stdout.write(f"  {p}: {b}  ->  {f}")


class _Rollback(Exception):
    """Sentinel to force the atomic() block to roll back the test screen."""

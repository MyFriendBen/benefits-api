"""
Plan and apply one program's payload, rendered from its program-ops v2 spec.

Unlike `import_program_records`, there is no baseline and nothing is labelled an admin edit,
because the payload has two plain rules:

- **The program row and its English text** are written to match the payload on every apply.
- **Navigators, documents and warning messages** are seeded. One that doesn't exist is created
  from the payload; one that exists is left exactly as it is, since people maintain them in the
  admin. Either way it is linked to the program. Nothing is ever unlinked, and navigator order is
  never rearranged: links people made or ordered in the admin stay as they are.

The writers are `RecordSync`'s, so the checks they make on write (county names against the white
label's ZIP map, shared categories, known legal statuses, programs that resolve) apply here too.
"""

from typing import Any

from django.core.management.base import CommandError, OutputWrapper

from programs.management.commands._program_record_sync import (
    NAVIGATOR,
    RECORD_CHANGE,
    SECTIONS,
    Change,
    EntitySpec,
    RecordPlan,
    RecordSync,
    WARNING,
    _describe,
    _print_notes,
    is_reference,
    section_entries,
)
from programs.models import Program


class ProgramApply(RecordSync):
    """Plan and apply one payload against the program it describes."""

    def plan(self, program: Program, baseline: Any = None, fresh: bool = True) -> RecordPlan:
        """Compare the payload with the database. Reads only; every difference is applied."""
        plan = RecordPlan(program=program)
        # `fresh` makes every program-field difference a change to apply: the payload always wins.
        self._plan_program(plan, None, fresh=True)
        for section, spec in SECTIONS:
            self._plan_seeded_section(plan, section, spec)
        return plan

    def _plan_seeded_section(self, plan: RecordPlan, section: str, spec: EntitySpec) -> None:
        linked = set(self._linked_names(plan.program, spec))
        for entry in section_entries(self.record, section):
            name = entry["external_name"]
            row = spec.model.objects.filter(external_name=name).first()
            if row is None:
                if is_reference(entry):
                    raise CommandError(
                        f"{spec.kind} '{name}' doesn't exist, and the payload only references it. Give its fields "
                        f"to create it."
                    )
                plan.changes.append(
                    Change(
                        key=f"{spec.kind}:{name}",
                        label=RECORD_CHANGE,
                        record="create",
                        database=None,
                        write=lambda _value, spec=spec, name=name: self._create_row(spec, name),
                        phase=0,
                    )
                )
                self._plan_row(plan, spec, entry, None, None, fresh=True)
            elif not is_reference(entry):
                self._note_kept_row(plan, spec, entry, row)

            if spec in (NAVIGATOR, WARNING):
                # Notes which state sees a state navigator or warning on a federal program, whether the
                # payload references it or gives its fields: an apply never changes an existing row, so
                # it keeps its white label either way. A row this apply creates is on the payload's
                # white label, so it gets no note. Documents aren't filtered by white label.
                self._note_state_row_on_federal(plan, spec, name, row)

            if name not in linked:
                plan.changes.append(
                    Change(
                        key=f"link:{spec.kind}:{name}",
                        label=RECORD_CHANGE,
                        record=True,
                        database=False,
                        write=lambda _value, spec=spec, name=name: self._set_link(spec, name, True),
                        phase=2,
                    )
                )

    def _note_kept_row(self, plan: RecordPlan, spec: EntitySpec, entry: dict[str, Any], row: Any) -> None:
        """Say when an existing row differs from the payload, since the apply leaves it alone."""
        scratch = RecordPlan(program=plan.program)
        self._plan_row(scratch, spec, entry, row, None, fresh=True)
        if scratch.changes:
            fields = ", ".join(change.key.rsplit(".", 1)[1] for change in scratch.changes)
            plan.notes.append(
                f"{spec.kind} '{entry['external_name']}' already exists, so it was left as it is. It differs from "
                f"the payload in: {fields}. People maintain it in the admin."
            )


def print_apply_plan(plan: RecordPlan, stdout: OutputWrapper, dry_run: bool) -> None:
    if not plan.changes:
        stdout.write("  ✓ Matches the payload.")
    else:
        stdout.write("  Changes (to apply):" if dry_run else "  Changes (applied):")
        for change in sorted(plan.changes, key=lambda change: change.phase):
            stdout.write(f"    • {_describe(change)}")
    _print_notes(plan, stdout)


def describe_changes(plan: RecordPlan) -> list[str]:
    """The plan's changes as one line each, for the import log."""
    return [_describe(change) for change in sorted(plan.changes, key=lambda change: change.phase)]

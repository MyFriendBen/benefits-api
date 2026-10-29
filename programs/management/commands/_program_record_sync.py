"""
Compare a program-ops record with the database and apply the difference.

A program-ops record is the source of truth for the program it describes, so a program that
already exists is updated to match it rather than skipped. Every field the record manages is
read from the database and compared three ways, against the record and against what the record
set when it was last applied (`ProgramRecordImport.applied_record`):

- **record change**: the record moved and the database didn't. Applied.
- **admin edit**: the database moved and the record didn't. Reported, and applied only when the
  caller asks to revert admin edits.
- **conflict**: both moved. Skipped and reported until someone makes them agree.

Navigators, documents and warning messages are shared rows. An entry naming only an
`external_name` is a reference: it links the row and never edits it. An entry with any other
field is a full entry: the record owns that row's content, and two records owning one row is an
error. A row the record stops listing is unlinked from this program, never deleted.
"""

import shlex
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from django.conf import settings
from django.core.management.base import CommandError, OutputWrapper
from django.db import transaction

from configuration.models import Configuration

from integrations.clients.google_translate import Translate, TranslationIntegrityError, is_auto_translatable
from programs.federal import FEDERAL_WHITE_LABEL
from programs.models import (
    BaseProgram,
    County,
    Document,
    FederalPoveryLimit,
    LegalStatus,
    Navigator,
    NavigatorLanguage,
    Program,
    ProgramCategory,
    ProgramNavigator,
    WarningMessage,
)
from screener.models import WhiteLabel
from translations.models import BLANK_TRANSLATION_PLACEHOLDER, Translation

RECORD_CHANGE = "record change"
ADMIN_EDIT = "admin edit"
CONFLICT = "conflict"

TOP_LEVEL_KEYS = frozenset(
    {"white_label", "program_category", "program", "documents", "navigators", "warning_message", "warning_messages"}
)
CATEGORY_KEYS = frozenset({"external_name", "name", "icon", "description", "tax_category"})

# Program fields a record manages. A field the record leaves out is managed as empty, so a value
# set only in the admin shows up as an admin edit. `external_name` is the exception: it is
# managed only when the record sets it, since a missing one means "generate one". `active` is
# not a record field at all: switching a program on is a release decision made per environment
# in the admin, so a new program is created switched off and no import changes it.
PROGRAM_SCALAR_FIELDS = (
    "low_confidence",
    "show_on_current_benefits",
    "show_in_has_benefits_step",
    "has_calculator",
    "value_format",
    "base_program",
)
PROGRAM_OPTIONAL_FIELDS = ("external_name",)
PROGRAM_PROGRAM_LISTS = ("required_programs", "excludes_programs")
PROGRAM_KEYS = frozenset(
    {"name_abbreviated", "year", "legal_status_required"}
    | set(PROGRAM_SCALAR_FIELDS)
    | set(PROGRAM_OPTIONAL_FIELDS)
    | set(PROGRAM_PROGRAM_LISTS)
    | set(Program.objects.translated_fields)
)


@dataclass(frozen=True)
class EntitySpec:
    """How one kind of shared row is described in a record."""

    kind: str
    model: type
    translated: tuple[str, ...]
    required: tuple[str, ...]
    lists: tuple[str, ...] = ()
    scalars: tuple[str, ...] = ()
    extra_keys: tuple[str, ...] = ()

    @property
    def keys(self) -> frozenset[str]:
        return frozenset({"external_name", *self.translated, *self.lists, *self.scalars, *self.extra_keys})


DOCUMENT = EntitySpec(kind="document", model=Document, translated=("text", "link_url", "link_text"), required=("text",))
NAVIGATOR = EntitySpec(
    kind="navigator",
    model=Navigator,
    translated=("name", "email", "description", "assistance_link"),
    required=("name", "email", "description", "assistance_link"),
    lists=("counties", "languages", "eligibility_programs"),
    scalars=("phone_number",),
)
WARNING = EntitySpec(
    kind="warning",
    model=WarningMessage,
    translated=("message", "link_url", "link_text"),
    required=("message",),
    lists=("counties", "legal_statuses"),
    scalars=("calculator",),
    extra_keys=("white_label",),
)
SECTIONS = (("documents", DOCUMENT), ("navigators", NAVIGATOR), ("warning_messages", WARNING))


def warning_entries(record: dict[str, Any]) -> Any:
    """Return a record's warning messages, whichever of the two shapes it uses."""
    if "warning_message" in record:
        return [record["warning_message"]]
    return record.get("warning_messages", [])


def section_entries(record: dict[str, Any], section: str) -> Any:
    """
    A section's entries as the record has them. Not coerced: `validate_record` rejects anything
    but a list, and callers that run before validation check the type themselves.
    """
    if section == "warning_messages":
        return warning_entries(record)
    return record.get(section, [])


def _stored_phone_number(value: Any) -> Any:
    """
    A phone number in the form the database stores it (E.164 where it parses).

    Compared raw, `+1 303-555-0100` in a record never equals the `+13035550100` the field saves,
    so every run after the first would report an admin edit nobody made.
    """
    if not value:
        return value
    stored = Navigator._meta.get_field("phone_number").get_prep_value(value)
    return None if stored is None else str(stored)


def is_reference(entry: dict[str, Any]) -> bool:
    return set(entry) == {"external_name"}


def validate_record(record: Any) -> list[str]:
    """
    Return every problem with a record's shape, or an empty list.

    Unknown keys are errors rather than being ignored: the importer used to drop them silently,
    which is how a typo like `has_calculcator` left a field unset with nothing reporting it.
    """
    if not isinstance(record, dict):
        return ["the record is not a JSON object"]

    problems = [f"unknown top-level key '{key}'" for key in sorted(set(record) - TOP_LEVEL_KEYS)]
    for key in ("white_label", "program_category", "program"):
        if not isinstance(record.get(key), dict):
            problems.append(f"'{key}' is missing or not an object")
    if problems:
        return problems

    if "warning_message" in record and "warning_messages" in record:
        problems.append("use 'warning_message' or 'warning_messages', not both")

    problems += [f"unknown white_label key '{key}'" for key in sorted(set(record["white_label"]) - {"code"})]
    if not isinstance(record["white_label"].get("code"), str) or not record["white_label"]["code"]:
        problems.append("white_label has no 'code'")
    problems += [
        f"unknown program_category key '{key}'" for key in sorted(set(record["program_category"]) - CATEGORY_KEYS)
    ]
    if "external_name" not in record["program_category"]:
        problems.append("program_category has no 'external_name' (use null for a program with no category)")

    program = record["program"]
    if "active" in program:
        problems.append(
            "program.active isn't a record field: a program is switched on or off in the admin, per environment"
        )
    problems += [f"unknown program key '{key}'" for key in sorted(set(program) - PROGRAM_KEYS - {"active"})]
    if not isinstance(program.get("name_abbreviated"), str) or not program["name_abbreviated"]:
        problems.append("program has no 'name_abbreviated'")
    if program.get("base_program") is not None and program["base_program"] not in BaseProgram.values:
        problems.append(f"program.base_program '{program['base_program']}' is not a BaseProgram value")
    value_formats = {value for value, _ in Program.VALUE_FORMAT_CHOICES}
    value_format = program.get("value_format")
    # Type first: a list or object isn't hashable, and the set lookup would raise.
    if not (value_format is None or isinstance(value_format, str)) or value_format not in value_formats:
        # The setter saves without model validation, so an unknown format would be stored as is.
        problems.append(
            f"program.value_format '{program['value_format']}' isn't one of "
            f"{', '.join(str(value) for value in sorted(value_formats, key=str))}"
        )

    for section, spec in SECTIONS:
        entries = section_entries(record, section)
        if not isinstance(entries, list):
            problems.append(f"'{section}' must be a list")
            continue
        seen: set[str] = set()
        for i, entry in enumerate(entries):
            where = f"{section}[{i}]"
            if (
                not isinstance(entry, dict)
                or not isinstance(entry.get("external_name"), str)
                or not entry["external_name"]
            ):
                problems.append(f"{where} has no 'external_name'")
                continue
            name = entry["external_name"]
            where = f"{section}[{i}] ({name})"
            if name in seen:
                problems.append(f"{where} is listed twice")
            seen.add(name)
            problems += [f"{where}: unknown key '{key}'" for key in sorted(set(entry) - spec.keys)]
            if "white_label" in entry and entry["white_label"] != record["white_label"].get("code"):
                problems.append(f"{where}: white_label '{entry['white_label']}' isn't the record's white label")
            if is_reference(entry):
                continue
            missing = [key for key in spec.required if key not in entry]
            if missing:
                problems.append(
                    f"{where} is a partial entry, missing {', '.join(missing)}. List only 'external_name' to link "
                    f"an existing {spec.kind}, or give every required field to own it."
                )
    return problems


def owned_rows(record: dict[str, Any]) -> list[tuple[str, str]]:
    """Return (kind, external_name) for every shared row a record owns through a full entry."""
    rows = []
    for section, spec in SECTIONS:
        entries = section_entries(record, section)
        if not isinstance(entries, list):
            continue  # reported when the record itself is validated
        rows += [
            (spec.kind, entry["external_name"])
            for entry in entries
            if isinstance(entry, dict) and isinstance(entry.get("external_name"), str) and not is_reference(entry)
        ]
    return rows


@dataclass
class Change:
    key: str
    label: str
    record: Any
    database: Any
    write: Callable[[Any], None]
    phase: int


@dataclass
class RecordPlan:
    program: Program
    changes: list[Change] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    # The values this run applies, to store as the next run's baseline.
    record_values: dict[str, Any] = field(default_factory=dict)
    previous_baseline: Optional[dict[str, Any]] = None

    def by_label(self, label: str) -> list[Change]:
        return [change for change in self.changes if change.label == label]

    def reverts(self, change: Change, revert_admin_edits: bool, revert_keys: frozenset[str] = frozenset()) -> bool:
        """Whether this run sets an admin edit back to the record: all of them, or the keys named."""
        return change.label == ADMIN_EDIT and (revert_admin_edits or change.key in revert_keys)

    def to_apply(self, revert_admin_edits: bool, revert_keys: frozenset[str] = frozenset()) -> list[Change]:
        return [
            change
            for change in self.changes
            if change.label == RECORD_CHANGE or self.reverts(change, revert_admin_edits, revert_keys)
        ]

    def next_baseline(self) -> dict[str, Any]:
        """
        The baseline to store once this plan is applied.

        A conflict keeps the old baseline, so it stays a conflict until the two sides agree
        instead of quietly turning into an admin edit on the next run.
        """
        baseline = dict(self.record_values)
        previous = self.previous_baseline or {}
        for change in self.by_label(CONFLICT):
            if change.key in previous:
                baseline[change.key] = previous[change.key]
            else:
                baseline.pop(change.key, None)
        return {key: value for key, value in baseline.items() if value is not False or not key.startswith("link:")}


def _is_empty(value: Any) -> bool:
    # False is a choice, not a gap: a flag switched off or a link removed in the admin is kept.
    return value is not False and value in (None, "", [], BLANK_TRANSLATION_PLACEHOLDER)


def _label(
    key: str, record: Any, database: Any, baseline: Optional[dict[str, Any]], fresh: bool, new_row: bool
) -> Optional[str]:
    """Return how a difference came about, or None when the record and database agree."""
    if record == database:
        return None
    if fresh or new_row:
        return RECORD_CHANGE
    if key.startswith("link:") and baseline is not None:
        previous = baseline.get(key, False)
    elif baseline is not None and key in baseline:
        previous = baseline[key]
    else:
        # Never applied under this importer, or a field or shared row the record didn't manage
        # last time: nothing says which side moved. An empty database value has nothing worth
        # protecting, so the record fills it; anything else is treated as an admin edit and kept
        # until someone decides.
        return RECORD_CHANGE if _is_empty(database) else ADMIN_EDIT
    if database == previous:
        return RECORD_CHANGE
    if record == previous:
        return ADMIN_EDIT
    return CONFLICT


def _english(translation: Translation) -> str:
    row = translation.get_lang(settings.LANGUAGE_CODE)
    return row.text if row is not None and row.text is not None else ""


def _edited_languages(translation: Translation) -> list[str]:
    return sorted(
        translation.translations.filter(edited=True)
        .exclude(language_code=settings.LANGUAGE_CODE)
        .values_list("language_code", flat=True)
    )


class TranslationWriter:
    """
    Write English text and re-translate the other languages, keeping human edits.

    A language someone edited by hand keeps its text, so a correction made in the admin isn't
    machine-translated away. Everything else is re-translated from the new English, in one batch
    per run. A string that can't be machine-translated, or a language whose placeholders don't
    survive, keeps its old text and is reported.
    """

    def __init__(self, stdout: OutputWrapper, skip_translation: bool = False) -> None:
        self.stdout = stdout
        self.skip_translation = skip_translation
        self.pending: list[tuple[Translation, str]] = []

    def write(self, translation: Translation, text: str) -> None:
        Translation.objects.edit_translation_by_id(translation.id, settings.LANGUAGE_CODE, text, manual=True)
        self.pending.append((translation, text))

    def flush(self) -> None:
        to_translate = sorted(
            {
                text
                for translation, text in self.pending
                if text and not translation.no_auto and not self.skip_translation and is_auto_translatable(text)
            }
        )
        translated: dict[str, dict[str, str]] = {}
        if to_translate:
            try:
                translated = Translate().bulk_translate(Translate.languages, to_translate, strict=False)
            except TranslationIntegrityError as e:
                self.stdout.write(f"  Could not auto-translate: {e}")

        for translation, text in self.pending:
            edited = set(_edited_languages(translation))
            untranslated = []
            for lang in Translate.languages:
                if lang in edited:
                    continue
                if translation.no_auto or self.skip_translation or not text:
                    value: Optional[str] = text
                else:
                    value = translated.get(text, {}).get(lang)
                if value is None:
                    untranslated.append(lang)
                    continue
                Translation.objects.edit_translation_by_id(translation.id, lang, value, manual=False)
            if untranslated:
                # The English changed but these languages kept the old text, and a later run won't
                # see a difference to report, so say so now.
                self.stdout.write(
                    f"  Not re-translated, old text kept: {translation.label} ({', '.join(untranslated)}). "
                    f"Translate these by hand in the admin."
                )
        self.pending = []


def valid_county_names(white_label: WhiteLabel) -> Optional[set[str]]:
    """
    The county names the screener stores in `Screen.county` for a white label.

    Read from its `counties_by_zipcode` configuration. None when it has none, in which case
    counties aren't checked.
    """
    try:
        data = Configuration.counties_by_zipcode(white_label)
    except ValueError as e:
        raise CommandError(str(e)) from e
    if data is None:
        return None
    return {name for county_map in data.values() if isinstance(county_map, dict) for name in county_map}


class RecordSync:
    """Plan and apply one program-ops record against the program it describes."""

    def __init__(self, record: dict[str, Any], stdout: OutputWrapper, skip_translation: bool = False) -> None:
        self.record = record
        self.stdout = stdout
        self.translations = TranslationWriter(stdout, skip_translation=skip_translation)
        self.white_label = WhiteLabel.objects.get(code=record["white_label"]["code"])
        self.program_key = record["program"]["name_abbreviated"]

    def create_program(self) -> Program:
        """
        Create the record's program, switched off, with nothing set yet.

        Planning it afterwards with `fresh=True` fills every field from the record, so a new program
        goes through the same code as an update.
        """
        return Program.objects.new_program(
            white_label=self.white_label.code,
            name_abbreviated=self.program_key,
            external_name=self.record["program"].get("external_name"),
        )

    # ------------------------------------------------------------------ planning

    def plan(self, program: Program, baseline: Optional[dict[str, Any]], fresh: bool = False) -> RecordPlan:
        """
        Compare the record with the database. Reads only.

        `fresh` marks a program this run just created from the record, so every difference left
        is the record's to apply.
        """
        plan = RecordPlan(program=program, previous_baseline=baseline)
        self._plan_program(plan, baseline, fresh)
        for section, spec in SECTIONS:
            self._plan_section(plan, section, spec, baseline, fresh)
        self._plan_navigator_order(plan, baseline, fresh)
        return plan

    def _add(
        self,
        plan: RecordPlan,
        key: str,
        record_value: Any,
        database_value: Any,
        write: Callable[[Any], None],
        phase: int,
        baseline: Optional[dict[str, Any]],
        fresh: bool,
        new_row: bool = False,
    ) -> Optional[Change]:
        plan.record_values[key] = record_value
        label = _label(key, record_value, database_value, baseline, fresh, new_row)
        if label is None:
            return None
        change = Change(key=key, label=label, record=record_value, database=database_value, write=write, phase=phase)
        plan.changes.append(change)
        return change

    def _plan_program(self, plan: RecordPlan, baseline: Optional[dict[str, Any]], fresh: bool) -> None:
        program = plan.program
        data = self.record["program"]

        for name in PROGRAM_SCALAR_FIELDS:
            default = Program._meta.get_field(name).get_default()
            self._add(
                plan,
                f"program.{name}",
                data.get(name, default),
                getattr(program, name),
                self._program_setter(name),
                1,
                baseline,
                fresh,
            )
        for name in PROGRAM_OPTIONAL_FIELDS:
            if name in data:
                self._add(
                    plan,
                    f"program.{name}",
                    data[name],
                    getattr(program, name),
                    self._program_setter(name),
                    1,
                    baseline,
                    fresh,
                )

        year = data.get("year")
        self._add(
            plan,
            "program.year",
            None if year is None else str(year),
            program.year.year if program.year_id else None,
            self._set_year,
            1,
            baseline,
            fresh,
        )
        self._add(
            plan,
            "program.category",
            self.record["program_category"]["external_name"],
            program.category.external_name if program.category_id else None,
            self._set_category,
            1,
            baseline,
            fresh,
        )
        self._add(
            plan,
            "program.legal_status_required",
            sorted(data.get("legal_status_required", [])),
            sorted(program.legal_status_required.values_list("status", flat=True)),
            lambda value: program.legal_status_required.set(self._legal_statuses(value)),
            1,
            baseline,
            fresh,
        )
        for name in PROGRAM_PROGRAM_LISTS:
            relation = getattr(program, name)
            self._add(
                plan,
                f"program.{name}",
                sorted(data.get(name, [])),
                sorted(relation.values_list("name_abbreviated", flat=True)),
                lambda value, relation=relation: relation.set(self._programs(value)),
                3,
                baseline,
                fresh,
            )

        for name in Program.objects.translated_fields:
            translation = getattr(program, name)
            change = self._add(
                plan,
                f"program.{name}",
                data.get(name, ""),
                _english(translation),
                lambda value, translation=translation: self.translations.write(translation, value),
                1,
                baseline,
                fresh,
            )
            self._note_kept_translations(plan, change, translation)

    def _plan_section(
        self, plan: RecordPlan, section: str, spec: EntitySpec, baseline: Optional[dict[str, Any]], fresh: bool
    ) -> None:
        program = plan.program
        entries = section_entries(self.record, section)
        listed = {entry["external_name"] for entry in entries}
        linked = set(self._linked_names(program, spec))
        previously_linked = {
            key.split(":", 2)[2] for key in (baseline or {}) if key.startswith(f"link:{spec.kind}:") and baseline[key]
        }

        for entry in entries:
            name = entry["external_name"]
            row = spec.model.objects.filter(external_name=name).first()
            new_row = row is None
            if new_row:
                if is_reference(entry):
                    raise CommandError(
                        f"{spec.kind} '{name}' doesn't exist, and the record only references it. Give its fields to "
                        f"create it."
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
            elif not is_reference(entry):
                # An existing row is shared: creating this program doesn't make the record newer
                # than an admin edit to it, so it's labelled like any update, never as fresh.
                self._plan_row(plan, spec, entry, row, baseline, fresh=False)
                others = self._other_programs(row, spec, program)
                if others and any(change.key.startswith(f"{spec.kind}:{name}.") for change in plan.changes):
                    plan.notes.append(
                        f"{spec.kind} '{name}' is also shown on {', '.join(others)}; changing it changes it there too."
                    )
            if new_row:
                self._plan_row(plan, spec, entry, None, baseline, fresh)
            elif spec is NAVIGATOR:
                self._plan_federal_navigator_owner(plan, entry, row)

            self._add(
                plan,
                f"link:{spec.kind}:{name}",
                True,
                name in linked,
                lambda value, spec=spec, name=name: self._set_link(spec, name, value),
                2,
                baseline,
                fresh,
                new_row=new_row,
            )

        for name in sorted((linked | previously_linked) - listed):
            change = self._add(
                plan,
                f"link:{spec.kind}:{name}",
                False,
                name in linked,
                lambda value, spec=spec, name=name: self._set_link(spec, name, value),
                2,
                baseline,
                fresh,
            )
            if change and change.database:
                row = spec.model.objects.filter(external_name=name).first()
                if row is not None and not self._other_programs(row, spec, program):
                    plan.notes.append(
                        f"{spec.kind} '{name}' is linked to no other program, so unlinking it leaves it unused."
                    )

    def _plan_federal_navigator_owner(self, plan: RecordPlan, entry: dict[str, Any], row: Navigator) -> None:
        """A federal record's navigators must belong to `federal`.

        On a federal program a state's navigator is shown only to that state's screens
        (`screener.navigators.filter_by_white_label`), and a navigator belongs to whichever white
        label created it first. A navigator this record owns is moved to `federal`; that leaves
        the state programs still linking it unchanged, since they don't filter by white label. One
        it only references is refused, since moving it would override the record that owns it.
        """
        if self.white_label.code != FEDERAL_WHITE_LABEL or row.white_label_id == self.white_label.id:
            return
        name = entry["external_name"]
        owner = row.white_label.code
        if is_reference(entry):
            raise CommandError(
                f"navigator '{name}' belongs to the '{owner}' white label, so on this federal program only "
                f"'{owner}' screens would see it. Own it in this record (give its fields) to move it to "
                f"'{FEDERAL_WHITE_LABEL}', or link it from the state program instead."
            )
        plan.changes.append(
            Change(
                key=f"navigator:{name}.white_label",
                label=RECORD_CHANGE,
                record=FEDERAL_WHITE_LABEL,
                database=owner,
                write=lambda _value, name=name: Navigator.objects.filter(external_name=name).update(
                    white_label=self.white_label
                ),
                phase=0,
            )
        )

    def _plan_row(
        self,
        plan: RecordPlan,
        spec: EntitySpec,
        entry: dict[str, Any],
        row: Any,
        baseline: Optional[dict[str, Any]],
        fresh: bool,
    ) -> None:
        name = entry["external_name"]
        new_row = row is None
        for field_name in spec.translated:
            translation = None if new_row else getattr(row, field_name)
            change = self._add(
                plan,
                f"{spec.kind}:{name}.{field_name}",
                entry.get(field_name, ""),
                None if translation is None else _english(translation),
                lambda value, spec=spec, name=name, field_name=field_name: self.translations.write(
                    getattr(self._row(spec, name), field_name), value
                ),
                1,
                baseline,
                fresh,
                new_row=new_row,
            )
            if translation is not None:
                self._note_kept_translations(plan, change, translation)
        for field_name in spec.scalars:
            default = "_show" if field_name == "calculator" else None
            current = None if new_row else getattr(row, field_name)
            value = entry.get(field_name, default)
            if field_name == "phone_number":
                value = _stored_phone_number(value)
            self._add(
                plan,
                f"{spec.kind}:{name}.{field_name}",
                value,
                None if current is None else str(current),
                lambda value, spec=spec, name=name, field_name=field_name: self._set_row_field(
                    spec, name, field_name, value
                ),
                1,
                baseline,
                fresh,
                new_row=new_row,
            )
        for field_name in spec.lists:
            self._add(
                plan,
                f"{spec.kind}:{name}.{field_name}",
                sorted(entry.get(field_name, [])),
                [] if new_row else self._row_list(row, field_name),
                lambda value, spec=spec, name=name, field_name=field_name: self._set_row_list(
                    spec, name, field_name, value
                ),
                3 if field_name == "eligibility_programs" else 1,
                baseline,
                fresh,
                new_row=new_row,
            )

    def _plan_navigator_order(self, plan: RecordPlan, baseline: Optional[dict[str, Any]], fresh: bool) -> None:
        wanted = [entry["external_name"] for entry in self.record.get("navigators", [])]
        if not wanted:
            return
        current = [
            name
            for name in ProgramNavigator.objects.filter(program=plan.program)
            .order_by("order", "id")
            .values_list("navigator__external_name", flat=True)
            if name in wanted
        ]
        self._add(plan, "navigators.order", wanted, current, self._set_navigator_order, 4, baseline, fresh)

    def _note_kept_translations(self, plan: RecordPlan, change: Optional[Change], translation: Translation) -> None:
        if change is None or change.label != RECORD_CHANGE:
            return
        edited = _edited_languages(translation)
        if edited:
            plan.notes.append(
                f"{change.key}: hand-edited translations are kept ({', '.join(edited)}) and may no longer match "
                f"the new English."
            )

    # ------------------------------------------------------------------ database reads

    def _linked_names(self, program: Program, spec: EntitySpec) -> list[str]:
        """Names of the rows linked to the program. A row with no external_name can't be named in a
        record, so it is left out: it stays linked, and the record neither manages nor reports it."""
        if spec is DOCUMENT:
            names = program.documents.values_list("external_name", flat=True)
        elif spec is NAVIGATOR:
            names = ProgramNavigator.objects.filter(program=program).values_list("navigator__external_name", flat=True)
        else:
            names = program.warning_messages.values_list("external_name", flat=True)
        return [name for name in names if name]

    def _other_programs(self, row: Any, spec: EntitySpec, program: Program) -> list[str]:
        if spec is DOCUMENT:
            programs = row.program_documents.exclude(id=program.id)
        elif spec is NAVIGATOR:
            programs = Program.objects.filter(program_navigators__navigator=row).exclude(id=program.id)
        else:
            programs = row.programs.exclude(id=program.id)
        return sorted(f"{p.white_label.code}/{p.name_abbreviated}" for p in programs.select_related("white_label"))

    @staticmethod
    def _row_list(row: Any, field_name: str) -> list[str]:
        if field_name == "counties":
            return sorted(row.counties.values_list("name", flat=True))
        if field_name == "languages":
            return sorted(row.languages.values_list("code", flat=True))
        if field_name == "legal_statuses":
            return sorted(row.legal_statuses.values_list("status", flat=True))
        return sorted(row.eligibility_programs.values_list("name_abbreviated", flat=True))

    def _row(self, spec: EntitySpec, name: str) -> Any:
        return spec.model.objects.get(external_name=name)

    # ------------------------------------------------------------------ writes

    def apply(
        self, plan: RecordPlan, revert_admin_edits: bool = False, revert_keys: frozenset[str] = frozenset()
    ) -> None:
        """Apply the plan's record changes, and its admin edits if asked, in one transaction."""
        with transaction.atomic():
            for change in sorted(plan.to_apply(revert_admin_edits, revert_keys), key=lambda change: change.phase):
                change.write(change.record)
            self.translations.flush()

    def _program_setter(self, name: str) -> Callable[[Any], None]:
        def write(value: Any) -> None:
            program = Program.objects.get(white_label=self.white_label, name_abbreviated=self.program_key)
            if name == "external_name" and Program.objects.filter(external_name=value).exclude(id=program.id).exists():
                raise CommandError(f"program external_name '{value}' is already used by another program")
            setattr(program, name, value)
            program.save(update_fields=[name])

        return write

    def _program(self) -> Program:
        return Program.objects.get(white_label=self.white_label, name_abbreviated=self.program_key)

    def _set_year(self, value: Optional[str]) -> None:
        program = self._program()
        if value is None:
            program.year = None
            program.year_type = "hardcoded"
        else:
            try:
                program.year = FederalPoveryLimit.objects.get(year=value)
            except FederalPoveryLimit.DoesNotExist:
                raise CommandError(f"program.year '{value}' has no FederalPovertyLimit row") from None
            # A dynamic row's year type has to agree with it, the same rule the create path follows.
            program.year_type = {"THIS_YEAR_CALENDAR": "calendar_year", "THIS_YEAR_FISCAL": "fiscal_year"}.get(
                value, "hardcoded"
            )
        program.save(update_fields=["year", "year_type"])

    def _set_category(self, value: Optional[str]) -> None:
        category = None
        if value is not None:
            try:
                category = ProgramCategory.objects.get(external_name=value)
            except ProgramCategory.DoesNotExist:
                raise CommandError(
                    f"program_category '{value}' doesn't exist. A new category is shared by every white label, "
                    f"so a developer adds it."
                ) from None
            if category.white_label_id not in (None, self.white_label.id):
                raise CommandError(
                    f"program_category '{value}' belongs to the '{category.white_label.code}' white label, not "
                    f"'{self.white_label.code}'"
                )
        program = self._program()
        program.category = category
        program.save(update_fields=["category"])

    def _legal_statuses(self, codes: list[str]) -> list[LegalStatus]:
        statuses = []
        for code in codes:
            status = LegalStatus.objects.filter(status=code).first()
            if status is None:
                raise CommandError(f"legal status '{code}' doesn't exist")
            statuses.append(status)
        return statuses

    def _programs(self, keys: list[str]) -> list[Program]:
        """Resolve program keys in this record's white label, falling back to the federal one."""
        programs = []
        for key in keys:
            program = (
                Program.objects.filter(white_label=self.white_label, name_abbreviated=key).first()
                or Program.objects.filter(white_label__code="federal", name_abbreviated=key).first()
            )
            if program is None:
                raise CommandError(f"no program '{key}' in '{self.white_label.code}' or 'federal'")
            programs.append(program)
        return programs

    def _create_row(self, spec: EntitySpec, name: str) -> None:
        code = self.white_label.code
        if spec is DOCUMENT:
            Document.objects.new_document(white_label=code, external_name=name)
        elif spec is NAVIGATOR:
            navigator = Navigator.objects.new_navigator(white_label=code, name=name)
            navigator.external_name = name
            navigator.save()
        else:
            WarningMessage.objects.new_warning(white_label=code, calculator="_show", external_name=name)

    def _set_link(self, spec: EntitySpec, name: str, linked: bool) -> None:
        program = self._program()
        row = self._row(spec, name)
        if spec is DOCUMENT:
            (program.documents.add if linked else program.documents.remove)(row)
        elif spec is NAVIGATOR:
            if linked:
                ProgramNavigator.objects.get_or_create(
                    program=program, navigator=row, defaults={"order": self._next_navigator_order(program)}
                )
            else:
                ProgramNavigator.objects.filter(program=program, navigator=row).delete()
        else:
            (row.programs.add if linked else row.programs.remove)(program)

    def _next_navigator_order(self, program: Program) -> int:
        orders = ProgramNavigator.objects.filter(program=program).values_list("order", flat=True)
        return max(orders, default=-1) + 1

    def _set_navigator_order(self, wanted: list[str]) -> None:
        """Put the record's navigators first, in its order; links made in the admin follow."""
        links = list(ProgramNavigator.objects.filter(program=self._program()).order_by("order", "id"))
        by_name = {link.navigator.external_name: link for link in links}
        ordered = [by_name[name] for name in wanted if name in by_name]
        ordered += [link for link in links if link not in ordered]
        for order, link in enumerate(ordered):
            if link.order != order:
                link.order = order
                link.save(update_fields=["order"])

    def _set_row_field(self, spec: EntitySpec, name: str, field_name: str, value: Any) -> None:
        row = self._row(spec, name)
        setattr(row, field_name, value)
        row.save(update_fields=[field_name])

    def _set_row_list(self, spec: EntitySpec, name: str, field_name: str, values: list[str]) -> None:
        row = self._row(spec, name)
        if field_name == "counties":
            row.counties.set(self._counties(spec, row, values))
        elif field_name == "languages":
            row.languages.set([NavigatorLanguage.objects.get_or_create(code=code)[0] for code in values])
        elif field_name == "legal_statuses":
            row.legal_statuses.set(self._legal_statuses(values))
        else:
            row.eligibility_programs.set(self._programs(values))

    def _counties(self, spec: EntitySpec, row: Any, names: list[str]) -> list[County]:
        """
        Resolve county names, refusing any the screener never sends.

        A county filter is an exact string match against the household's county, so a name in
        the wrong form would silently match nobody.
        """
        valid = valid_county_names(self.white_label)
        invalid = [name for name in names if valid is not None and name not in valid]
        if invalid:
            raise CommandError(
                f"{spec.kind} '{row.external_name}': {', '.join(invalid)} not in the "
                f"'{self.white_label.code}' county list the screener sends"
            )
        if spec is NAVIGATOR:
            return [County.objects.get_or_create(name=name, white_label=self.white_label)[0] for name in names]
        counties = []
        for name in names:
            county = County.objects.filter(name=name, white_label=row.white_label).first()
            if county is None:
                raise CommandError(f"warning '{row.external_name}': county '{name}' doesn't exist")
            counties.append(county)
        return counties


def _short(value: Any, limit: int = 70) -> str:
    text = value if isinstance(value, str) else repr(value)
    text = text.replace("\n", "\\n")
    return f'"{text[:limit]}…"' if isinstance(value, str) and len(text) > limit else repr(value)


def _describe(change: Change) -> str:
    if change.key.startswith("link:"):
        _, kind, name = change.key.split(":", 2)
        if change.label == ADMIN_EDIT:
            state = "linked in the admin, not in the record" if change.database else "unlinked in the admin"
            return f"{kind} '{name}': {state}"
        return f"{kind} '{name}': {'link' if change.record else 'unlink'}"
    if change.record == "create" and change.database is None and change.phase == 0:
        return f"{change.key}: create"
    if change.label == RECORD_CHANGE:
        return f"{change.key}: {_short(change.database)} → {_short(change.record)}"
    return f"{change.key}: database {_short(change.database)} | record {_short(change.record)}"


REVERT_HINT = "revert with --revert-admin-edit"


def print_plan(
    plan: RecordPlan,
    stdout: OutputWrapper,
    revert_admin_edits: bool,
    dry_run: bool = False,
    record_file: str = "",
    revert_keys: frozenset[str] = frozenset(),
) -> None:
    """
    Print the plan. Every kept admin edit names the `--revert-admin-edit <file>:<key>` that
    applies the record over it alone, which is how program-ops' import script asks one at a time.
    """
    record_changes = plan.by_label(RECORD_CHANGE)
    admin_edits = plan.by_label(ADMIN_EDIT)
    reverted = [change for change in admin_edits if plan.reverts(change, revert_admin_edits, revert_keys)]
    kept = [change for change in admin_edits if not plan.reverts(change, revert_admin_edits, revert_keys)]
    conflicts = plan.by_label(CONFLICT)
    if not plan.changes:
        stdout.write("  ✓ Matches the record.")
        return

    sections = [
        (record_changes, "Record changes (to apply)" if dry_run else "Record changes (applied)"),
        (reverted, "Admin edits (reverted to the record)"),
        (kept, "Admin edits (kept)"),
        (conflicts, "Conflicts: changed in both the record and the admin (skipped)"),
    ]
    for changes, title in sections:
        if not changes:
            continue
        stdout.write(f"  {title}:")
        for change in changes:
            stdout.write(f"    • {_describe(change)}")
            if record_file and change.label == ADMIN_EDIT and not plan.reverts(change, revert_admin_edits, revert_keys):
                # Quoted for a shell: a key carries the row's external_name, which may have spaces.
                stdout.write(f"      {REVERT_HINT} {shlex.quote(f'{record_file}:{change.key}')}")
    if plan.notes:
        stdout.write("  Notes:")
        for note in plan.notes:
            stdout.write(f"    • {note}")


PROGRAM_KEY_ORDER = (
    "name_abbreviated",
    "legal_status_required",
    "name",
    "description_short",
    "description",
    "website_description",
    "learn_more_link",
    "apply_button_link",
    "apply_button_description",
    "estimated_application_time",
    "estimated_decision_time",
    "estimated_delivery_time",
    "estimated_value",
    "value_format",
    "year",
    "show_on_current_benefits",
    "has_calculator",
    "show_in_has_benefits_step",
    "base_program",
    "external_name",
    "active",
    "low_confidence",
    "required_programs",
    "excludes_programs",
)


def _ordered_like(values: list[str], previous: list[Any]) -> list[str]:
    """Keep the record's own order for the values it already lists; anything new follows, sorted."""
    kept = [value for value in previous if value in values]
    return kept + sorted(value for value in values if value not in kept)


def record_from_database(program: Program, existing: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """
    Write a program's current state in record form.

    Given the record it came from, the export keeps that record's choices: which entries are
    references, which optional keys it sets, and the order it lists things in. A row linked in the
    admin and absent from the record comes out as a reference, since another record may own it.
    Applying the result changes nothing.
    """
    existing = existing or {}
    previous = existing.get("program", {})

    values: dict[str, Any] = {
        "name_abbreviated": program.name_abbreviated,
        "legal_status_required": _ordered_like(
            list(program.legal_status_required.values_list("status", flat=True)),
            previous.get("legal_status_required", []),
        ),
        "value_format": program.value_format,
        "year": program.year.year if program.year_id else None,
        "show_on_current_benefits": program.show_on_current_benefits,
        "has_calculator": program.has_calculator,
        "show_in_has_benefits_step": program.show_in_has_benefits_step,
    }
    for name in Program.objects.translated_fields:
        text = _english(getattr(program, name))
        if text or name in previous or name != "estimated_decision_time":
            values[name] = text
    if program.base_program:
        values["base_program"] = program.base_program
    # `active` is left out: an import never reads it, so writing it would only suggest it does.
    if "external_name" in previous:
        values["external_name"] = program.external_name
    if program.low_confidence or "low_confidence" in previous:
        values["low_confidence"] = program.low_confidence
    for name in PROGRAM_PROGRAM_LISTS:
        keys = list(getattr(program, name).values_list("name_abbreviated", flat=True))
        if keys or name in previous:
            values[name] = _ordered_like(keys, previous.get(name, []))

    record: dict[str, Any] = {
        "white_label": {"code": program.white_label.code},
        "program_category": {"external_name": program.category.external_name if program.category_id else None},
        "program": _keyed_like(values, list(previous), PROGRAM_KEY_ORDER),
    }

    for section, spec in SECTIONS:
        previous_entries = {entry["external_name"]: entry for entry in section_entries(existing, section)}
        if spec is NAVIGATOR:
            rows = [
                link.navigator
                for link in ProgramNavigator.objects.filter(program=program)
                .select_related("navigator")
                .order_by("order", "id")
            ]
        else:
            rows = list(program.documents.all() if spec is DOCUMENT else program.warning_messages.all())
        rows = [row for row in rows if row.external_name]  # a record can't name an unnamed row
        if spec is not NAVIGATOR:
            order = _ordered_like([row.external_name for row in rows], list(previous_entries))
            rows.sort(key=lambda row: order.index(row.external_name))

        entries = []
        for row in rows:
            entry = previous_entries.get(row.external_name)
            if entry is None or is_reference(entry):
                entries.append({"external_name": row.external_name})
            else:
                entries.append(_entry_from_row(spec, row, entry))
        if not entries:
            continue
        if section == "warning_messages" and "warning_message" in existing and len(entries) == 1:
            record["warning_message"] = entries[0]
        else:
            record[section] = entries
    canonical = ("white_label", "program_category", "program", "documents", "navigators")
    return _keyed_like(record, list(existing), (*canonical, "warning_message", "warning_messages"))


def _keyed_like(values: dict[str, Any], previous: list[str], canonical: tuple[str, ...]) -> dict[str, Any]:
    """Order keys as the record already had them, then in template order, so an export diffs cleanly."""
    order = [key for key in previous if key in values]
    order += [key for key in canonical if key in values and key not in order]
    return {key: values[key] for key in order}


def _entry_from_row(spec: EntitySpec, row: Any, previous: dict[str, Any]) -> dict[str, Any]:
    canonical = ("external_name", *spec.translated, *spec.scalars, *spec.lists, *spec.extra_keys)
    return _keyed_like(_entry_values(spec, row, previous), list(previous), canonical)


def _entry_values(spec: EntitySpec, row: Any, previous: dict[str, Any]) -> dict[str, Any]:
    entry: dict[str, Any] = {"external_name": row.external_name}
    for field_name in spec.scalars:
        value = getattr(row, field_name)
        if field_name == "calculator" or value or field_name in previous:
            entry[field_name] = "" if value is None else str(value)
    for field_name in spec.translated:
        text = _english(getattr(row, field_name))
        if text or field_name in spec.required or field_name in previous:
            entry[field_name] = text
    for field_name in spec.lists:
        values = RecordSync._row_list(row, field_name)
        if values or field_name in previous:
            entry[field_name] = _ordered_like(values, previous.get(field_name, []))
    if "white_label" in previous:
        entry["white_label"] = previous["white_label"]
    return entry

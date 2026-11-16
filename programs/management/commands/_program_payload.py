"""
The payload `apply_program` accepts: one program's fields, rendered from its program-ops v2 spec.

`parse_payload` checks a payload against a strict, typed model and builds it, or raises
`PayloadError` listing every problem at once. Nothing reaches the database until a payload has
parsed. program-ops' renderer produces the same shape, and both repos test against
`tests/fixtures/example_program_payload.json`, so a change to the shape is a change to both.

The shape follows a program record (`_program_record_sync.py`) so the same writers apply it, with
three differences: every program field is required unless it has an obvious default, values must
have the right type, and only the plural `warning_messages` is accepted.
"""

from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urlparse

from programs.models import BaseProgram, Program

TOP_LEVEL_KEYS = ("white_label", "program_category", "program", "documents", "navigators", "warning_messages")

PROGRAM_TEXT_FIELDS = Program.objects.translated_fields
PROGRAM_FLAGS = ("has_calculator", "show_on_current_benefits", "show_in_has_benefits_step", "low_confidence")
PROGRAM_URL_FIELDS = ("learn_more_link", "apply_button_link")
# Required on every payload. `value_format` and `year` may be null, but must be present.
PROGRAM_REQUIRED = ("name_abbreviated", "legal_status_required", "value_format", "year", *PROGRAM_FLAGS)
# May be left out: a missing `external_name` is generated, and the rest default to empty.
PROGRAM_OPTIONAL = ("external_name", "base_program", "required_programs", "excludes_programs")
PROGRAM_KEYS = frozenset((*PROGRAM_REQUIRED, *PROGRAM_OPTIONAL, *PROGRAM_TEXT_FIELDS))


class PayloadError(ValueError):
    """A payload that can't be applied. `problems` lists every reason, in payload order."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("; ".join(problems))


@dataclass(frozen=True)
class ProgramFields:
    """The program row and its English text. Written on every apply."""

    name_abbreviated: str
    legal_status_required: tuple[str, ...]
    value_format: Optional[str]
    year: Optional[str]
    has_calculator: bool
    show_on_current_benefits: bool
    show_in_has_benefits_step: bool
    low_confidence: bool
    text: dict[str, str]
    external_name: Optional[str] = None
    base_program: Optional[str] = None
    required_programs: tuple[str, ...] = ()
    excludes_programs: tuple[str, ...] = ()


@dataclass(frozen=True)
class NavigatorSeed:
    """A navigator: created from these fields if it doesn't exist, otherwise only linked.

    A reference (`external_name` alone) links a navigator that must already exist.
    """

    external_name: str
    reference: bool = False
    name: str = ""
    email: str = ""
    description: str = ""
    assistance_link: str = ""
    phone_number: Optional[str] = None
    counties: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    eligibility_programs: tuple[str, ...] = ()


@dataclass(frozen=True)
class DocumentSeed:
    """A document: created from these fields if it doesn't exist, otherwise only linked."""

    external_name: str
    reference: bool = False
    text: str = ""
    link_url: str = ""
    link_text: str = ""


@dataclass(frozen=True)
class WarningSeed:
    """A warning message: created from these fields if it doesn't exist, otherwise only linked."""

    external_name: str
    reference: bool = False
    message: str = ""
    calculator: str = "_show"
    link_url: str = ""
    link_text: str = ""
    counties: tuple[str, ...] = ()
    legal_statuses: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProgramPayload:
    white_label: str
    category: Optional[str]
    program: ProgramFields
    documents: tuple[DocumentSeed, ...] = ()
    navigators: tuple[NavigatorSeed, ...] = ()
    warning_messages: tuple[WarningSeed, ...] = ()

    def as_record(self) -> dict[str, Any]:
        """The payload in the program-record form `RecordSync`'s writers read."""
        program: dict[str, Any] = {
            "name_abbreviated": self.program.name_abbreviated,
            "legal_status_required": list(self.program.legal_status_required),
            "value_format": self.program.value_format,
            "year": self.program.year,
            "has_calculator": self.program.has_calculator,
            "show_on_current_benefits": self.program.show_on_current_benefits,
            "show_in_has_benefits_step": self.program.show_in_has_benefits_step,
            "low_confidence": self.program.low_confidence,
            "base_program": self.program.base_program,
            "required_programs": list(self.program.required_programs),
            "excludes_programs": list(self.program.excludes_programs),
            **self.program.text,
        }
        if self.program.external_name is not None:
            program["external_name"] = self.program.external_name

        return {
            "white_label": {"code": self.white_label},
            "program_category": {"external_name": self.category},
            "program": program,
            "documents": [_seed_entry(seed, DOCUMENT_FIELDS) for seed in self.documents],
            "navigators": [_seed_entry(seed, NAVIGATOR_FIELDS) for seed in self.navigators],
            "warning_messages": [_seed_entry(seed, WARNING_FIELDS) for seed in self.warning_messages],
        }


# Per kind of shared row: (required text, optional text, optional lists, URL fields).
@dataclass(frozen=True)
class SeedFields:
    required: tuple[str, ...]
    optional_text: tuple[str, ...]
    lists: tuple[str, ...]
    urls: tuple[str, ...]

    @property
    def keys(self) -> frozenset[str]:
        return frozenset(("external_name", *self.required, *self.optional_text, *self.lists))


NAVIGATOR_FIELDS = SeedFields(
    required=("name", "email", "description", "assistance_link"),
    optional_text=("phone_number",),
    lists=("counties", "languages", "eligibility_programs"),
    urls=("assistance_link",),
)
DOCUMENT_FIELDS = SeedFields(required=("text",), optional_text=("link_url", "link_text"), lists=(), urls=("link_url",))
WARNING_FIELDS = SeedFields(
    required=("message",),
    optional_text=("calculator", "link_url", "link_text"),
    lists=("counties", "legal_statuses"),
    urls=("link_url",),
)


def _seed_entry(seed: Any, fields: SeedFields) -> dict[str, Any]:
    if seed.reference:
        return {"external_name": seed.external_name}
    entry: dict[str, Any] = {"external_name": seed.external_name}
    for name in (*fields.required, *fields.optional_text):
        entry[name] = getattr(seed, name)
    for name in fields.lists:
        entry[name] = list(getattr(seed, name))
    return entry


def parse_payload(data: Any) -> ProgramPayload:
    """Check a payload and build its typed model. Raises `PayloadError` with every problem found."""
    problems: list[str] = []
    if not isinstance(data, dict):
        raise PayloadError(["the payload is not a JSON object"])

    problems += [f"unknown top-level key '{key}'" for key in data if key not in TOP_LEVEL_KEYS]
    if "warning_message" in data:
        problems.append("use 'warning_messages' (a list), not 'warning_message'")

    white_label = data.get("white_label")
    code = white_label.get("code") if isinstance(white_label, dict) else None
    if not isinstance(white_label, dict) or set(white_label) != {"code"} or not _is_text(code):
        problems.append('\'white_label\' must be {"code": "<white label>"}')

    category_data = data.get("program_category")
    category = category_data.get("external_name") if isinstance(category_data, dict) else None
    if (
        not isinstance(category_data, dict)
        or set(category_data) != {"external_name"}
        or not (category is None or _is_text(category))
    ):
        problems.append('\'program_category\' must be {"external_name": "<category>"} or its external_name null')

    program = _parse_program(data.get("program"), problems)
    sections: dict[str, tuple[Any, ...]] = {}
    for section, fields, model in (
        ("documents", DOCUMENT_FIELDS, DocumentSeed),
        ("navigators", NAVIGATOR_FIELDS, NavigatorSeed),
        ("warning_messages", WARNING_FIELDS, WarningSeed),
    ):
        sections[section] = _parse_section(section, data.get(section, []), fields, model, problems)

    if problems:
        raise PayloadError(problems)
    assert program is not None and isinstance(code, str)
    return ProgramPayload(
        white_label=code,
        category=category,
        program=program,
        documents=sections["documents"],
        navigators=sections["navigators"],
        warning_messages=sections["warning_messages"],
    )


def _parse_program(data: Any, problems: list[str]) -> Optional[ProgramFields]:
    if not isinstance(data, dict):
        problems.append("'program' is missing or not an object")
        return None
    start = len(problems)

    if "active" in data:
        problems.append("program.active isn't a payload field: a program is switched on or off in the admin")
    problems += [f"unknown program key '{key}'" for key in data if key not in PROGRAM_KEYS and key != "active"]
    missing = [key for key in (*PROGRAM_REQUIRED, *PROGRAM_TEXT_FIELDS) if key not in data]
    if missing:
        problems.append(f"program is missing {', '.join(missing)}")

    if "name_abbreviated" in data and not _is_text(data["name_abbreviated"]):
        problems.append("program.name_abbreviated must be a non-empty string")
    for name in PROGRAM_TEXT_FIELDS:
        if name in data and not isinstance(data[name], str):
            problems.append(f"program.{name} must be a string")
    for name in PROGRAM_URL_FIELDS:
        if isinstance(data.get(name), str) and data[name] and not _is_url(data[name]):
            problems.append(f"program.{name} '{data[name]}' isn't an http(s) URL")
    for name in PROGRAM_FLAGS:
        if name in data and not isinstance(data[name], bool):
            problems.append(f"program.{name} must be true or false")
    for name in ("legal_status_required", "required_programs", "excludes_programs"):
        if name in data and not _is_text_list(data[name]):
            problems.append(f"program.{name} must be a list of strings")
    if "year" in data and not (data["year"] is None or _is_text(data["year"])):
        problems.append('program.year must be a string, such as "2025", or null')
    if "external_name" in data and not _is_text(data["external_name"]):
        problems.append("program.external_name must be a non-empty string when present")

    value_formats = [value for value, _ in Program.VALUE_FORMAT_CHOICES]
    if "value_format" in data and data["value_format"] not in value_formats:
        allowed = ", ".join("null" if value is None else value for value in value_formats)
        problems.append(f"program.value_format must be one of {allowed}")
    base_program = data.get("base_program")
    if base_program is not None and base_program not in BaseProgram.values:
        problems.append(f"program.base_program '{base_program}' is not a BaseProgram value")

    if len(problems) > start:
        return None
    return ProgramFields(
        name_abbreviated=data["name_abbreviated"],
        legal_status_required=tuple(data["legal_status_required"]),
        value_format=data["value_format"],
        year=data["year"],
        has_calculator=data["has_calculator"],
        show_on_current_benefits=data["show_on_current_benefits"],
        show_in_has_benefits_step=data["show_in_has_benefits_step"],
        low_confidence=data["low_confidence"],
        text={name: data[name] for name in PROGRAM_TEXT_FIELDS},
        external_name=data.get("external_name"),
        base_program=base_program,
        required_programs=tuple(data.get("required_programs", [])),
        excludes_programs=tuple(data.get("excludes_programs", [])),
    )


def _parse_section(section: str, entries: Any, fields: SeedFields, model: type, problems: list[str]) -> tuple[Any, ...]:
    if not isinstance(entries, list):
        problems.append(f"'{section}' must be a list")
        return ()
    seeds = []
    seen: set[str] = set()
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict) or not _is_text(entry.get("external_name")):
            problems.append(f"{section}[{i}] has no 'external_name'")
            continue
        name = entry["external_name"]
        where = f"{section}[{i}] ({name})"
        start = len(problems)
        if name in seen:
            problems.append(f"{where} is listed twice")
        seen.add(name)
        problems += [f"{where}: unknown key '{key}'" for key in entry if key not in fields.keys]

        if set(entry) == {"external_name"}:
            if len(problems) == start:
                seeds.append(model(external_name=name, reference=True))
            continue

        missing = [key for key in fields.required if key not in entry]
        if missing:
            problems.append(
                f"{where} is missing {', '.join(missing)}. List only 'external_name' to link an existing row, "
                f"or give every required field so it can be created."
            )
        for key in (*fields.required, *fields.optional_text):
            value = entry.get(key)
            if key in entry and not (isinstance(value, str) or (key == "phone_number" and value is None)):
                problems.append(f"{where}: {key} must be a string")
        for key in fields.urls:
            value = entry.get(key)
            if isinstance(value, str) and value and not _is_url(value):
                problems.append(f"{where}: {key} '{value}' isn't an http(s) URL")
        for key in fields.lists:
            if key in entry and not _is_text_list(entry[key]):
                problems.append(f"{where}: {key} must be a list of strings")

        if len(problems) == start:
            values = {key: entry[key] for key in (*fields.required, *fields.optional_text) if key in entry}
            values.update({key: tuple(entry[key]) for key in fields.lists if key in entry})
            seeds.append(model(external_name=name, **values))
    return tuple(seeds)


def _is_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_text_list(value: Any) -> bool:
    return isinstance(value, list) and all(_is_text(item) for item in value)


def _is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)

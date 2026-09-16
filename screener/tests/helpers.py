"""
Shared fixtures for tests that exercise Screen.has_benefit() — which reads from
the CurrentBenefit join table. Use seed_program() to create the Program row a
join-table lookup will need, then write CurrentBenefit rows directly (or via the
`current_benefits: [...]` serializer payload) for the screen under test.
"""

from django.conf import settings

from programs.models import County, Document, Program, WarningMessage
from screener.models import WhiteLabel


def seed_program(white_label: WhiteLabel, *name_abbreviateds: str, base_program: str | None = None) -> None:
    """Create one or more Programs (with required Translation FKs) so the
    join-table read path can resolve `program__name_abbreviated=name`. Thin
    wrapper around the canonical `Program.objects.new_program` manager method.

    `new_program` leaves `base_program` unset, so pass `base_program=` when the code
    under test resolves variants structurally (e.g. `has_base_benefit`)."""
    for name in name_abbreviateds:
        program = Program.objects.new_program(white_label.code, name)
        if base_program is not None:
            program.base_program = base_program
            program.save()


def _set_default_text(translation, text: str) -> None:
    """Write a parler Translation's text in the DEFAULT language, explicitly.

    `Translation.objects.add_translation` creates a row per supported language and
    leaves parler's active language on whichever it wrote last (currently 'ht'), so
    assigning `.text` straight after it silently lands in that language instead of
    English — and the assistant context, which resolves through the screen language
    then falls back to `settings.LANGUAGE_CODE`, reads back "".
    """
    translation.set_current_language(settings.LANGUAGE_CODE)
    translation.text = text
    translation.save()


def seed_document(program: Program, external_name: str, text: str) -> Document:
    """Attach a Document to `program` with its `text` translation filled in.

    `Document.objects.new_document` creates the three Translation rows with text="",
    which the assistant context treats as "no value" — so callers that want the
    document to actually appear have to set the text. This does both.

    `link_url` and `link_text` are deliberately left blank: the assistant must never
    receive a document URL, and a test asserting that is stronger when the row it's
    reading from has one. Pass them explicitly on the returned object when a test
    needs them populated.
    """
    document = Document.objects.new_document(program.white_label.code, external_name)
    _set_default_text(document.text, text)
    program.documents.add(document)
    return document


def seed_warning(
    program: Program,
    calculator: str,
    message: str,
    *,
    external_name: str | None = None,
    county_names: tuple[str, ...] = (),
) -> WarningMessage:
    """Attach a WarningMessage driven by `calculator` to `program`.

    Same translation caveat as `seed_document`. `county_names` creates the County rows
    and links them, which is how `WarningCalculator.county_eligible` is gated — an
    empty tuple means "all counties", matching the model's `county_names` property.
    """
    warning = WarningMessage.objects.new_warning(
        program.white_label.code, calculator, external_name=external_name or calculator
    )
    _set_default_text(warning.message, message)
    for county_name in county_names:
        county, _ = County.objects.get_or_create(white_label=program.white_label, name=county_name)
        warning.counties.add(county)
    warning.programs.add(program)
    return warning

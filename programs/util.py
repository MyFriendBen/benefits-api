from typing import Any, Iterable, NamedTuple


class MalformedValue(NamedTuple):
    """A screener field holding a value we can't compute with, as opposed to no value.

    Kept structured so the reporter can group Sentry events by field rather than by a
    message embedding the value, which would open one issue per screen.
    """

    field: str
    value: Any
    detail: str

    def describe(self) -> str:
        return f"{self.field}={self.value!r} ({self.detail})"


class Dependencies(set):
    """Screener fields unusable for a screen. A calculator declaring one is skipped.

    A field is unusable either because it was never answered (null: ordinary partial input,
    quiet) or because it holds a value we can't compute with (a defect, recorded in
    `malformed` so `eligibility_results` can report it).
    """

    def __init__(self, *args: Iterable[str]) -> None:
        super().__init__(*args)
        self.malformed: list[MalformedValue] = []

    def has(self, *iter):
        for dependency in iter:
            if dependency in self:
                return True

        return False

    def report_malformed(self, field: str, value: Any, detail: str) -> None:
        """Record why `field` is unusable. Callers still `add()` the dependency name."""
        self.malformed.append(MalformedValue(field, value, detail))

    def update(self, *others: Iterable[str]) -> None:
        """Union the others in, keeping their malformed-value detail.

        Overridden rather than offered as a separate method so the aggregation in
        `Screen.missing_fields()` can't drop the detail by calling the usual one.
        """
        for other in others:
            super().update(other)
            self.malformed.extend(getattr(other, "malformed", ()))


class DependencyError(Exception):
    def __init__(self):
        super().__init__("Missing at least dependency")


class UnregisteredCalculatorError(DependencyError):
    """A program row whose name has no calculator registered under it.

    The calculator was deleted from the code, or the row was imported ahead of it. A
    subclass of `DependencyError` so every results loop that already drops a program it
    cannot calculate drops this one too, instead of failing the whole page on a `KeyError`.
    """

    def __init__(self, white_label_code: str, name_abbreviated: str):
        super().__init__()
        self.white_label_code = white_label_code
        self.name_abbreviated = name_abbreviated


class UpstreamAbsentError(DependencyError):
    """A gate read a program that was not calculated.

    A subclass rather than a separate exception because every existing handler catches
    `DependencyError` and should keep catching this — the program drops out either way.
    The distinction is for reporting: a missing screener field means the household was
    never asked, while an absent upstream means something upstream of us failed, and
    `EligibilitySnapshot.dropped_programs` records which.
    """

    def __init__(self, program_code: str):
        self.program_code = program_code
        Exception.__init__(self, f"{program_code} has not been calculated")

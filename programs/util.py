from typing import Any, NamedTuple


class MalformedValue(NamedTuple):
    """One screener field that holds a present-but-unusable value.

    Kept structured rather than pre-formatted so the reporter can group Sentry events by
    `field` (one issue per kind of corruption) instead of by a message string that
    embeds the value (one issue per screen).
    """

    field: str
    value: Any
    detail: str

    def describe(self) -> str:
        return f"{self.field}={self.value!r} ({self.detail})"


class Dependencies(set):
    """The set of screener field names that are unusable for a given screen, and so
    gate any calculator declaring them (see `ProgramCalculator.can_calc`).

    A field lands here for one of two reasons, which `malformed` distinguishes:
      - it was never answered (null) — ordinary partial-screen input, expected and quiet;
      - it holds a value we can't compute with (blank string, unrecognized frequency) —
        data corruption or serializer drift, recorded in `malformed` so the caller can
        report it loudly and flag the results as incomplete.
    """

    def __init__(self, *args):
        super().__init__(*args)
        # Present-but-unusable values, for Sentry. See MalformedValue.
        self.malformed: list[MalformedValue] = []

    def has(self, *iter):
        for dependency in iter:
            if dependency in self:
                return True

        return False

    def report_malformed(self, field: str, value, detail: str) -> None:
        """Record that `field` is unusable because of the value it holds rather than
        because it is missing. Callers still `add()` the field name separately — this
        only carries the diagnostic detail."""
        self.malformed.append(MalformedValue(field, value, detail))

    def update(self, *others) -> None:
        """Union other iterables in, carrying any malformed-value details along.

        Overridden rather than offered as a separate `merge()` so the obvious method is
        also the correct one — nested detail can't be dropped by reaching for `update()`
        out of habit. Plain sets/iterables have no `malformed`, which is fine.
        """
        for other in others:
            super().update(other)
            self.malformed.extend(getattr(other, "malformed", ()))


class DependencyError(Exception):
    def __init__(self):
        super().__init__("Missing at least dependency")


class ProgramConfigurationError(Exception):
    """A program is missing configuration it cannot be calculated without (an unset
    `year`, for example).

    Distinct from `DependencyError`, which means the *screen* didn't supply something:
    this is our own data being wrong, so it is a defect that should be reported loudly.
    Calculators that broadly degrade on failure must re-raise it rather than swallow it,
    so it reaches the reporting handler in `eligibility_results`.
    """

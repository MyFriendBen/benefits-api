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
        # Human-readable descriptors of present-but-unusable values, for Sentry.
        self.malformed: list[str] = []

    def has(self, *iter):
        for dependency in iter:
            if dependency in self:
                return True

        return False

    def report_malformed(self, field: str, value, detail: str) -> None:
        """Record that `field` is unusable because of the value it holds rather than
        because it is missing. Callers still `add()` the field name separately — this
        only carries the diagnostic detail."""
        self.malformed.append(f"{field}={value!r} ({detail})")

    def merge(self, other: "Dependencies") -> None:
        """Union another Dependencies in, carrying its malformed-value details along.
        Use instead of `update()` so nested detail isn't dropped on the way up."""
        self.update(other)
        self.malformed.extend(getattr(other, "malformed", ()))


class DependencyError(Exception):
    def __init__(self):
        super().__init__("Missing at least dependency")

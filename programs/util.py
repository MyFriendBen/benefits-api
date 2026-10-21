class Dependencies(set):
    def has(self, *iter):
        for dependency in iter:
            if dependency in self:
                return True

        return False


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

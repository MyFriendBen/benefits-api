class Dependencies(set):
    def has(self, *iter):
        for dependency in iter:
            if dependency in self:
                return True

        return False


class DependencyError(Exception):
    def __init__(self):
        super().__init__("Missing at least dependency")


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

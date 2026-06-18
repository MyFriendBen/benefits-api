class Dependencies(set):
    def has(self, *iter) -> bool:
        for dependency in iter:
            if dependency in self:
                return True

        return False


class DependencyError(Exception):
    def __init__(self) -> None:
        super().__init__("Missing at least dependency")

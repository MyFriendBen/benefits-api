from ..base import UrgentNeedFunction
from programs.programs.shared.household import needs_child_development_help


class CommunitySupportLine(UrgentNeedFunction):
    dependencies = ["age"]
    max_age = 21

    def eligible(self) -> bool:
        return needs_child_development_help(self.screen, self.max_age)

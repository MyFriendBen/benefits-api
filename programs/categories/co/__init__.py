from programs.categories.co.caps import HealthCareCategoryCap, PreschoolCategoryCap
from ..base import ProgramCategoryCapCalculator

co_category_cap_calculators: dict[str, type[ProgramCategoryCapCalculator]] = {
    "co_preschool": PreschoolCategoryCap,
    "co_health_care": HealthCareCategoryCap,
}

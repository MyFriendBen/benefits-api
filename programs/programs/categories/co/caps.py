from programs.programs.categories.base import CategoryCap, ProgramCategoryCapCalculator


class PreschoolCategoryCap(ProgramCategoryCapCalculator):
    static_caps = [CategoryCap(["dpp", "upk", "co_head_start", "cccap"], cap=8_640, member_cap=True)]


class HealthCareCategoryCap(ProgramCategoryCapCalculator):
    max_caps = [CategoryCap(["cfhc", "awd_medicaid", "cwd_medicaid"], member_cap=True)]

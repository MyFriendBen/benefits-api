"""KS Medicaid."""

from programs.programs.cross_white_label.medicaid.base import Medicaid
import programs.framework.pe_dependencies as dependency


class KsKanCare(Medicaid):
    """KanCare is Kansas's Medicaid program (subclass of the federal ``medicaid`` calculator).

    Kansas has not adopted ACA adult expansion, so PE returns ineligible for
    non-disabled, non-pregnant, childless adults under 65 at any income.

    KS-specific inputs added on top of the federal Medicaid set:

    - ``MeetsSsiDisabilityCriteriaDependency`` / ``IsBlindDependency`` map the screener's
      disability, long-term-disability, SSDI, and visual-impairment signals to PE's
      SSI-criterion inputs (leaving the SGA earnings test intact). Without them,
      disabled/blind applicants would wrongly return ineligible.
    """

    program_code = "ks_medicaid"

    pe_inputs = [
        *Medicaid.pe_inputs,
        dependency.member.MeetsSsiDisabilityCriteriaDependency,
        dependency.member.IsBlindDependency,
        dependency.household.KsStateCodeDependency,
    ]

    # KHI / Kansas Action for Children FY2023 KS Medicaid & CHIP per-enrollee
    # spending by group, monthly (annual figure returned = value * 12):
    #   MAGI groups  -> $3,644/yr  -> $304/mo
    #   aged (65+)   -> $20,511/yr -> $1,709/mo
    #   disabled     -> $32,459/yr -> $2,705/mo
    medicaid_categories = {
        "NONE": 0,
        "ADULT": 304,
        "INFANT": 304,
        "YOUNG_CHILD": 304,
        "OLDER_CHILD": 304,
        "PREGNANT": 304,
        "YOUNG_ADULT": 304,
        "PARENT": 304,
        "SSI_RECIPIENT": 2705,
        "AGED": 1709,
        "DISABLED": 2705,
    }

"""NC Medicaid."""

from programs.programs.cross_white_label.medicaid.base import Medicaid
import programs.framework.pe_dependencies as dependency


class NcMedicaid(Medicaid):
    program_code = "nc_medicaid"
    pe_inputs = [
        *Medicaid.pe_inputs,
        # PolicyEngine needs these to classify a member as SSI-disabled or blind, which is what
        # gates the aged/blind/disabled Medicaid pathway. Declared here rather than relied on from
        # a sibling program: PolicyEngine inputs are pooled per request, but SSI is computed in our
        # own code and SNAP can be removed by a referrer, so no other NC program is guaranteed to
        # send them; a request without them resolves is_optional_senior_or_disabled_for_medicaid
        # to False and returns $0 for a disabled applicant. Mirrors MoHealthNet. Both only ever
        # widen eligibility - they feed an OR.
        dependency.member.MeetsSsiDisabilityCriteriaDependency,
        dependency.member.IsBlindDependency,
        dependency.household.NcStateCodeDependency,
    ]

    medicaid_categories = {
        "NONE": 0,
        "ADULT": 512,  # * 12 = 6146,  Medicaid Expansion Adults
        "INFANT": 372,  # * 12 = 4464,  Medicaid for Children
        "YOUNG_CHILD": 372,  # * 12 = 4464,  Medicaid for Children
        "OLDER_CHILD": 372,  # * 12 = 4464,  Medicaid for Children
        "PREGNANT": 1045,  # * 12 = 12536, Medicaid for Pregnant Women
        "YOUNG_ADULT": 512,  # * 12 = 6146,  Medicaid Expansion Adults
        "PARENT": 512,  # * 12 = 6146,  Medicaid Expansion Parents
        "SSI_RECIPIENT": 1519,  # * 12 = 18227,  Medicaid Expansion Parents
        "AGED": 1086,  # * 12 = 13035, Medicaid for the Aged
        "DISABLED": 1519,  # * 12 = 18227, Medicaid for the Disabled
    }

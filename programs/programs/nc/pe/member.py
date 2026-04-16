import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.federal.pe.member import Medicaid
from programs.programs.federal.pe.member import Wic
from programs.programs.federal.pe.tax import Aca


class NcMedicaid(Medicaid):
    pe_inputs = [
        *Medicaid.pe_inputs,
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


class NcWic(Wic):
    wic_categories = {
        "NONE": 0,
        "INFANT": 60,
        "CHILD": 60,
        "PREGNANT": 60,
        "POSTPARTUM": 60,
        "BREASTFEEDING": 60,
    }
    pe_inputs = [
        *Wic.pe_inputs,
        dependency.household.NcStateCodeDependency,
    ]


class NcAca(Aca):
    pe_name = "aca_ptc"
    pe_inputs = [
        *Aca.pe_inputs,
        dependency.household.NcStateCodeDependency,
    ]

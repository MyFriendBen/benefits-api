from programs.programs.white_labels.cesn.utility_assistance import CesnGasUtilityAssistance


class EnergyCalculatorNaturalGasBillAssistance(CesnGasUtilityAssistance):
    program_code = "cesn_cngba"
    gates_on_any = (
        "cesn_leap",
        "cesn_eoc",
        "cesn_cowap",
    )
    gas_providers = ["co-colorado-natural-gas"]

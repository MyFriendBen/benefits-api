from programs.programs.white_labels.cesn.utility_assistance import CesnGasUtilityAssistance


class EnergyCalculatorGasAffordabilityXcel(CesnGasUtilityAssistance):
    program_code = "cesn_xcelgap"
    gates_on_any = (
        "cesn_leap",
        "cesn_eoc",
        "cesn_cowap",
    )
    gas_providers = ["co-xcel-energy-gas"]

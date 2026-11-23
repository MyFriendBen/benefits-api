from programs.programs.white_labels.cesn.utility_assistance import CesnGasUtilityAssistance


class EnergyCalculatorGasAffordabilityBlackHills(CesnGasUtilityAssistance):
    program_code = "cesn_bhgap"
    gates_on_any = (
        "cesn_leap",
        "cesn_eoc",
        "cesn_cowap",
        "cesn_care",
    )
    gas_providers = ["co-black-hills-energy-gas"]

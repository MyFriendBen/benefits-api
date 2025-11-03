from programs.programs.calc import ProgramCalculator
from .affordable_residential_energy.calculator import AffordableResidentialEnergy
from .electric_affordability_black_hills.calculator import (
    EnergyCalculatorElectricityAffordabilityBlackHills,
)
from .electric_affordability_xcel.calculator import (
    EnergyCalculatorElectricityAffordabilityXcel,
)
from .emergency_assistance.calculator import EnergyCalculatorEmergencyAssistance
from .energy_assistance.calculator import EnergyCalculatorEnergyAssistance
from .energy_ebt.calculator import EnergyCalculatorEnergyEbt
from .energy_outreach.calculator import EnergyCalculatorEnergyOutreach
from .energy_outreach_crisis_intervention.calculator import (
    EnergyCalculatorEnergyOutreachCrisisIntervention,
)
from .energy_outreach_solar.calculator import EnergyOutreachSolar
from .gas_affordability_black_hills.calculator import (
    EnergyCalculatorGasAffordabilityBlackHills,
)
from .gas_affordability_xcel.calculator import EnergyCalculatorGasAffordabilityXcel
from .home_efficiency_assistance_program.calculator import (
    EnergyCalculatorHomeEfficiencyAssistance,
)
from .medical_certification.calculator import EnergyCalculatorMedicalCertification
from .medical_exemption.calculator import EnergyCalculatorMedicalExemption
from .natural_gas_bill_assistance.calculator import (
    EnergyCalculatorNaturalGasBillAssistance,
)
from .percentage_of_income_payment_plan.calculator import (
    EnergyCalculatorPercentageOfIncomePaymentPlan,
)
from .property_credit_rebate.calculator import EnergyCalculatorPropertyCreditRebate
from .utility_bill_pay.calculator import EnergyCalculatorUtilityBillPay
from .vehicle_exchange.calculator import EnergyCalculatorVehicleExchange
from .weatherization_assistance.calculator import (
    EnergyCalculatorWeatherizationAssistance,
)
from programs.programs.co.energy_calculator.energy_ebt.calculator import EnergyCalculatorEnergyEbt
from programs.programs.co.energy_calculator.assistance_programs.project_cope.calculator import (
    EnergyCalculatorProjectCOPE,
)


co_energy_calculators: dict[str, type[ProgramCalculator]] = {
    "co_energy_calculator_care": AffordableResidentialEnergy,
    "co_energy_calculator_eocs": EnergyOutreachSolar,
    "co_energy_calculator_leap": EnergyCalculatorEnergyAssistance,
    "co_energy_calculator_ubp": EnergyCalculatorUtilityBillPay,
    "co_energy_calculator_cpcr": EnergyCalculatorPropertyCreditRebate,
    "co_energy_calculator_eoc": EnergyCalculatorEnergyOutreach,
    "co_energy_calculator_ea": EnergyCalculatorEmergencyAssistance,
    "co_energy_calculator_cowap": EnergyCalculatorWeatherizationAssistance,
    "co_energy_calculator_eoccip": EnergyCalculatorEnergyOutreachCrisisIntervention,
    "co_energy_calculator_xcelgap": EnergyCalculatorGasAffordabilityXcel,
    "co_energy_calculator_xceleap": EnergyCalculatorElectricityAffordabilityXcel,
    "co_energy_calculator_bhgap": EnergyCalculatorGasAffordabilityBlackHills,
    "co_energy_calculator_bheap": EnergyCalculatorElectricityAffordabilityBlackHills,
    "co_energy_calculator_cngba": EnergyCalculatorNaturalGasBillAssistance,
    "co_energy_calculator_poipp": EnergyCalculatorPercentageOfIncomePaymentPlan,
    "co_energy_calculator_energy_ebt": EnergyCalculatorEnergyEbt,
    "co_energy_calculator_energy_vec": EnergyCalculatorVehicleExchange,
    "co_energy_calculator_energy_mep": EnergyCalculatorMedicalExemption,
    "co_energy_calculator_mcp": EnergyCalculatorMedicalCertification,
    "co_energy_calculator_cope": EnergyCalculatorProjectCOPE,
}

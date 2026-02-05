from programs.programs.calc import ProgramCalculator
from .affordable_residential_energy.calculator import EnergyCalculatorAffordableResidentialEnergy
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
from .energy_outreach_solar.calculator import EnergyCalculatorEnergyOutreachSolar
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
from .assistance_programs.project_cope.calculator import (
    EnergyCalculatorProjectCOPE,
)

cesn_calculators: dict[str, type[ProgramCalculator]] = {
    "cesn_care": EnergyCalculatorAffordableResidentialEnergy,
    "cesn_eocs": EnergyCalculatorEnergyOutreachSolar,
    "cesn_leap": EnergyCalculatorEnergyAssistance,
    "cesn_ubp": EnergyCalculatorUtilityBillPay,
    "cesn_cpcr": EnergyCalculatorPropertyCreditRebate,
    "cesn_eoc": EnergyCalculatorEnergyOutreach,
    "cesn_ea": EnergyCalculatorEmergencyAssistance,
    "cesn_cowap": EnergyCalculatorWeatherizationAssistance,
    "cesn_eoccip": EnergyCalculatorEnergyOutreachCrisisIntervention,
    "cesn_xcelgap": EnergyCalculatorGasAffordabilityXcel,
    "cesn_xceleap": EnergyCalculatorElectricityAffordabilityXcel,
    "cesn_bhgap": EnergyCalculatorGasAffordabilityBlackHills,
    "cesn_bheap": EnergyCalculatorElectricityAffordabilityBlackHills,
    "cesn_cngba": EnergyCalculatorNaturalGasBillAssistance,
    "cesn_poipp": EnergyCalculatorPercentageOfIncomePaymentPlan,
    "cesn_energy_ebt": EnergyCalculatorEnergyEbt,
    "cesn_energy_vec": EnergyCalculatorVehicleExchange,
    "cesn_energy_mep": EnergyCalculatorMedicalExemption,
    "cesn_mcp": EnergyCalculatorMedicalCertification,
    "cesn_cope": EnergyCalculatorProjectCOPE,
    "cesn_heap": EnergyCalculatorHomeEfficiencyAssistance,
}

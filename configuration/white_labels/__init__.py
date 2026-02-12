from ._default import DefaultConfigurationData
from .base import ConfigurationData
from .co import CoConfigurationData
from .il import IlConfigurationData
from .ma import MaConfigurationData
from .nc import NcConfigurationData
from .tx import TxConfigurationData
from configuration.white_labels.co_energy_calculator import (
    CoEnergyCalculatorConfigurationData,
)

white_label_config: dict[str, ConfigurationData] = {
    "_default": DefaultConfigurationData,
    "co": CoConfigurationData,
    "co_energy_calculator": CoEnergyCalculatorConfigurationData,
    "il": IlConfigurationData,
    "ma": MaConfigurationData,
    "nc": NcConfigurationData,
    "tx": TxConfigurationData,
}

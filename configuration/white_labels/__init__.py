from ._default import DefaultConfigurationData
from .base import ConfigurationData
from .co import CoConfigurationData
from .il import IlConfigurationData
from .ma import MaConfigurationData
from .nc import NcConfigurationData
from .tx import TxConfigurationData
from configuration.white_labels.cesn import (
    CesnConfigurationData,
)

white_label_config: dict[str, ConfigurationData] = {
    "_default": DefaultConfigurationData,
    "co": CoConfigurationData,
    "cesn": CesnConfigurationData,
    "il": IlConfigurationData,
    "ma": MaConfigurationData,
    "nc": NcConfigurationData,
    "tx": TxConfigurationData,
}

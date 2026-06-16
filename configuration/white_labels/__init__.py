from ._default import DefaultConfigurationData
from .base import ConfigurationData
from .co import CoConfigurationData
from .il import IlConfigurationData
from .ks import KsConfigurationData
from .ma import MaConfigurationData
from .nc import NcConfigurationData
from .tx import TxConfigurationData
from .wa import WaConfigurationData
from configuration.white_labels.cesn import (
    CesnConfigurationData,
)

white_label_config: dict[str, ConfigurationData] = {
    "_default": DefaultConfigurationData,
    "co": CoConfigurationData,
    "cesn": CesnConfigurationData,
    "il": IlConfigurationData,
    "ks": KsConfigurationData,
    "ma": MaConfigurationData,
    "nc": NcConfigurationData,
    "tx": TxConfigurationData,
    "wa": WaConfigurationData,
}

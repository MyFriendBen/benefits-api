"""Throttle rates that can be changed without a deploy.

A rate read from the environment is one typo away from breaking the endpoint it
protects: DRF parses the rate on every request, and a value it cannot parse raises
there. Raising at startup instead would take the whole API down on a bad config
change. So a blank or unreadable value falls back to the default in code, with a
warning in the logs.
"""

import logging

from decouple import config

logger = logging.getLogger(__name__)

# The periods DRF's SimpleRateThrottle.parse_rate understands, by first letter.
_PERIODS = ("s", "m", "h", "d")


def is_valid_rate(rate: str) -> bool:
    """Whether DRF can parse `rate`: a whole number, a slash, and a period ("5/hour")."""
    number, slash, period = rate.partition("/")
    return number.isdigit() and slash == "/" and period[:1] in _PERIODS


def throttle_rate(name: str, default: str) -> str:
    """The rate in environment variable `name`, or `default` when unset or unusable."""
    rate = str(config(name, default=default)).strip()
    if is_valid_rate(rate):
        return rate
    if rate:
        logger.warning("%s is not a throttle rate like '5/hour'; using the default %s", name, default)
    return default

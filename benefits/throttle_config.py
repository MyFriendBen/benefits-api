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
_PERIODS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_rate(rate: str) -> tuple[int, int]:
    """(requests, seconds) for a rate like "5/hour", read exactly as DRF reads it.

    Raises ValueError for anything DRF's own parser would choke on: more or fewer
    than one slash ("5/hour/x"), a count that isn't plain ASCII digits ("²/hour",
    "-5/hour"), or an unknown period ("5/fortnight").
    """
    number, period = rate.split("/")
    if not (number.isascii() and number.isdigit()) or period[:1] not in _PERIODS:
        raise ValueError(f"Not a throttle rate: {rate!r}")
    return int(number), _PERIODS[period[0]]


def is_valid_rate(rate: str) -> bool:
    """Whether `rate` is a throttle rate DRF can parse, like "5/hour"."""
    try:
        parse_rate(rate)
    except ValueError:
        return False
    return True


def throttle_rate(name: str, default: str) -> str:
    """The rate in environment variable `name`, or `default` when unset or unusable."""
    rate = str(config(name, default=default)).strip()
    if is_valid_rate(rate):
        return rate
    if rate:
        logger.warning("%s is not a throttle rate like '5/hour'; using the default %s", name, default)
    return default

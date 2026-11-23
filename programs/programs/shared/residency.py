"""Where the household lives."""

from screener.models import Screen


def lives_in(screen: Screen, place: str) -> bool:
    """
    Whether the screen's location is ``place``, compared exactly.

    The location is read from ``screen.county``, which holds whatever the white label's
    ZIP map emits. That is a county for most white labels, but MA's map emits a city or
    town ("Cambridge"), so ``place`` must use the same form as the map.
    """
    return screen.county == place

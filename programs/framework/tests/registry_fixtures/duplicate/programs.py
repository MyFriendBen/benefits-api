from programs.framework.tests.registry_fixtures.base import FixtureBase


class FirstClaimant(FixtureBase):
    name_abbreviated = "fixture_duplicate"


class SecondClaimant(FixtureBase):
    """Claims a key another class already claims."""

    name_abbreviated = "fixture_duplicate"

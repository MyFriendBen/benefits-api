from programs.framework.tests.registry_fixtures.base import FixtureBase


class FirstClaimant(FixtureBase):
    program_code = "fixture_duplicate"


class SecondClaimant(FixtureBase):
    """Claims a key another class already claims."""

    program_code = "fixture_duplicate"

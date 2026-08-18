from programs.framework.tests.registry_fixtures.base import FixtureBase


class FixtureParent(FixtureBase):
    name_abbreviated = "fixture_parent"


class FixtureChildWithNoKeyOfItsOwn(FixtureParent):
    """Inherits `fixture_parent` without declaring a key, so must not register."""

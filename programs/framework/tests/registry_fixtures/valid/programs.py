from programs.framework.tests.registry_fixtures.base import FixtureBase


class FixtureParent(FixtureBase):
    program_code = "fixture_parent"


class FixtureChildWithNoKeyOfItsOwn(FixtureParent, abstract=True):
    """Inherits ``fixture_parent`` without declaring a key.

    Marked abstract so this fixture is about the inherited-key rule rather than the
    declare-something rule: an inherited key must not register the subclass, or the
    parent's key would silently point at the child.
    """

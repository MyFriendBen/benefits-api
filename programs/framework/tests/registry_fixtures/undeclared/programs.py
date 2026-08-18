from programs.framework.tests.registry_fixtures.base import FixtureBase


class DeclaredNothing(FixtureBase):
    """Neither a key nor abstract=True — the mistake build() must reject."""

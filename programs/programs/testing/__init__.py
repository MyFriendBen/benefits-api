"""Scaffolding shared by program tests.

Fixtures and base classes used from more than one family or white label. Nothing
here asserts behavior — a test case belongs with the program or family it covers.

The registry walks this package, so the name must not start with ``test_``: that
prefix marks a module as test code and excludes it from the walk, which would make
these unimportable from the tests that need them.
"""

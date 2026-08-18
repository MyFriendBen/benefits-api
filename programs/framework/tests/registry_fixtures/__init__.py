"""Throwaway packages used only by test_registry.py.

Kept outside `programs/programs/` so the real registry never sees them, and named
`registry_fixtures` rather than `tests` so discovery's test-module skip does not
hide them from the tests that need them.
"""

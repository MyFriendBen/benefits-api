"""Fixtures and base classes for program tests.

Household builders, a received-benefit fixture, and the base test cases that
program tests inherit. Nothing here asserts behavior — a test case belongs with
the program or family it covers.

The registry walks ``programs.programs``, and a module named ``tests`` or prefixed
``test_`` is excluded from that walk as test code. These have to stay importable,
so the name avoids both.
"""

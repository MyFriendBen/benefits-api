"""
Atomic helpers shared by calculators and urgent needs.

Each function answers one question from the screen, member or values it is handed and
returns the answer, so it can be tested without building a calculator. Calculators call
these from their own methods rather than inheriting them: the method stays on the
calculator, so a white label that needs a different rule overrides that one method and
everyone else keeps the shared behavior.

A helper belongs here once a second, unrelated calculator needs it. Logic that only one
family shares stays with that family (``cross_white_label/<family>/``), and a whole
calculator shared by a family is a base class there, not a helper here.
"""

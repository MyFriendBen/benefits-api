"""
Guard: production code must not read the stored `HouseholdMember.age` column.

`age` is written once, when the member is created, and never refreshed. A household that
comes back to its results after a birthday is judged on last year's age, and a frozen
screen drifts away from the reference date it was pinned to. `calc_age()` derives the age
from `birth_year_month` at `Screen.get_reference_date()` and falls back to the stored
column only when there is no birth date, so it is right in every case the column is.

Allowed:
- `calc_age()` and `fraction_age()` in `screener/models.py`, which are the fallback.
- A class constant named `age` read through its own class (`UniversalPreschool.age`), or
  through `self`/`cls` inside a class that assigns a literal to `age` in its body or
  inherits one. Constant classes are collected across the whole repo, so a subclass in
  another module is recognised.

Also caught: ORM reads of the column, `filter(age__gte=18)` and `values("age")`.

Not caught: an `age` read through `getattr(member, "age")`. Nothing does that today.
"""

import ast
from pathlib import Path

from django.test import SimpleTestCase

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

SKIPPED_DIRS = {"migrations", "tests", "__pycache__"}

#: Code-generation templates with `{{placeholder}}` syntax; not valid Python.
SKIPPED_FILES = {"configuration/white_labels/_template.py"}

#: (repo-relative path, enclosing function) pairs allowed to read the stored column.
FALLBACKS = {
    ("screener/models.py", "calc_age"),
    ("screener/models.py", "fraction_age"),
}


#: Queryset methods whose keyword arguments are field lookups (`age=`, `age__gte=`).
LOOKUP_METHODS = {"filter", "exclude", "get", "get_or_create", "update_or_create"}

#: Callables whose string arguments name fields (`values("age")`, `F("age")`).
FIELD_NAME_CALLS = {"values", "values_list", "order_by", "only", "defer", "distinct", "F"}


def _is_age_field(name: str) -> bool:
    return name == "age" or name.startswith("age__")


def _class_index(tree: ast.Module) -> dict[str, tuple[set[str], bool]]:
    """Each class's base names, and whether it assigns a literal to `age` in its own body."""
    index = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        bases = {base.id if isinstance(base, ast.Name) else getattr(base, "attr", "") for base in node.bases}
        has_constant = False
        for stmt in node.body:
            targets = stmt.targets if isinstance(stmt, ast.Assign) else [getattr(stmt, "target", None)]
            value = getattr(stmt, "value", None)
            if isinstance(value, ast.Constant) and any(isinstance(t, ast.Name) and t.id == "age" for t in targets):
                has_constant = True
        index[node.name] = (bases, has_constant)
    return index


def _class_constant_names(index: dict[str, tuple[set[str], bool]]) -> set[str]:
    """Classes with a literal `age`, in their own body or inherited from a base."""
    names = {name for name, (_, has_constant) in index.items() if has_constant}
    changed = True
    while changed:
        changed = False
        for name, (bases, _) in index.items():
            if name not in names and bases & names:
                names.add(name)
                changed = True
    return names


class _AgeReadFinder(ast.NodeVisitor):
    def __init__(self, relative_path: str, constant_classes: set[str]):
        self.relative_path = relative_path
        self.constant_classes = constant_classes
        self.functions: list[str] = []
        self.classes: list[str] = []
        self.offenders: list[int] = []

    def visit_ClassDef(self, node):
        self.classes.append(node.name)
        self.generic_visit(node)
        self.classes.pop()

    def visit_FunctionDef(self, node):
        self.functions.append(node.name)
        self.generic_visit(node)
        self.functions.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Attribute(self, node):
        if node.attr == "age" and isinstance(node.ctx, ast.Load) and not self._allowed(node):
            self.offenders.append(node.lineno)
        self.generic_visit(node)

    def visit_Call(self, node):
        name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", None)
        if name in LOOKUP_METHODS and any(kw.arg and _is_age_field(kw.arg) for kw in node.keywords):
            self.offenders.append(node.lineno)
        elif name in FIELD_NAME_CALLS and any(
            isinstance(arg, ast.Constant) and isinstance(arg.value, str) and _is_age_field(arg.value.lstrip("-"))
            for arg in node.args
        ):
            self.offenders.append(node.lineno)
        self.generic_visit(node)

    def _allowed(self, node: ast.Attribute) -> bool:
        if self.functions and (self.relative_path, self.functions[-1]) in FALLBACKS:
            return True
        if not isinstance(node.value, ast.Name):
            return False
        owner = node.value.id
        if owner in self.constant_classes:
            return True
        return owner in ("self", "cls") and bool(self.classes) and self.classes[-1] in self.constant_classes


def _static_age_reads(source: str, relative_path: str = "<source>", constant_classes=None) -> list[int]:
    """Line numbers of every read of an `age` attribute that isn't allowed.

    `constant_classes` defaults to the classes in `source` itself; the production scan
    passes the repo-wide set so inherited constants are recognised across modules.
    """
    tree = ast.parse(source, filename=relative_path)
    if constant_classes is None:
        constant_classes = _class_constant_names(_class_index(tree))
    finder = _AgeReadFinder(relative_path, constant_classes)
    finder.visit(tree)
    return finder.offenders


def _production_files():
    """Every non-test module under the repo's top-level packages.

    Walks packages (directories with an `__init__.py`), not the whole checkout, so local
    scratch directories and virtualenvs are never scanned.
    """
    packages = sorted(p.parent for p in REPO_ROOT.glob("*/__init__.py"))
    for path in sorted(path for package in packages for path in package.rglob("*.py")):
        relative = path.relative_to(REPO_ROOT)
        if SKIPPED_DIRS.intersection(relative.parts):
            continue
        if path.name.startswith("test_") or path.name in ("tests.py", "conftest.py"):
            continue
        if relative.as_posix() in SKIPPED_FILES:
            continue
        yield path, relative.as_posix()


class NoStaticAgeReadsTests(SimpleTestCase):
    def test_production_code_reads_age_through_calc_age(self):
        sources = [(path.read_text(), relative) for path, relative in _production_files()]
        index = {}
        for source, relative in sources:
            index.update(_class_index(ast.parse(source, filename=relative)))
        constant_classes = _class_constant_names(index)

        offenders = []
        for source, relative in sources:
            for lineno in _static_age_reads(source, relative, constant_classes):
                offenders.append(f"{relative}:{lineno}")

        self.assertEqual(
            offenders,
            [],
            "The stored HouseholdMember.age is set once when the member is created and goes "
            "stale after a birthday. Use member.calc_age(), which works from birth_year_month "
            "at the screen's reference date. For an age as of a tax or claim year, use "
            "member.age_at_end_of_year(year):\n  " + "\n  ".join(offenders),
        )

    def test_detects_a_member_age_read(self):
        """The walker finds what it's looking for, so it can't silently stop working if the
        ast shape assumptions drift."""
        self.assertEqual(_static_age_reads("def f(member):\n    return member.age >= 18\n"), [2])

    def test_detects_a_chained_read(self):
        self.assertEqual(_static_age_reads("def f(screen):\n    return screen.get_head().age\n"), [2])

    def test_detects_self_age_on_a_model(self):
        """HouseholdMember's own methods read `self.age`; its `age` is a field, not a literal."""
        source = (
            "class HouseholdMember:\n"
            "    age = models.PositiveIntegerField()\n"
            "    def is_adult(self):\n"
            "        return self.age >= 18\n"
        )
        self.assertEqual(_static_age_reads(source, "screener/models.py"), [4])

    def test_allows_the_calc_age_fallback(self):
        source = "class HouseholdMember:\n    def calc_age(self):\n        return self.age\n"
        self.assertEqual(_static_age_reads(source, "screener/models.py"), [])

    def test_fallback_is_scoped_to_screener_models(self):
        """A function called calc_age anywhere else gets no pass."""
        source = "class Other:\n    def calc_age(self, member):\n        return member.age\n"
        self.assertEqual(_static_age_reads(source, "programs/other.py"), [3])

    def test_allows_a_class_constant(self):
        source = (
            "class UniversalPreschool:\n"
            "    age = 4\n"
            "    def f(self, member):\n"
            "        return member.calc_age() == UniversalPreschool.age or member.calc_age() == self.age\n"
        )
        self.assertEqual(_static_age_reads(source), [])

    def test_allows_an_inherited_class_constant(self):
        source = (
            "class UniversalPreschool:\n"
            "    age = 4\n"
            "class Denver(UniversalPreschool):\n"
            "    def f(self):\n"
            "        return self.age\n"
        )
        self.assertEqual(_static_age_reads(source), [])

    def test_allows_a_constant_inherited_from_another_module(self):
        index = _class_index(ast.parse("class UniversalPreschool:\n    age = 4\n"))
        index.update(_class_index(ast.parse("class Denver(base.UniversalPreschool):\n    pass\n")))
        source = "class Denver(base.UniversalPreschool):\n    def f(self):\n        return self.age\n"
        self.assertEqual(_static_age_reads(source, constant_classes=_class_constant_names(index)), [])

    def test_detects_self_age_without_an_inherited_constant(self):
        source = "class Denver(Base):\n    def f(self):\n        return self.age\n"
        self.assertEqual(_static_age_reads(source), [3])

    def test_detects_orm_lookups(self):
        self.assertEqual(_static_age_reads("qs.filter(age__gte=18)\n"), [1])
        self.assertEqual(_static_age_reads("qs.exclude(age=None)\n"), [1])
        self.assertEqual(_static_age_reads("qs.values_list('id', 'age')\n"), [1])
        self.assertEqual(_static_age_reads("qs.order_by('-age')\n"), [1])
        self.assertEqual(_static_age_reads("qs.annotate(x=F('age'))\n"), [1])

    def test_ignores_orm_writes_and_other_fields(self):
        source = "HouseholdMember(age=3)\nqs.filter(birth_year_month__lte=d).values('min_age')\n"
        self.assertEqual(_static_age_reads(source), [])

    def test_ignores_writes_and_calc_age(self):
        source = "def f(member):\n    member.age = 3\n    return member.calc_age(), member.birth_year_month\n"
        self.assertEqual(_static_age_reads(source), [])

"""Tests for the check_migrations command that CI runs before migrate.

Each test installs a throwaway app, built in a temp directory, next to the project's own apps, so the
command also checks the whole repository every time.
"""

from io import StringIO
from pathlib import Path
from typing import Callable, Optional

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from pytest_django.fixtures import SettingsWrapper

REQUIRED = "models.IntegerField()"
NULLABLE = "models.IntegerField(null=True)"


def models_source(field_name: str = "size", field: str = REQUIRED) -> str:
    """models.py for an app holding one model, Probe, with one field besides its id."""
    return f"""\
from django.db import models


class Probe(models.Model):
    {field_name} = {field}
"""


def initial_migration(field_name: Optional[str] = "size", field: str = REQUIRED) -> str:
    """0001_initial creating Probe with the given field, or with only its id when field_name is None."""
    fields = '("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),'
    if field_name is not None:
        fields += f"\n                ({field_name!r}, {field}),"
    return f"""\
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="Probe",
            fields=[
                {fields}
            ],
        ),
    ]
"""


EMPTY_ON_INITIAL = """\
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("{app}", "0001_initial")]
    operations = []
"""


InstallApp = Callable[..., None]


@pytest.fixture
def install_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, settings: SettingsWrapper) -> InstallApp:
    """Install a throwaway app with the given models.py and migration files (None: no migrations package)."""

    def install(name: str, migrations: Optional[dict[str, str]], models: str = models_source()) -> None:
        package = tmp_path / name
        package.mkdir()
        (package / "__init__.py").write_text("")
        (package / "models.py").write_text(models)
        if migrations is not None:
            (package / "migrations").mkdir()
            (package / "migrations" / "__init__.py").write_text("")
            for filename, source in migrations.items():
                (package / "migrations" / filename).write_text(source.replace("{app}", name))
        monkeypatch.syspath_prepend(str(tmp_path))
        # pytest runs with --nomigrations, which hides every app's migration files.
        settings.MIGRATION_MODULES = {}
        settings.INSTALLED_APPS = [*settings.INSTALLED_APPS, name]

    return install


def run_check() -> str:
    out = StringIO()
    call_command("check_migrations", stdout=out, stderr=out)
    return out.getvalue()


@pytest.mark.django_db
def test_passes_when_every_app_is_migrated(install_app: InstallApp) -> None:
    install_app("check_migrations_clean", {"0001_initial.py": initial_migration()})

    assert "none missing, none conflicting" in run_check()


@pytest.mark.django_db
def test_fails_on_an_app_with_models_and_no_migrations_package(install_app: InstallApp) -> None:
    # makemigrations given no app labels passes this app; the command must not.
    install_app("check_migrations_new_app", None)

    with pytest.raises(CommandError, match="have no migration"):
        run_check()


@pytest.mark.django_db
def test_fails_on_a_new_required_field_without_a_migration(install_app: InstallApp) -> None:
    # Not interactive, makemigrations exits 3 here, not 1: a required field has no default to fill
    # existing rows with.
    install_app("check_migrations_missing_field", {"0001_initial.py": initial_migration(field_name=None)})

    with pytest.raises(CommandError, match="have no migration"):
        run_check()


@pytest.mark.django_db
def test_fails_on_two_migrations_on_one_parent(install_app: InstallApp) -> None:
    install_app(
        "check_migrations_conflict",
        {"0001_initial.py": initial_migration(), "0002_first.py": EMPTY_ON_INITIAL, "0002_second.py": EMPTY_ON_INITIAL},
    )

    with pytest.raises(CommandError, match="Conflicting migrations detected"):
        run_check()


@pytest.mark.django_db
def test_fails_on_a_renamed_required_field_without_a_migration(install_app: InstallApp) -> None:
    # Interactive, makemigrations would ask "Was probe.size renamed to probe.amount? [y/N]" and crash
    # with no one to answer. Not interactive, the required field it adds exits 3.
    install_app(
        "check_migrations_required_rename",
        {"0001_initial.py": initial_migration()},
        models=models_source(field_name="amount"),
    )

    with pytest.raises(CommandError, match="have no migration"):
        run_check()


@pytest.mark.django_db
def test_fails_on_a_renamed_nullable_field_without_a_migration(install_app: InstallApp) -> None:
    # Not interactive, the rename is listed as a remove plus an add, and --check exits 1.
    install_app(
        "check_migrations_nullable_rename",
        {"0001_initial.py": initial_migration(field=NULLABLE)},
        models=models_source(field_name="amount", field=NULLABLE),
    )

    with pytest.raises(CommandError, match="have no migration"):
        run_check()

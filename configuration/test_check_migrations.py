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

MODELS = """\
from django.db import models


class Probe(models.Model):
    size = models.IntegerField()
"""

INITIAL = """\
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="Probe",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("size", models.IntegerField()),
            ],
        ),
    ]
"""

INITIAL_WITHOUT_SIZE = """\
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="Probe",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
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


InstallApp = Callable[[str, Optional[dict[str, str]]], None]


@pytest.fixture
def install_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, settings: SettingsWrapper) -> InstallApp:
    """Install a throwaway app holding one model, with the given migration files (None: no migrations package)."""

    def install(name: str, migrations: Optional[dict[str, str]]) -> None:
        package = tmp_path / name
        package.mkdir()
        (package / "__init__.py").write_text("")
        (package / "models.py").write_text(MODELS)
        if migrations is not None:
            (package / "migrations").mkdir()
            (package / "migrations" / "__init__.py").write_text("")
            for filename, source in migrations.items():
                (package / "migrations" / filename).write_text(source.format(app=name))
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
    install_app("check_migrations_clean", {"0001_initial.py": INITIAL})

    assert "none missing, none conflicting" in run_check()


@pytest.mark.django_db
def test_fails_on_an_app_with_models_and_no_migrations_package(install_app: InstallApp) -> None:
    # makemigrations given no app labels passes this app; the command must not.
    install_app("check_migrations_new_app", None)

    with pytest.raises(CommandError, match="have no migration"):
        run_check()


@pytest.mark.django_db
def test_fails_on_a_model_change_without_a_migration(install_app: InstallApp) -> None:
    install_app("check_migrations_missing_field", {"0001_initial.py": INITIAL_WITHOUT_SIZE})

    with pytest.raises(CommandError, match="have no migration"):
        run_check()


@pytest.mark.django_db
def test_fails_on_two_migrations_on_one_parent(install_app: InstallApp) -> None:
    install_app(
        "check_migrations_conflict",
        {"0001_initial.py": INITIAL, "0002_first.py": EMPTY_ON_INITIAL, "0002_second.py": EMPTY_ON_INITIAL},
    )

    with pytest.raises(CommandError, match="Conflicting migrations detected"):
        run_check()

"""Tests for the check_migrations command that CI runs before migrate.

makemigrations is mocked: these tests check the call the command makes and how it reports the result,
not Django's own detection. Installing a throwaway app instead would mean overriding INSTALLED_APPS,
and reloading the app registry makes unfold swap in an empty admin site that breaks admin URLs for
every later test in the same process.
"""

from io import StringIO
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest
from django.apps import apps
from django.core.management import call_command
from django.core.management.base import CommandError

MAKEMIGRATIONS = "configuration.management.commands.check_migrations.call_command"


def run_check(side_effect: Optional[BaseException] = None) -> tuple[MagicMock, str]:
    out = StringIO()
    with patch(MAKEMIGRATIONS, side_effect=side_effect) as makemigrations:
        call_command("check_migrations", stdout=out, stderr=out)
    return makemigrations, out.getvalue()


def test_checks_every_installed_app_without_prompting() -> None:
    makemigrations, output = run_check()

    args, kwargs = makemigrations.call_args
    assert args[0] == "makemigrations"
    # Without labels, makemigrations skips an app that has models but no migrations package.
    assert list(args[1:]) == [app_config.label for app_config in apps.get_app_configs()]
    assert kwargs["check"] is True
    assert kwargs["dry_run"] is True
    # Interactive, a rename asks "Was x renamed to y? [y/N]", which crashes CI with EOFError.
    assert kwargs["interactive"] is False
    assert "none missing, none conflicting" in output


@pytest.mark.parametrize(
    "code",
    [
        pytest.param(1, id="model change listed by --check"),
        pytest.param(3, id="new non-nullable field with no default"),
    ],
)
def test_reports_a_missing_migration_with_the_fix(code: int) -> None:
    with pytest.raises(CommandError, match="have no migration") as error:
        run_check(SystemExit(code))

    assert "makemigrations <app_label>" in str(error.value)


def test_passes_any_other_exit_through() -> None:
    with pytest.raises(SystemExit) as exit_:
        run_check(SystemExit(2))

    assert exit_.value.code == 2


def test_passes_a_conflict_through_unchanged() -> None:
    conflict = CommandError("Conflicting migrations detected; multiple leaf nodes in the migration graph")

    with pytest.raises(CommandError, match="Conflicting migrations detected"):
        run_check(conflict)

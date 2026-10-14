import os
import subprocess
import sys
import types

import pytest


class DummySettings:
    def __init__(self, redis_url=None, debug=True):
        self.REDIS_URL = redis_url
        self.DEBUG = debug


def _import_command():
    # Import the command module to make its Command class available
    # Ensure minimal django scaffolding exists so importing the command
    # doesn't require a full Django installation in this test environment.
    if "django" not in sys.modules:
        django = types.ModuleType("django")
        django.conf = types.ModuleType("django.conf")
        django.conf.settings = types.SimpleNamespace()
        django.contrib = types.ModuleType("django.contrib")
        django.contrib.staticfiles = types.ModuleType("django.contrib.staticfiles")
        django.contrib.staticfiles.management = types.ModuleType("django.contrib.staticfiles.management")
        django.contrib.staticfiles.management.commands = types.ModuleType(
            "django.contrib.staticfiles.management.commands"
        )

        rs_mod = types.ModuleType("django.contrib.staticfiles.management.commands.runserver")

        class BaseCommand:
            def __init__(self):
                pass

            def add_arguments(self, parser):
                pass

            def handle(self, *a, **k):
                pass

        rs_mod.Command = BaseCommand

        sys.modules["django"] = django
        sys.modules["django.conf"] = django.conf
        sys.modules["django.contrib"] = django.contrib
        sys.modules["django.contrib.staticfiles"] = django.contrib.staticfiles
        sys.modules["django.contrib.staticfiles.management"] = django.contrib.staticfiles.management
        sys.modules["django.contrib.staticfiles.management.commands"] = django.contrib.staticfiles.management.commands
        sys.modules["django.contrib.staticfiles.management.commands.runserver"] = rs_mod

    from screener.management.commands.runserver import Command

    return Command


def test_no_redis_url(monkeypatch, capsys):
    Command = _import_command()
    settings = DummySettings(redis_url=None, debug=True)
    monkeypatch.setattr("screener.management.commands.runserver.settings", settings)

    cmd = Command()
    # Should simply return without attempting to find redis-server
    cmd._maybe_start_redis({})


def test_debug_false_prevents_start(monkeypatch):
    Command = _import_command()
    settings = DummySettings(redis_url="redis://localhost:6379", debug=False)
    monkeypatch.setattr("screener.management.commands.runserver.settings", settings)

    cmd = Command()
    # Should return early
    cmd._maybe_start_redis({})


def test_no_redis_binary_prints_hint(monkeypatch, capsys):
    Command = _import_command()
    settings = DummySettings(redis_url="redis://localhost:6379", debug=True)
    monkeypatch.setattr("screener.management.commands.runserver.settings", settings)

    # Ensure the test proceeds to binary discovery even if a real Redis is
    # listening on localhost:6379 on the developer machine.
    def fake_create_connection(addr, timeout=1):
        raise OSError()

    monkeypatch.setattr("socket.create_connection", fake_create_connection)
    monkeypatch.setattr("shutil.which", lambda _name: None)

    cmd = Command()
    cmd._maybe_start_redis({})
    captured = capsys.readouterr()
    assert "redis-server not found on PATH; skipping auto-start" in captured.out


def test_port_already_listening(monkeypatch):
    Command = _import_command()
    settings = DummySettings(redis_url="redis://localhost:9999", debug=True)
    monkeypatch.setattr("screener.management.commands.runserver.settings", settings)

    # Simulate socket.create_connection succeeding (port in use)
    class DummySocket:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_create_connection(addr, timeout=1):
        return DummySocket()

    monkeypatch.setattr("socket.create_connection", fake_create_connection)
    monkeypatch.setattr("shutil.which", lambda _name: "/usr/bin/redis-server")

    cmd = Command()
    # Should detect listener and return without attempting spawn
    cmd._maybe_start_redis({})


def test_spawn_redis_when_available(monkeypatch, tmp_path, capsys):
    Command = _import_command()
    settings = DummySettings(redis_url="redis://localhost:6380", debug=True)
    monkeypatch.setattr("screener.management.commands.runserver.settings", settings)

    # No socket connection (port free)
    def fake_create_connection(addr, timeout=1):
        raise OSError()

    monkeypatch.setattr("socket.create_connection", fake_create_connection)
    # redis-server exists
    monkeypatch.setattr("shutil.which", lambda _name: "/usr/bin/redis-server")

    # record the args passed to subprocess.check_call
    called = {}

    def fake_check_call(args):
        called["args"] = args
        return 0

    # Patch the subprocess.check_call used by the runserver module so the
    # fake is invoked regardless of the test environment.
    monkeypatch.setattr("screener.management.commands.runserver.subprocess.check_call", fake_check_call)
    # Also patch the top-level subprocess.check_call as a fallback for test
    # environments that may reference it directly.
    monkeypatch.setattr("subprocess.check_call", fake_check_call)

    cmd = Command()
    cmd._maybe_start_redis({})

    assert "args" in called
    assert "--maxmemory" in called["args"]
    assert "25mb" in called["args"]
    assert "--maxmemory-policy" in called["args"]
    assert "allkeys-lru" in called["args"]


def test_spawn_redis_in_wsl_when_on_windows(monkeypatch, tmp_path, capsys):
    Command = _import_command()
    settings = DummySettings(redis_url="redis://localhost:6381", debug=True)
    monkeypatch.setattr("screener.management.commands.runserver.settings", settings)

    # No socket connection (port free)
    def fake_create_connection(addr, timeout=1):
        raise OSError()

    monkeypatch.setattr("socket.create_connection", fake_create_connection)

    # Simulate redis-server not on PATH but wsl exists
    # simulate no native redis-server but wsl exists
    def fake_which(name):
        if name == "wsl":
            return r"C:\Windows\System32\wsl.exe"
        return None

    monkeypatch.setattr("shutil.which", fake_which)

    # Force platform to Windows
    monkeypatch.setattr("platform.system", lambda: "Windows")

    called = {}

    def fake_check_call(args):
        called["args"] = args
        return 0

    # Patch the subprocess.check_call used by the runserver module so the
    # fake is invoked regardless of the test environment.
    monkeypatch.setattr("screener.management.commands.runserver.subprocess.check_call", fake_check_call)
    # Also patch the top-level subprocess.check_call as a fallback for test
    # environments that may reference it directly.
    monkeypatch.setattr("subprocess.check_call", fake_check_call)

    cmd = Command()
    cmd._maybe_start_redis({})

    assert "args" in called
    # For WSL we expect wsl to be invoked (first arg)
    assert any("wsl" in str(a).lower() for a in called["args"])

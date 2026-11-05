import pytest


@pytest.fixture(autouse=True)
def _auto_start_redis_enabled(monkeypatch):
    """Ensure AUTO_START_REDIS is enabled for these tests regardless of the
    developer's local environment/opt-out, since _maybe_start_redis returns
    early (before reaching any of the Popen/check_call code these tests
    assert on) when AUTO_START_REDIS is falsy."""
    monkeypatch.setenv("AUTO_START_REDIS", "true")


class DummySettings:
    def __init__(self, redis_url=None, debug=True):
        self.REDIS_URL = redis_url
        self.DEBUG = debug


class _DummySocket:
    """Stands in for the context manager socket.create_connection returns."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _import_command():
    # pytest-django (see pytest.ini: DJANGO_SETTINGS_MODULE) already runs
    # django.setup() before test collection, so the real Django package is
    # available here same as in every other test module in this project.
    from screener.management.commands.runserver import Command

    return Command


def _forbid_spawn(monkeypatch):
    """Patch check_call/Popen to fail the test if the command ever reaches
    the point of actually trying to spawn a redis-server. Tests for the
    early-exit guards use this to prove the guard actually triggers, rather
    than just asserting no exception was raised."""

    def fail_check_call(args):
        raise AssertionError(f"should not attempt to spawn redis-server, got check_call({args!r})")

    def fail_popen(args, **kwargs):
        raise AssertionError(f"should not attempt to spawn redis-server, got Popen({args!r})")

    monkeypatch.setattr("screener.management.commands.runserver.subprocess.check_call", fail_check_call)
    monkeypatch.setattr("screener.management.commands.runserver.subprocess.Popen", fail_popen)


def test_no_redis_url(monkeypatch):
    Command = _import_command()
    settings = DummySettings(redis_url=None, debug=True)
    monkeypatch.setattr("screener.management.commands.runserver.settings", settings)
    _forbid_spawn(monkeypatch)

    def fail_create_connection(addr, timeout=1):
        raise AssertionError("should bail out before checking the port at all")

    monkeypatch.setattr("socket.create_connection", fail_create_connection)

    cmd = Command()
    # Should simply return without attempting to find or spawn redis-server
    cmd._maybe_start_redis({})


def test_no_redis_option_prevents_start(monkeypatch):
    Command = _import_command()
    settings = DummySettings(redis_url="redis://localhost:6379", debug=True)
    monkeypatch.setattr("screener.management.commands.runserver.settings", settings)
    _forbid_spawn(monkeypatch)

    def fail_create_connection(addr, timeout=1):
        raise AssertionError("should bail out before checking the port at all")

    monkeypatch.setattr("socket.create_connection", fail_create_connection)

    cmd = Command()
    cmd._maybe_start_redis({"no_redis": True})


def test_auto_start_redis_env_false_prevents_start(monkeypatch):
    Command = _import_command()
    settings = DummySettings(redis_url="redis://localhost:6379", debug=True)
    monkeypatch.setattr("screener.management.commands.runserver.settings", settings)
    monkeypatch.setenv("AUTO_START_REDIS", "false")
    _forbid_spawn(monkeypatch)

    def fail_create_connection(addr, timeout=1):
        raise AssertionError("should bail out before checking the port at all")

    monkeypatch.setattr("socket.create_connection", fail_create_connection)

    cmd = Command()
    cmd._maybe_start_redis({})


def test_non_loopback_host_prevents_start(monkeypatch):
    Command = _import_command()
    settings = DummySettings(redis_url="redis://example.com:6379", debug=True)
    monkeypatch.setattr("screener.management.commands.runserver.settings", settings)
    _forbid_spawn(monkeypatch)

    def fail_create_connection(addr, timeout=1):
        raise AssertionError("should bail out before checking the port at all")

    monkeypatch.setattr("socket.create_connection", fail_create_connection)

    cmd = Command()
    cmd._maybe_start_redis({})


def test_non_redis_scheme_prevents_start(monkeypatch):
    """A unix socket URL has no hostname/port to speak of; parsed.hostname
    would otherwise silently fall back to "localhost" and start an unrelated
    TCP redis-server that the app never talks to."""
    Command = _import_command()
    settings = DummySettings(redis_url="unix:///var/run/redis/redis.sock", debug=True)
    monkeypatch.setattr("screener.management.commands.runserver.settings", settings)
    _forbid_spawn(monkeypatch)

    def fail_create_connection(addr, timeout=1):
        raise AssertionError("should bail out before checking the port at all")

    monkeypatch.setattr("socket.create_connection", fail_create_connection)

    cmd = Command()
    cmd._maybe_start_redis({})


def test_handle_skips_auto_start_when_run_main_true(monkeypatch):
    """The autoreloader runs manage.py twice; _maybe_start_redis must only
    run in the parent process (RUN_MAIN unset), not the reloaded child."""
    Command = _import_command()
    monkeypatch.setenv("RUN_MAIN", "true")

    def fail_maybe_start(self, options):
        raise AssertionError("_maybe_start_redis should not run when RUN_MAIN=true")

    monkeypatch.setattr(Command, "_maybe_start_redis", fail_maybe_start)
    monkeypatch.setattr(
        "django.contrib.staticfiles.management.commands.runserver.Command.handle",
        lambda self, *a, **k: "super-called",
    )

    cmd = Command()
    assert cmd.handle() == "super-called"


def test_handle_calls_super_even_when_auto_start_raises(monkeypatch, capsys):
    """A broken auto-start attempt must never prevent runserver itself from
    starting."""
    Command = _import_command()
    monkeypatch.delenv("RUN_MAIN", raising=False)

    def raise_maybe_start(self, options):
        raise RuntimeError("boom")

    monkeypatch.setattr(Command, "_maybe_start_redis", raise_maybe_start)
    monkeypatch.setattr(
        "django.contrib.staticfiles.management.commands.runserver.Command.handle",
        lambda self, *a, **k: "super-called",
    )

    cmd = Command()
    assert cmd.handle() == "super-called"

    captured = capsys.readouterr()
    assert "boom" in captured.err
    assert "Continuing without redis" in captured.err


def test_runserver_command_is_registered_as_screener_override():
    """Guard against app ordering regressions that would silently let
    django.contrib.staticfiles' own runserver load instead of this one
    (which would break admin static files without raising any error)."""
    from django.core.management import get_commands

    assert get_commands()["runserver"] == "screener"


def test_tls_scheme_prevents_start(monkeypatch, capsys):
    Command = _import_command()
    settings = DummySettings(redis_url="rediss://localhost:6379", debug=True)
    monkeypatch.setattr("screener.management.commands.runserver.settings", settings)
    _forbid_spawn(monkeypatch)

    def fail_create_connection(addr, timeout=1):
        raise AssertionError("should bail out before checking the port at all")

    monkeypatch.setattr("socket.create_connection", fail_create_connection)

    cmd = Command()
    cmd._maybe_start_redis({})

    captured = capsys.readouterr()
    assert "rediss" in captured.out
    assert "skipping auto-start" in captured.out


def test_credentials_in_url_prevent_start(monkeypatch, capsys):
    Command = _import_command()
    settings = DummySettings(redis_url="redis://user:pass@localhost:6379", debug=True)
    monkeypatch.setattr("screener.management.commands.runserver.settings", settings)
    _forbid_spawn(monkeypatch)

    def fail_create_connection(addr, timeout=1):
        raise AssertionError("should bail out before checking the port at all")

    monkeypatch.setattr("socket.create_connection", fail_create_connection)

    cmd = Command()
    cmd._maybe_start_redis({})

    captured = capsys.readouterr()
    assert "credentials" in captured.out
    assert "skipping auto-start" in captured.out


def test_query_param_credentials_prevent_start(monkeypatch, capsys):
    Command = _import_command()
    settings = DummySettings(redis_url="redis://localhost:6379/0?password=secret", debug=True)
    monkeypatch.setattr("screener.management.commands.runserver.settings", settings)
    _forbid_spawn(monkeypatch)

    def fail_create_connection(addr, timeout=1):
        raise AssertionError("should bail out before checking the port at all")

    monkeypatch.setattr("socket.create_connection", fail_create_connection)

    cmd = Command()
    cmd._maybe_start_redis({})

    captured = capsys.readouterr()
    assert "credentials" in captured.out
    assert "skipping auto-start" in captured.out


def test_debug_false_prevents_start(monkeypatch):
    Command = _import_command()
    settings = DummySettings(redis_url="redis://localhost:6379", debug=False)
    monkeypatch.setattr("screener.management.commands.runserver.settings", settings)
    _forbid_spawn(monkeypatch)

    def fail_create_connection(addr, timeout=1):
        raise AssertionError("should bail out before checking the port at all")

    monkeypatch.setattr("socket.create_connection", fail_create_connection)

    cmd = Command()
    # Should return early
    cmd._maybe_start_redis({})


def test_no_redis_binary_prints_hint(monkeypatch, capsys):
    Command = _import_command()
    settings = DummySettings(redis_url="redis://localhost:6379", debug=True)
    monkeypatch.setattr("screener.management.commands.runserver.settings", settings)
    _forbid_spawn(monkeypatch)
    # Avoid platform.system() internally invoking subprocess.Popen('ver') on
    # real Windows hosts, which would trip the fail_popen guard above.
    monkeypatch.setattr("platform.system", lambda: "Linux")

    # Ensure the test proceeds to binary discovery even if a real Redis is
    # listening on localhost:6379 on the developer machine.
    def fake_create_connection(addr, timeout=1):
        raise OSError()

    monkeypatch.setattr("socket.create_connection", fake_create_connection)
    monkeypatch.setattr("screener.management.commands.runserver.shutil.which", lambda _name: None)

    cmd = Command()
    cmd._maybe_start_redis({})
    captured = capsys.readouterr()
    assert "redis-server not found on PATH; skipping auto-start" in captured.err


def test_port_already_listening(monkeypatch):
    Command = _import_command()
    settings = DummySettings(redis_url="redis://localhost:9999", debug=True)
    monkeypatch.setattr("screener.management.commands.runserver.settings", settings)
    _forbid_spawn(monkeypatch)

    def fake_create_connection(addr, timeout=1):
        return _DummySocket()

    monkeypatch.setattr("socket.create_connection", fake_create_connection)

    cmd = Command()
    # Should detect listener and return without attempting spawn
    cmd._maybe_start_redis({})


def test_port_already_listening_prints_message(monkeypatch, capsys):
    Command = _import_command()
    settings = DummySettings(redis_url="redis://localhost:9999", debug=True)
    monkeypatch.setattr("screener.management.commands.runserver.settings", settings)
    _forbid_spawn(monkeypatch)

    def fake_create_connection(addr, timeout=1):
        return _DummySocket()

    monkeypatch.setattr("socket.create_connection", fake_create_connection)

    cmd = Command()
    cmd._maybe_start_redis({})

    captured = capsys.readouterr()
    assert "already running" in captured.out


def test_spawn_redis_when_available(monkeypatch, tmp_path, capsys):
    Command = _import_command()
    settings = DummySettings(redis_url="redis://localhost:6380", debug=True)
    monkeypatch.setattr("screener.management.commands.runserver.settings", settings)

    # Force the POSIX daemonize/check_call path regardless of the host OS
    # running this test (this file's CI/dev machines may be Linux or Windows).
    monkeypatch.setattr("platform.system", lambda: "Linux")

    # First call simulates the "is the port already in use" pre-check (port
    # free); every call after that simulates the post-spawn readiness probe
    # succeeding immediately so the test doesn't block on the 3s timeout.
    calls = {"count": 0}

    def fake_create_connection(addr, timeout=1):
        calls["count"] += 1
        if calls["count"] == 1:
            raise OSError()
        return _DummySocket()

    monkeypatch.setattr("socket.create_connection", fake_create_connection)
    # redis-server exists. Create a harmless dummy executable in tmp_path and
    # return its path from shutil.which so the test doesn't fail with
    # FileNotFoundError on environments that don't have /usr/bin/redis-server.
    dummy = tmp_path / "redis-server"
    dummy.write_text("#!/usr/bin/env true\n")
    # Make executable on POSIX; on Windows this is a no-op but the file still
    # exists so attempts to execute it will fail differently but not with
    # FileNotFoundError.
    try:
        dummy.chmod(0o755)
    except PermissionError:
        pass

    # Only resolve the redis-server binary itself, like the real shutil.which
    # would -- otherwise the pgrep pid-discovery lookup below would also
    # resolve to this dummy (non-executable) path and attempt to exec it.
    # The module looks up shutil.which and subprocess.check_call as
    # attributes, so patching them on the runserver module is sufficient --
    # no need for a duplicate global builtins-level patch.
    def fake_which(name):
        return str(dummy) if name == "redis-server" else None

    monkeypatch.setattr("screener.management.commands.runserver.shutil.which", fake_which)

    # record the args passed to subprocess.check_call
    called = {}

    def fake_check_call(args):
        called["args"] = args
        return 0

    monkeypatch.setattr("screener.management.commands.runserver.subprocess.check_call", fake_check_call)

    cmd = Command()
    cmd._maybe_start_redis({})

    assert "args" in called
    assert "--bind" in called["args"]
    assert "127.0.0.1" in called["args"]
    assert "-::1" in called["args"]
    assert "--maxmemory" in called["args"]
    assert "25mb" in called["args"]
    assert "--maxmemory-policy" in called["args"]
    assert "allkeys-lru" in called["args"]
    assert "--daemonize" in called["args"]

    captured = capsys.readouterr()
    assert "Started local redis-server" in captured.out


def test_spawn_redis_foreground_on_windows_native(monkeypatch, tmp_path, capsys):
    """Native (non-Memurai) Windows builds generally can't daemonize, so the
    command must run them in the foreground via Popen instead of passing
    --daemonize and trusting the process to detach itself."""
    Command = _import_command()
    settings = DummySettings(redis_url="redis://localhost:6382", debug=True)
    monkeypatch.setattr("screener.management.commands.runserver.settings", settings)

    monkeypatch.setattr("platform.system", lambda: "Windows")

    calls = {"count": 0}

    def fake_create_connection(addr, timeout=1):
        calls["count"] += 1
        if calls["count"] == 1:
            raise OSError()
        return _DummySocket()

    monkeypatch.setattr("socket.create_connection", fake_create_connection)

    dummy = tmp_path / "redis-server.exe"
    dummy.write_text("not a real binary\n")

    def fake_which(name):
        return str(dummy) if name == "redis-server" else None

    monkeypatch.setattr("screener.management.commands.runserver.shutil.which", fake_which)

    # The CREATE_NEW_PROCESS_GROUP / DETACHED_PROCESS constants only exist on
    # Windows builds of Python, but this test simulates Windows behavior
    # while actually running on whatever OS runs the test suite (e.g. Linux
    # CI), so provide them here instead of relying on the real subprocess
    # module to expose them.
    monkeypatch.setattr(
        "screener.management.commands.runserver.subprocess.CREATE_NEW_PROCESS_GROUP", 0x200, raising=False
    )
    monkeypatch.setattr("screener.management.commands.runserver.subprocess.DETACHED_PROCESS", 0x8, raising=False)

    class FakeProcess:
        pid = 4321

        def poll(self):
            return None  # still running

    popen_calls = {}

    def fake_popen(args, **kwargs):
        popen_calls["args"] = args
        popen_calls["kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.setattr("screener.management.commands.runserver.subprocess.Popen", fake_popen)

    def fail_check_call(args):
        raise AssertionError("check_call should not be used on native Windows; Popen should be used instead")

    monkeypatch.setattr("screener.management.commands.runserver.subprocess.check_call", fail_check_call)

    cmd = Command()
    cmd._maybe_start_redis({})

    assert "args" in popen_calls
    assert "--daemonize" not in popen_calls["args"]
    assert "--bind" in popen_calls["args"]
    # On Windows the child must be detached into its own process group so
    # Ctrl-C (which stops runserver) doesn't also stop this redis-server.
    assert popen_calls["kwargs"].get("creationflags")

    captured = capsys.readouterr()
    assert "Started local redis-server (PID 4321)" in captured.out


def test_spawn_redis_in_wsl_when_on_windows(monkeypatch, tmp_path, capsys):
    Command = _import_command()
    settings = DummySettings(redis_url="redis://localhost:6381", debug=True)
    monkeypatch.setattr("screener.management.commands.runserver.settings", settings)

    # First call simulates the "is the port already in use" pre-check (port
    # free); every call after that simulates the post-spawn readiness probe
    # succeeding immediately so the test doesn't block on the 3s timeout.
    calls = {"count": 0}

    def fake_create_connection(addr, timeout=1):
        calls["count"] += 1
        if calls["count"] == 1:
            raise OSError()
        return _DummySocket()

    monkeypatch.setattr("socket.create_connection", fake_create_connection)

    # Simulate redis-server not on PATH but wsl exists
    # simulate no native redis-server but wsl exists
    def fake_which(name):
        if name == "wsl":
            return r"C:\Windows\System32\wsl.exe"
        return None

    monkeypatch.setattr("screener.management.commands.runserver.shutil.which", fake_which)

    # Force platform to Windows
    monkeypatch.setattr("platform.system", lambda: "Windows")

    called = {}

    def fake_check_call(args):
        called["args"] = args
        return 0

    monkeypatch.setattr("screener.management.commands.runserver.subprocess.check_call", fake_check_call)

    cmd = Command()
    cmd._maybe_start_redis({})

    assert "args" in called
    # For WSL we expect wsl to be invoked (first arg)
    assert any("wsl" in str(a).lower() for a in called["args"])
    joined = " ".join(str(a) for a in called["args"])
    assert "--bind 127.0.0.1 -::1" in joined

    captured = capsys.readouterr()
    assert "Started local redis-server inside WSL" in captured.out

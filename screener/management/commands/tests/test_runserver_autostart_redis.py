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


def test_no_redis_url(monkeypatch, capsys):
    Command = _import_command()
    settings = DummySettings(redis_url=None, debug=True)
    monkeypatch.setattr("screener.management.commands.runserver.settings", settings)

    cmd = Command()
    # Should simply return without attempting to find redis-server
    cmd._maybe_start_redis({})


def test_tls_scheme_prevents_start(monkeypatch, capsys):
    Command = _import_command()
    settings = DummySettings(redis_url="rediss://localhost:6379", debug=True)
    monkeypatch.setattr("screener.management.commands.runserver.settings", settings)

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


def test_port_already_listening(monkeypatch, tmp_path):
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
    # Provide a harmless dummy executable so any accidental execution path
    # doesn't raise FileNotFoundError in test environments.
    dummy = tmp_path / "redis-server"
    dummy.write_text("#!/usr/bin/env true\n")
    try:
        dummy.chmod(0o755)
    except PermissionError:
        pass

    monkeypatch.setattr("shutil.which", lambda _name: str(dummy))
    monkeypatch.setattr("screener.management.commands.runserver.shutil.which", lambda _name: str(dummy))

    cmd = Command()
    # Should detect listener and return without attempting spawn
    cmd._maybe_start_redis({})


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
    def fake_which(name):
        return str(dummy) if name in ("redis-server", "redis-server.exe") else None

    monkeypatch.setattr("shutil.which", fake_which)
    monkeypatch.setattr("screener.management.commands.runserver.shutil.which", fake_which)

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
    # No Popen stub required for this test; check_call is patched.

    cmd = Command()
    cmd._maybe_start_redis({})

    assert "args" in called
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
        return str(dummy) if name in ("redis-server", "redis-server.exe") else None

    monkeypatch.setattr("shutil.which", fake_which)
    monkeypatch.setattr("screener.management.commands.runserver.shutil.which", fake_which)

    class FakeProcess:
        pid = 4321

        def poll(self):
            return None  # still running

    popen_calls = {}

    def fake_popen(args, **kwargs):
        popen_calls["args"] = args
        return FakeProcess()

    monkeypatch.setattr("screener.management.commands.runserver.subprocess.Popen", fake_popen)

    def fail_check_call(args):
        raise AssertionError("check_call should not be used on native Windows; Popen should be used instead")

    monkeypatch.setattr("screener.management.commands.runserver.subprocess.check_call", fail_check_call)

    cmd = Command()
    cmd._maybe_start_redis({})

    assert "args" in popen_calls
    assert "--daemonize" not in popen_calls["args"]

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

    monkeypatch.setattr("shutil.which", fake_which)
    monkeypatch.setattr("screener.management.commands.runserver.shutil.which", fake_which)

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
    # No Popen stub required for this test; check_call is patched.

    cmd = Command()
    cmd._maybe_start_redis({})

    assert "args" in called
    # For WSL we expect wsl to be invoked (first arg)
    assert any("wsl" in str(a).lower() for a in called["args"])

    captured = capsys.readouterr()
    assert "Started local redis-server inside WSL" in captured.out

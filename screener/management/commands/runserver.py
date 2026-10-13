from __future__ import annotations

import os
import platform
import shutil
import socket
import subprocess
import tempfile
import uuid
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.staticfiles.management.commands.runserver import (
    Command as StaticFilesRunserver,
)


class Command(StaticFilesRunserver):
    """Runserver that will attempt to auto-start a small local redis-server.

    Behavior (conservative):
    - Only runs the startup once per manage.py lifecycle (guard on RUN_MAIN)
    - Only when settings.REDIS_URL is set and points at loopback
    - Only when the configured port is not already accepting connections
    - Does nothing (prints a one-line hint) when `redis-server` is not on PATH
    - Can be opted out with --no-redis or AUTO_START_REDIS=false

    This mirrors the Heroku Redis config closely so local development sees
    the same maxmemory and eviction behaviour (25mb, allkeys-lru).
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--no-redis",
            action="store_true",
            dest="no_redis",
            help="Do not auto-start a local redis server for development.",
        )

    def handle(self, *args, **options):
        # The autoreloader runs manage.py twice; only run once in the parent
        if os.environ.get("RUN_MAIN") != "true":
            try:
                self._maybe_start_redis(options)
            except Exception as exc:  # defensive: never hard-fail runserver
                self.stdout.write(f"Warning: auto-start redis failed: {exc}. Continuing without redis.")

        return super().handle(*args, **options)

    def _maybe_start_redis(self, options: dict) -> None:
        # Explicit one-off opt-out
        if options.get("no_redis"):
            return

        # Persistent opt-out via env
        if os.environ.get("AUTO_START_REDIS", "true").lower() in ("0", "false", "no"):
            return

        # Only act when REDIS_URL is configured
        redis_url = getattr(settings, "REDIS_URL", None)
        if not redis_url:
            return

        # Only in DEBUG mode: be belt-and-braces because runserver shouldn't
        # implicitly manage services in production-like environments.
        if not getattr(settings, "DEBUG", False):
            return

        parsed = urlparse(redis_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6379

        # Only auto-start for loopback addresses
        if host not in ("127.0.0.1", "localhost", "::1"):
            return

        # If anything is already listening on the configured port, leave it alone
        try:
            with socket.create_connection((host, port), timeout=1):
                # connected -> redis is up
                return
        except OSError:
            # no connection -> we'll attempt to spawn
            pass

        # Decide how to start Redis depending on the platform and available
        # binaries. Prefer a native redis-server when present. On Windows, if
        # redis-server is not on PATH but WSL is available, try starting
        # redis-server inside WSL so developers using WSL work seamlessly.
        # Look for a native redis binary. On Windows installations this may be
        # `redis-server.exe` or Memurai (`memurai.exe`), so check a few common
        # names before falling back to WSL.
        candidates = ["redis-server", "redis-server.exe", "memurai", "memurai.exe"]
        redis_bin = None
        for c in candidates:
            p = shutil.which(c)
            if p:
                redis_bin = p
                break

        wsl_bin = shutil.which("wsl")

        if redis_bin:
            start_mode = "native"
        elif platform.system() == "Windows" and wsl_bin:
            start_mode = "wsl"
        else:
            # Print a single-line hint so it stays visible but not noisy.
            self.stdout.write(
                "redis-server not found on PATH; skipping auto-start. Install Redis or use --no-redis / AUTO_START_REDIS=false."
            )
            return

        # Prepare a small ephemeral dir for redis persistence files so we don't
        # pollute the repo. For WSL we'll create a temp dir path inside WSL's
        # /tmp using a UUID; for native we use tempfile on the host.
        if start_mode == "native":
            tmpdir = tempfile.mkdtemp(prefix="mfb-redis-")
            args = self._build_native_args(str(redis_bin), port, tmpdir)
            runner = args
        else:  # wsl
            wsl_tmp = f"/tmp/mfb-redis-{uuid.uuid4().hex}"
            # Build the redis-server command to run inside WSL. Use -- to
            # pass args to the Linux binary; prefer wsl -- <cmd> form.
            redis_cmd = " ".join(
                [
                    "redis-server",
                    "--port",
                    str(port),
                    "--maxmemory",
                    "25mb",
                    "--maxmemory-policy",
                    "allkeys-lru",
                    "--save",
                    "''",
                    "--appendonly",
                    "no",
                    "--dir",
                    wsl_tmp,
                    "--daemonize",
                    "yes",
                ]
            )
            # Ensure the tmp dir exists and then run the command inside WSL
            runner = [wsl_bin, "--", "bash", "-lc", f"mkdir -p {wsl_tmp} && {redis_cmd}"]

        try:
            subprocess.check_call(runner)
        except (OSError, subprocess.CalledProcessError) as exc:
            self.stdout.write(f"Failed to start redis-server: {exc}. Continuing without redis.")
            return

    def _build_native_args(self, redis_bin: str, port: int, tmpdir: str) -> list:
        """Return the argument list to start a native redis-server."""
        return [
            redis_bin,
            "--port",
            str(port),
            "--maxmemory",
            "25mb",
            "--maxmemory-policy",
            "allkeys-lru",
            "--save",
            "",
            "--appendonly",
            "no",
            "--dir",
            tmpdir,
            "--daemonize",
            "yes",
        ]

        pid = None
        # Try to discover the pid (best-effort, non-fatal). On POSIX use
        # pgrep; on Windows when using native redis-server we can't reliably
        # pgrep here, and for WSL we skip pid detection.
        if platform.system() != "Windows" and start_mode != "wsl":
            pgrep = shutil.which("pgrep")
            if pgrep:
                try:
                    out = subprocess.check_output(
                        [pgrep, "-f", f"redis-server.*--port {port}"],
                        stderr=subprocess.DEVNULL,
                    )
                    # take the last matched pid
                    pid = out.decode().strip().splitlines()[-1]
                except subprocess.CalledProcessError:
                    pid = None

        if pid:
            self.stdout.write(
                f"Started local redis-server (PID {pid}) on {host}:{port}. "
                f"To stop: kill {pid} or 'redis-cli -p {port} shutdown'"
            )
        else:
            self.stdout.write(
                f"Started local redis-server on {host}:{port} (pid unknown). "
                f"To stop: 'redis-cli -p {port} shutdown'"
            )

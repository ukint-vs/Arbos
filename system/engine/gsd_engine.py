from __future__ import annotations

import os
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from .base import EngineStatus


class GsdEngine:
    name = "gsd"

    def __init__(self, workdir: Path, goal_file: Path, inbox_file: Path, log_fn):
        self._workdir = workdir
        self._goal_file = goal_file
        self._inbox_file = inbox_file
        self._log = log_fn
        self._lock = threading.Lock()
        self._proc: subprocess.Popen[str] | None = None
        self._last_heartbeat: str | None = None

    def _build_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env.pop("TAU_BOT_TOKEN", None)
        return env

    def _spawn(self, continue_session: bool = False) -> None:
        gsd_cmd = ["gsd", "--continue"] if continue_session else ["gsd"]
        # Run through `script` to allocate a pseudo-TTY; GSD exits quickly without one.
        cmd = ["script", "-q", "/dev/null", *gsd_cmd]

        self._proc = subprocess.Popen(
            cmd,
            cwd=self._workdir,
            env=self._build_env(),
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        self._last_heartbeat = datetime.now(timezone.utc).isoformat()
        self._log(f"gsd engine started pid={self._proc.pid} continue={continue_session}")
        time.sleep(1.0)
        self._send_line("/gsd auto")

    def _send_line(self, line: str) -> bool:
        proc = self._proc
        if not proc or proc.poll() is not None or not proc.stdin:
            return False
        try:
            proc.stdin.write(line + "\n")
            proc.stdin.flush()
            self._last_heartbeat = datetime.now(timezone.utc).isoformat()
            return True
        except Exception:
            return False

    def start(self, goal_text: str) -> None:
        self._goal_file.parent.mkdir(parents=True, exist_ok=True)
        self._goal_file.write_text(goal_text)
        with self._lock:
            if self._proc and self._proc.poll() is None:
                self._send_line("/gsd auto")
                return
            self._spawn(continue_session=False)

    def stop(self, graceful: bool = True) -> None:
        with self._lock:
            proc = self._proc
            if not proc:
                return
            if graceful and self._send_line("/gsd stop"):
                for _ in range(15):
                    if proc.poll() is not None:
                        break
                    time.sleep(0.2)
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
            self._log("gsd engine stopped")

    def resume(self) -> None:
        with self._lock:
            if self._proc and self._proc.poll() is None:
                self._send_line("/gsd auto")
                return
            self._spawn(continue_session=True)

    def send_operator_note(self, text: str) -> None:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
        self._inbox_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._inbox_file, "a") as f:
            f.write(f"- {ts} | operator: {text}\n")
        self._last_heartbeat = datetime.now(timezone.utc).isoformat()
        self._send_line(f"/gsd discuss {text}")

    def status(self) -> EngineStatus:
        proc = self._proc
        running = bool(proc and proc.poll() is None)
        pid = proc.pid if proc else None
        mode = "auto" if running else "idle"

        detail = ""
        gsd_state = self._workdir / ".gsd" / "STATE.md"
        if gsd_state.exists():
            lines = [ln.strip() for ln in gsd_state.read_text().splitlines() if ln.strip()]
            if lines:
                detail = " | ".join(lines[:3])[:280]
        if not detail:
            detail = "gsd running" if running else "gsd not running"

        return EngineStatus(
            engine=self.name,
            running=running,
            mode=mode,
            detail=detail,
            pid=pid,
            last_heartbeat=self._last_heartbeat,
        )

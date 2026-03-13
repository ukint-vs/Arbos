from __future__ import annotations

from pathlib import Path
import threading
from datetime import datetime, timezone

from .base import EngineStatus


class ArbosEngine:
    name = "arbos"

    def __init__(
        self,
        goal_file: Path,
        inbox_file: Path,
        wake_event: threading.Event,
        status_provider,
    ):
        self._goal_file = goal_file
        self._inbox_file = inbox_file
        self._wake_event = wake_event
        self._status_provider = status_provider

    def start(self, goal_text: str) -> None:
        self._goal_file.parent.mkdir(parents=True, exist_ok=True)
        self._goal_file.write_text(goal_text)
        self._wake_event.set()

    def stop(self, graceful: bool = True) -> None:
        self._goal_file.parent.mkdir(parents=True, exist_ok=True)
        self._goal_file.write_text("")
        self._wake_event.set()

    def resume(self) -> None:
        self._wake_event.set()

    def send_operator_note(self, text: str) -> None:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
        self._inbox_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._inbox_file, "a") as f:
            f.write(f"- {ts} | operator: {text}\n")
        self._wake_event.set()

    def status(self) -> EngineStatus:
        step_count, goal_step_count, active = self._status_provider()
        detail = f"steps={step_count}, goal_steps={goal_step_count}"
        return EngineStatus(
            engine=self.name,
            running=active,
            mode="loop",
            detail=detail,
            last_heartbeat=datetime.now(timezone.utc).isoformat(),
        )

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .arbos_engine import ArbosEngine
from .base import EngineStatus
from .gsd_engine import GsdEngine


class EngineManager:
    def __init__(
        self,
        workdir: Path,
        context_dir: Path,
        engine_name: str,
        goal_file: Path,
        inbox_file: Path,
        wake_event,
        status_provider,
        log_fn,
    ):
        self._workdir = workdir
        self._context_dir = context_dir
        self._state_file = context_dir / "engine_state.json"
        self._log = log_fn

        desired = (engine_name or "gsd").strip().lower()
        if desired not in {"gsd", "arbos"}:
            desired = "gsd"

        if desired == "arbos":
            self.engine = ArbosEngine(goal_file, inbox_file, wake_event, status_provider)
        else:
            self.engine = GsdEngine(workdir, goal_file, inbox_file, log_fn)

        self.engine_name = self.engine.name
        self._write_state(self.engine.status())

    def _write_state(self, status: EngineStatus) -> None:
        self._context_dir.mkdir(parents=True, exist_ok=True)
        data = status.to_dict()
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._state_file.write_text(json.dumps(data, indent=2))

    def start(self, goal_text: str) -> None:
        self.engine.start(goal_text)
        self._write_state(self.engine.status())

    def stop(self, graceful: bool = True) -> None:
        self.engine.stop(graceful=graceful)
        self._write_state(self.engine.status())

    def resume(self) -> None:
        self.engine.resume()
        self._write_state(self.engine.status())

    def send_operator_note(self, text: str) -> None:
        self.engine.send_operator_note(text)
        self._write_state(self.engine.status())

    def status(self) -> dict:
        status = self.engine.status()
        self._write_state(status)
        return status.to_dict()

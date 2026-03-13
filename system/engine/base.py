from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Protocol, Any


@dataclass
class EngineStatus:
    engine: str
    running: bool
    mode: str
    detail: str = ""
    pid: int | None = None
    last_heartbeat: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LoopEngine(Protocol):
    name: str

    def start(self, goal_text: str) -> None:
        ...

    def stop(self, graceful: bool = True) -> None:
        ...

    def resume(self) -> None:
        ...

    def send_operator_note(self, text: str) -> None:
        ...

    def status(self) -> EngineStatus:
        ...

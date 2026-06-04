"""Progress reporting. The UI passes an `on_progress` callback; the engine emits events the
UI turns into a progress bar. `emit` tolerates a None callback (headless/scripted use)."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class ProgressEvent:
    stage: str          # "resolve" | "list" | "download" | "convert" | "index"
    current: int
    total: int
    message: str        # human-readable, safe to show ("Downloading Annual Report 2024")

    @property
    def percent(self) -> int:
        return int(self.current / self.total * 100) if self.total else 0


ProgressCallback = Optional[Callable[[ProgressEvent], None]]


def emit(cb: ProgressCallback, event: ProgressEvent) -> None:
    if cb is not None:
        cb(event)

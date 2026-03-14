from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class BaseAgentEntity:
    agent_id: str
    agent_name: str
    version: str = "v1"
    status: str = "idle"
    owner: str = "member-c"
    description: str = ""
    input_contract: dict[str, Any] = field(default_factory=dict)
    output_contract: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    last_run_at: str | None = None
    last_error: str | None = None

    def mark_running(self) -> None:
        self.status = "running"
        self.last_error = None
        self.last_run_at = _utc_now_iso()

    def mark_failed(self, message: str) -> None:
        self.status = "failed"
        self.last_error = message
        self.last_run_at = _utc_now_iso()

    def mark_completed(self) -> None:
        self.status = "completed"
        self.last_run_at = _utc_now_iso()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

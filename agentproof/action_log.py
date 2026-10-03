from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ActionLogger:
    """Write structured AgentProof action events."""

    def __init__(self, repo: Path):
        self.repo = repo
        self.log_path = repo / ".agentproof" / "actions.jsonl"

        self.log_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def record(
        self,
        action_type: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record one action event."""

        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action_type": action_type,
            "details": details or {},
        }

        with self.log_path.open(
            "a",
            encoding="utf-8",
        ) as file:
            file.write(
                json.dumps(
                    event,
                    ensure_ascii=False,
                )
                + "\n"
            )

        return event

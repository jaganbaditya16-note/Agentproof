from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_actions(repo: Path) -> list[dict[str, Any]]:
    """Load recorded AgentProof actions from actions.jsonl."""

    path = repo / ".agentproof" / "actions.jsonl"

    if not path.exists():
        return []

    actions: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid action log entry on line {line_number}: {exc}"
                ) from exc

            if not isinstance(event, dict):
                raise ValueError(
                    f"Action log entry on line {line_number} "
                    "must be a JSON object."
                )

            actions.append(event)

    return actions

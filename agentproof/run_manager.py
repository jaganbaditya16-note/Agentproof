from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class RunManager:
    """Create and manage an AgentProof verification run."""

    def __init__(self, repo: Path):
        self.repo = repo
        self.state_dir = repo / ".agentproof"
        self.state_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.current_run_path = (
            self.state_dir / "current_run.json"
        )

    def start(self) -> dict[str, Any]:
        """Start a new verification run."""

        run = {
            "run_id": str(uuid.uuid4()),
            "started_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

        with self.current_run_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                run,
                file,
                indent=2,
            )

        return run

    def current(self) -> dict[str, Any] | None:
        """Return the currently active run."""

        if not self.current_run_path.exists():
            return None

        with self.current_run_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    def finish(self) -> None:
        """Remove the active run."""

        if self.current_run_path.exists():
            self.current_run_path.unlink()

from __future__ import annotations

from pathlib import Path
from typing import Any

from agentproof.action_log import ActionLogger


class FileOperator:
    """Perform file operations while recording AgentProof events."""

    def __init__(self, repo: Path):
        self.repo = repo
        self.logger = ActionLogger(repo)

    def read_text(self, relative_path: str) -> str:
        """Read a text file and record the operation."""

        path = self.repo / relative_path

        self.logger.record(
            "FILE_READ",
            {
                "path": relative_path,
            },
        )

        return path.read_text(encoding="utf-8")

    def write_text(
        self,
        relative_path: str,
        content: str,
    ) -> None:
        """Write a text file and record the operation."""

        path = self.repo / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)

        path.write_text(
            content,
            encoding="utf-8",
        )

        self.logger.record(
            "FILE_WRITTEN",
            {
                "path": relative_path,
                "bytes": len(content.encode("utf-8")),
            },
        )

    def delete(self, relative_path: str) -> None:
        """Delete a file and record the operation."""

        path = self.repo / relative_path

        if not path.exists():
            raise FileNotFoundError(relative_path)

        path.unlink()

        self.logger.record(
            "FILE_DELETED",
            {
                "path": relative_path,
            },
        )

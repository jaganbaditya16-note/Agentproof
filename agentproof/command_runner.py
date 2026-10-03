from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any

from agentproof.action_log import ActionLogger
from agentproof.run_manager import RunManager


class CommandRunner:
    """Run commands while recording structured AgentProof events."""

    def __init__(self, repo: Path):
        self.repo = repo

        run = RunManager(repo).current()
        run_id = run["run_id"] if run else None

        self.logger = ActionLogger(
            repo,
            run_id=run_id,
        )

    def run(
        self,
        command: str,
        timeout: int = 120,
    ) -> dict[str, Any]:
        """Execute a command and record its lifecycle."""

        start_time = time.time()

        self.logger.record(
            "COMMAND_STARTED",
            {
                "command": command,
            },
        )

        try:
            result = subprocess.run(
                command,
                cwd=self.repo,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )

            duration = round(
                time.time() - start_time,
                3,
            )

            event = {
                "command": command,
                "exit_code": result.returncode,
                "duration_seconds": duration,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

            self.logger.record(
                "COMMAND_FINISHED",
                {
                    "command": command,
                    "exit_code": result.returncode,
                    "duration_seconds": duration,
                },
            )

            return event

        except subprocess.TimeoutExpired:
            duration = round(
                time.time() - start_time,
                3,
            )

            self.logger.record(
                "COMMAND_TIMEOUT",
                {
                    "command": command,
                    "duration_seconds": duration,
                },
            )

            return {
                "command": command,
                "exit_code": -1,
                "duration_seconds": duration,
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds.",
            }

        except Exception as exc:
            duration = round(
                time.time() - start_time,
                3,
            )

            self.logger.record(
                "COMMAND_ERROR",
                {
                    "command": command,
                    "duration_seconds": duration,
                    "error": str(exc),
                },
            )

            return {
                "command": command,
                "exit_code": -1,
                "duration_seconds": duration,
                "stdout": "",
                "stderr": str(exc),
            }

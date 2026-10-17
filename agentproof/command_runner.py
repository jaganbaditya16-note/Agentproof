from __future__ import annotations

import os
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any

from agentproof.action_log import ActionLogger
from agentproof.run_manager import RunManager


class CommandRunner:
    """Run configured argument lists with subprocess shell=False."""

    def __init__(self, repo: Path):
        self.repo = repo

        run = RunManager(repo).current()
        run_id = run["run_id"] if run else None

        self.logger = ActionLogger(repo, run_id=run_id)

    def run(
        self,
        command: list[str],
        timeout: int = 120,
    ) -> dict[str, Any]:
        """Execute an explicit argument list with shell execution disabled."""
        if (
            not isinstance(command, list)
            or not command
            or any(not isinstance(arg, str) for arg in command)
            or not command[0].strip()
        ):
            raise ValueError(
                "Command must be a non-empty list of string arguments."
            )

        args = list(command)
        display_command = (
            subprocess.list2cmdline(args)
            if os.name == "nt"
            else shlex.join(args)
        )

        start_time = time.time()

        self.logger.record(
            "COMMAND_STARTED",
            {"command": display_command, "shell": False},
        )

        try:
            result = subprocess.run(
                args,
                cwd=self.repo,
                shell=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )

            duration = round(time.time() - start_time, 3)

            self.logger.record(
                "COMMAND_FINISHED",
                {
                    "command": display_command,
                    "exit_code": result.returncode,
                    "duration_seconds": duration,
                },
            )

            return {
                "command": display_command,
                "exit_code": result.returncode,
                "duration_seconds": duration,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        except subprocess.TimeoutExpired:
            duration = round(time.time() - start_time, 3)

            self.logger.record(
                "COMMAND_TIMEOUT",
                {
                    "command": display_command,
                    "duration_seconds": duration,
                },
            )

            return {
                "command": display_command,
                "exit_code": -1,
                "duration_seconds": duration,
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds.",
            }

        except OSError as exc:
            duration = round(time.time() - start_time, 3)

            self.logger.record(
                "COMMAND_ERROR",
                {
                    "command": display_command,
                    "duration_seconds": duration,
                    "error": str(exc),
                },
            )

            return {
                "command": display_command,
                "exit_code": -1,
                "duration_seconds": duration,
                "stdout": "",
                "stderr": str(exc),
            }

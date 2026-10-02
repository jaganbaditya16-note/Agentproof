from __future__ import annotations

import json
import subprocess
from pathlib import Path


def run_git(repo: Path, args: list[str]) -> tuple[int, str, str]:
    """Run a Git command and return exit code, stdout, stderr."""

    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        return (
            result.returncode,
            result.stdout.strip(),
            result.stderr.strip(),
        )

    except FileNotFoundError:
        return -1, "", "Git was not found."


def load_baseline(repo: Path) -> dict:
    """Load the AgentProof baseline."""

    path = repo / ".agentproof" / "baseline.json"

    if not path.exists():
        raise FileNotFoundError(
            "No baseline exists. Run `agentproof baseline` first."
        )

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def detect_changes(repo: Path) -> list[dict]:
    """
    Compare the current working tree with the baseline commit.

    The comparison includes tracked changes and untracked files.
    """

    baseline = load_baseline(repo)
    commit = baseline["commit"]

    # Tracked changes compared with the baseline commit.
    code, output, error = run_git(
        repo,
        [
            "diff",
            "--name-status",
            "--find-renames",
            commit,
        ],
    )

    if code != 0:
        raise RuntimeError(
            f"Git diff failed: {error or 'unknown error'}"
        )

    changes: list[dict] = []

    for line in output.splitlines():
        if not line.strip():
            continue

        parts = line.split("\t")

        status = parts[0]

        if status.startswith("R") and len(parts) >= 3:
            changes.append(
                {
                    "status": "RENAMED",
                    "old_path": parts[1],
                    "path": parts[2],
                }
            )
        elif len(parts) >= 2:
            status_map = {
                "A": "ADDED",
                "M": "MODIFIED",
                "D": "DELETED",
            }

            changes.append(
                {
                    "status": status_map.get(status, status),
                    "path": parts[1],
                }
            )

    # Git diff does not include untracked files, so inspect them separately.
    code, output, error = run_git(
        repo,
        [
            "ls-files",
            "--others",
            "--exclude-standard",
        ],
    )

    if code != 0:
        raise RuntimeError(
            f"Could not inspect untracked files: "
            f"{error or 'unknown error'}"
        )

    for path in output.splitlines():
        if path.strip():
            changes.append(
                {
                    "status": "UNTRACKED",
                    "path": path,
                }
            )

    return changes

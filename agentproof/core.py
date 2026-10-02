from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


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


def load_baseline(repo: Path) -> dict[str, Any]:
    """Load the AgentProof baseline."""

    path = repo / ".agentproof" / "baseline.json"

    if not path.exists():
        raise FileNotFoundError(
            "No baseline exists. Run `agentproof baseline` first."
        )

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def detect_changes(repo: Path) -> list[dict[str, str]]:
    """
    Compare the current working tree with the baseline commit.

    Detects:
    - added files
    - modified files
    - deleted files
    - renamed files
    - untracked files
    """

    baseline = load_baseline(repo)
    commit = baseline["commit"]

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

    changes: list[dict[str, str]] = []

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

    # Git diff does not include untracked files.
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
            "Could not inspect untracked files: "
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


def run_tests(repo: Path) -> dict[str, Any]:
    """
    Run the project's independent test suite.

    This is intentionally separate from change detection.
    The agent's changed code is not trusted just because it changed.
    """

    command = [
        ".venv",
        "Scripts",
        "python.exe",
    ]

    python_path = repo.joinpath(*command)

    if python_path.exists():
        executable = str(python_path)
        args = [executable, "-m", "pytest", "-q"]
    else:
        executable = "py"
        args = [executable, "-m", "pytest", "-q"]

    try:
        result = subprocess.run(
            args,
            cwd=repo,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )

        return {
            "status": "PASS" if result.returncode == 0 else "FAIL",
            "command": " ".join(args),
            "exit_code": result.returncode,
            "stdout": result.stdout[-10000:],
            "stderr": result.stderr[-10000:],
        }

    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""

        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")

        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")

        return {
            "status": "UNKNOWN",
            "command": " ".join(args),
            "exit_code": -1,
            "stdout": stdout[-10000:],
            "stderr": (
                stderr[-10000:]
                + "\nTest suite timed out after 120 seconds."
            ),
        }

    except FileNotFoundError as exc:
        return {
            "status": "UNKNOWN",
            "command": " ".join(args),
            "exit_code": -1,
            "stdout": "",
            "stderr": str(exc),
        }


def determine_verdict(
    changes: list[dict[str, str]],
    tests: dict[str, Any],
) -> str:
    """
    Produce a conservative verification verdict.

    FAIL always wins.
    UNKNOWN is returned when verification cannot establish success.
    PASS requires the independent test suite to pass.
    """

    if tests["status"] == "FAIL":
        return "FAIL"

    if tests["status"] == "UNKNOWN":
        return "UNKNOWN"

    if not changes:
        return "UNKNOWN"

    return "PASS"


def verify(repo: Path) -> dict[str, Any]:
    """
    Run the first AgentProof verification workflow.

    1. Load baseline.
    2. Detect changes.
    3. Run independent tests.
    4. Produce a conservative verdict.
    """

    baseline = load_baseline(repo)
    changes = detect_changes(repo)
    tests = run_tests(repo)

    verdict = determine_verdict(
        changes=changes,
        tests=tests,
    )

    return {
        "agentproof_version": "0.1.0",
        "baseline": baseline,
        "changes": changes,
        "tests": tests,
        "verdict": verdict,
    }

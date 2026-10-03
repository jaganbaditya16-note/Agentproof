from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import yaml


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


def load_contract(repo: Path) -> dict[str, Any]:
    """
    Load and validate the AgentProof task contract.

    The contract defines:
    - task identity and goal
    - allowed paths
    - forbidden paths
    - verification requirements
    - verdict behavior
    """

    path = repo / "agentproof.yaml"

    if not path.exists():
        raise FileNotFoundError(
            "agentproof.yaml was not found."
        )

    try:
        with path.open("r", encoding="utf-8") as file:
            contract = yaml.safe_load(file)
    except yaml.YAMLError as exc:
        raise ValueError(
            f"Invalid YAML in agentproof.yaml: {exc}"
        ) from exc

    if not isinstance(contract, dict):
        raise ValueError(
            "agentproof.yaml must contain a YAML mapping."
        )

    required_sections = [
        "task",
        "scope",
        "verification",
        "verdict",
    ]

    missing_sections = [
        section
        for section in required_sections
        if section not in contract
    ]

    if missing_sections:
        raise ValueError(
            "Task contract is missing required section(s): "
            + ", ".join(missing_sections)
        )

    task = contract["task"]

    if not isinstance(task, dict):
        raise ValueError("The 'task' section must be a mapping.")

    if not task.get("id"):
        raise ValueError("The task must have an 'id'.")

    if not task.get("name"):
        raise ValueError("The task must have a 'name'.")

    if not task.get("goal"):
        raise ValueError("The task must have a 'goal'.")

    scope = contract["scope"]

    if not isinstance(scope, dict):
        raise ValueError("The 'scope' section must be a mapping.")

    verification = contract["verification"]

    if not isinstance(verification, dict):
        raise ValueError(
            "The 'verification' section must be a mapping."
        )

    if verification.get("require_tests_to_pass") is True:
        if not verification.get("test_command"):
            raise ValueError(
                "test_command is required when "
                "require_tests_to_pass is true."
            )

    return contract


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
    Run the independent test suite defined by the task contract.
    """

    contract = load_contract(repo)
    verification = contract["verification"]

    command = verification.get("test_command")

    if not command:
        return {
            "status": "UNKNOWN",
            "command": None,
            "exit_code": -1,
            "stdout": "",
            "stderr": "No test command configured.",
        }

    try:
        result = subprocess.run(
            command,
            cwd=repo,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )

        return {
            "status": "PASS" if result.returncode == 0 else "FAIL",
            "command": command,
            "exit_code": result.returncode,
            "stdout": result.stdout[-10000:],
            "stderr": result.stderr[-10000:],
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "UNKNOWN",
            "command": command,
            "exit_code": -1,
            "stdout": "",
            "stderr": "Test suite timed out after 120 seconds.",
        }

    except Exception as exc:
        return {
            "status": "UNKNOWN",
            "command": command,
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
    UNKNOWN is returned when success cannot be established.
    PASS requires changes and passing independent tests.
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
    Run the AgentProof verification workflow.
    """

    contract = load_contract(repo)
    baseline = load_baseline(repo)
    changes = detect_changes(repo)
    tests = run_tests(repo)

    verdict = determine_verdict(
        changes=changes,
        tests=tests,
    )

    return {
        "agentproof_version": "0.1.0",
        "task": contract["task"],
        "scope": contract["scope"],
        "verification": contract["verification"],
        "baseline": baseline,
        "changes": changes,
        "tests": tests,
        "verdict": verdict,
    }

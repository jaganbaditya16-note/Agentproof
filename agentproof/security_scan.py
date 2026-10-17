from __future__ import annotations

import re
from typing import Any


RULES = (
    (
        "AWS_ACCESS_KEY_ID",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        "high",
    ),
    (
        "GITHUB_TOKEN",
        re.compile(
            r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|"
            r"github_pat_[A-Za-z0-9_]{20,})\b"
        ),
        "high",
    ),
    (
        "STRIPE_LIVE_SECRET",
        re.compile(r"\b(?:sk|rk)_live_[A-Za-z0-9]{16,}\b"),
        "high",
    ),
    (
        "PRIVATE_KEY_HEADER",
        re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"
        ),
        "high",
    ),
)

GENERIC_CREDENTIAL = re.compile(
    r"""(?i)\b(?:api[_-]?key|access[_-]?token|client[_-]?secret|"""
    r"""secret[_-]?key|password)\b\s*[:=]\s*["']?"""
    r"""([A-Za-z0-9_./+=-]{16,})"""
)

PLACEHOLDER_MARKERS = (
    "example",
    "placeholder",
    "dummy",
    "changeme",
    "replace_me",
    "redacted",
    "your_",
    "your-",
)


def _is_placeholder(value: str) -> bool:
    normalized = value.strip().lower()
    return any(marker in normalized for marker in PLACEHOLDER_MARKERS)


def scan_text(text: str) -> list[dict[str, Any]]:
    """Find likely secrets without returning their values."""
    findings: list[dict[str, Any]] = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        for rule_id, pattern, severity in RULES:
            if pattern.search(line):
                findings.append(
                    {
                        "line": line_number,
                        "rule_id": rule_id,
                        "severity": severity,
                    }
                )

        match = GENERIC_CREDENTIAL.search(line)
        if match and not _is_placeholder(match.group(1)):
            findings.append(
                {
                    "line": line_number,
                    "rule_id": "GENERIC_CREDENTIAL_ASSIGNMENT",
                    "severity": "medium",
                }
            )

    return findings

from pathlib import Path


def scan_changed_files(
    repo: str | Path,
    changes: list[dict[str, str]],
    max_file_bytes: int = 1_000_000,
) -> dict[str, Any]:
    """Scan changed UTF-8 text files without exposing secret values."""
    root = Path(repo).resolve()
    findings: list[dict[str, Any]] = []
    files_scanned: list[str] = []
    skipped: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    seen: set[str] = set()

    for change in changes:
        relative = change.get("path", "")
        status = change.get("status", "")

        if not relative or status == "DELETED":
            continue

        if relative in seen:
            continue
        seen.add(relative)

        candidate = (root / relative).resolve()

        try:
            candidate.relative_to(root)
        except ValueError:
            errors.append({
                "path": relative,
                "reason": "PATH_OUTSIDE_REPOSITORY",
            })
            continue

        if not candidate.exists():
            skipped.append({
                "path": relative,
                "reason": "FILE_NOT_PRESENT",
            })
            continue

        if not candidate.is_file():
            skipped.append({
                "path": relative,
                "reason": "NOT_A_REGULAR_FILE",
            })
            continue

        try:
            if candidate.stat().st_size > max_file_bytes:
                errors.append({
                    "path": relative,
                    "reason": "FILE_TOO_LARGE",
                })
                continue

            raw = candidate.read_bytes()
            content = raw.decode("utf-8-sig")

        except UnicodeDecodeError:
            skipped.append({
                "path": relative,
                "reason": "NON_UTF8_OR_BINARY_FILE",
            })
            continue

        except OSError:
            errors.append({
                "path": relative,
                "reason": "FILE_READ_ERROR",
            })
            continue

        files_scanned.append(relative)

        for finding in scan_text(content):
            findings.append({
                "path": relative,
                **finding,
            })

    if findings:
        result_status = "FAIL"
    elif errors or skipped or not files_scanned:
        result_status = "UNKNOWN"
    else:
        result_status = "PASS"

    return {
        "status": result_status,
        "files_scanned": files_scanned,
        "findings": findings,
        "skipped": skipped,
        "errors": errors,
    }

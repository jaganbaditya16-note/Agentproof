from pathlib import Path

from agentproof.core import determine_verdict, evaluate_evidence


def test_evidence_passes_for_current_security_scanner():
    result = evaluate_evidence(Path.cwd())

    assert result["status"] == "PASS"
    assert result["passed"] == 2
    assert result["failed"] == 0


def test_evidence_fails_when_security_expectation_is_wrong():
    contract = Path("agentproof.yaml")
    original = contract.read_text(encoding="utf-8-sig")

    try:
        old = 'input: "ordinary code without credentials"\n      expected: []'
        new = 'input: "ordinary code without credentials"\n      expected: ["unexpected"]'

        if original.count(old) != 1:
            raise AssertionError(
                "Could not uniquely locate the security evidence case."
            )

        contract.write_text(
            original.replace(old, new, 1),
            encoding="utf-8",
        )

        result = evaluate_evidence(Path.cwd())

        assert result["status"] == "FAIL"
        assert result["failed"] == 1
    finally:
        contract.write_text(original, encoding="utf-8")


def test_evidence_reports_missing_function():
    contract = Path("agentproof.yaml")
    original = contract.read_text(encoding="utf-8-sig")

    try:
        old = "function: scan_text"
        new = "function: does_not_exist"

        if original.count(old) != 1:
            raise AssertionError(
                "Could not uniquely locate the configured evidence function."
            )

        contract.write_text(
            original.replace(old, new, 1),
            encoding="utf-8",
        )

        result = evaluate_evidence(Path.cwd())

        assert result["status"] == "FAIL"
        assert "does_not_exist" in result["error"]
    finally:
        contract.write_text(original, encoding="utf-8")


def test_security_finding_forces_failure():
    verdict = determine_verdict(
        changes=[{"status": "MODIFIED", "path": "src/example.py"}],
        scope={"status": "PASS"},
        tests={"status": "PASS"},
        evidence={"status": "PASS"},
        security={"status": "FAIL"},
    )

    assert verdict == "FAIL"


def test_incomplete_security_scan_cannot_pass():
    verdict = determine_verdict(
        changes=[{"status": "MODIFIED", "path": "src/example.py"}],
        scope={"status": "PASS"},
        tests={"status": "PASS"},
        evidence={"status": "PASS"},
        security={"status": "UNKNOWN"},
    )

    assert verdict == "UNKNOWN"
def _stub_verify_dependencies(monkeypatch, security_result):
    import agentproof.core as core

    contract = {
        "task": {
            "id": "example-task",
            "name": "Example task",
            "goal": "Verify expected behavior",
        },
        "scope": {
            "allowed_paths": ["src/**"],
            "forbidden_paths": [],
        },
    }

    monkeypatch.setattr(core, "load_contract", lambda repo: contract)
    monkeypatch.setattr(
        core, "load_baseline", lambda repo: {"commit": "test-commit"}
    )
    monkeypatch.setattr(
        core,
        "detect_changes",
        lambda repo: [{"status": "MODIFIED", "path": "src/example.py"}],
    )
    monkeypatch.setattr(
        core,
        "check_scope",
        lambda changes, contract: {
            "status": "PASS",
            "message": "Scope passed",
            "violations": [],
        },
    )
    monkeypatch.setattr(
        core,
        "run_tests",
        lambda repo: {
            "status": "PASS",
            "command": "pytest",
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
        },
    )
    monkeypatch.setattr(
        core,
        "evaluate_evidence",
        lambda repo, log_actions=False: {
            "status": "PASS",
            "module": "src.example",
            "function": "run",
            "cases": [],
            "passed": 1,
            "failed": 0,
            "error": None,
        },
    )
    monkeypatch.setattr(
        core, "scan_changed_files", lambda repo, changes: security_result
    )

    return core


def test_verify_report_includes_security_scan_and_passes_when_clean(
    monkeypatch, tmp_path
):
    security = {
        "status": "PASS",
        "files_scanned": ["src/example.py"],
        "findings": [],
        "skipped": [],
        "errors": [],
    }
    core = _stub_verify_dependencies(monkeypatch, security)

    report = core.verify(tmp_path)

    assert report["security_scan"] == security
    assert report["verdict"] == "PASS"


def test_verify_report_fails_when_security_finding_exists(
    monkeypatch, tmp_path
):
    security = {
        "status": "FAIL",
        "files_scanned": ["src/example.py"],
        "findings": [
            {
                "path": "src/example.py",
                "line": 4,
                "rule_id": "AWS_ACCESS_KEY_ID",
                "severity": "high",
            }
        ],
        "skipped": [],
        "errors": [],
    }
    core = _stub_verify_dependencies(monkeypatch, security)

    report = core.verify(tmp_path)

    assert report["security_scan"]["status"] == "FAIL"
    assert report["verdict"] == "FAIL"


def test_verify_report_is_unknown_when_security_scan_is_incomplete(
    monkeypatch, tmp_path
):
    security = {
        "status": "UNKNOWN",
        "files_scanned": [],
        "findings": [],
        "skipped": [],
        "errors": [
            {"path": "src/example.py", "reason": "FILE_READ_ERROR"}
        ],
    }
    core = _stub_verify_dependencies(monkeypatch, security)

    report = core.verify(tmp_path)

    assert report["security_scan"]["status"] == "UNKNOWN"
    assert report["verdict"] == "UNKNOWN"

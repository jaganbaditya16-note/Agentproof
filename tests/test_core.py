from pathlib import Path

from agentproof.core import evaluate_evidence


def test_evidence_passes_for_current_username_implementation():
    result = evaluate_evidence(Path.cwd())

    assert result["status"] == "PASS"
    assert result["passed"] == 8
    assert result["failed"] == 0


def test_evidence_fails_when_username_rule_is_broken():
    username_file = Path("src/username.py")
    original = username_file.read_text(encoding="utf-8")

    try:
        username_file.write_text(
            original.replace(
                "USERNAME_MIN_LENGTH: Final[int] = 3",
                "USERNAME_MIN_LENGTH: Final[int] = 4",
            ),
            encoding="utf-8",
        )

        result = evaluate_evidence(Path.cwd())

        assert result["status"] == "FAIL"
        assert result["failed"] == 1
        assert result["cases"][7]["input"] == "123"
        assert result["cases"][7]["status"] == "FAIL"
    finally:
        username_file.write_text(original, encoding="utf-8")


def test_evidence_reports_missing_function():
    contract = Path("agentproof.yaml")
    original = contract.read_text(encoding="utf-8")

    try:
        modified = original.replace(
            "function: is_valid_username",
            "function: does_not_exist",
        )
        contract.write_text(modified, encoding="utf-8")

        result = evaluate_evidence(Path.cwd())

        assert result["status"] == "FAIL"
        assert "does_not_exist" in result["error"]
    finally:
        contract.write_text(original, encoding="utf-8")

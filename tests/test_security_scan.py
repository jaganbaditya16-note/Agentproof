from agentproof.security_scan import scan_text


def test_detects_aws_access_key_without_exposing_value():
    fake_key = "AKIA" + "1234567890ABCDEF"

    findings = scan_text("key=" + fake_key)

    assert any(
        item["rule_id"] == "AWS_ACCESS_KEY_ID"
        for item in findings
    )
    assert all("value" not in item for item in findings)


def test_detects_github_and_stripe_token_patterns():
    text = "\n".join(
        [
            "token = " + '"ghp_' + ("a" * 30) + '"',
            "stripe = " + '"sk_live_' + ("b" * 24) + '"',
        ]
    )

    findings = scan_text(text)
    rule_ids = {item["rule_id"] for item in findings}

    assert "GITHUB_TOKEN" in rule_ids
    assert "STRIPE_LIVE_SECRET" in rule_ids


def test_detects_generic_credentials_and_private_key_header():
    credential = (
        "API" + "_KEY=" + '"' + ("qwerty" * 4) + '"'
    )
    private_header = (
        "-----BEGIN " + "RSA " + "PRIVATE KEY-----"
    )

    findings = scan_text(credential + "\n" + private_header)
    rule_ids = {item["rule_id"] for item in findings}

    assert "GENERIC_CREDENTIAL_ASSIGNMENT" in rule_ids
    assert "PRIVATE_KEY_HEADER" in rule_ids


def test_ignores_common_placeholder_values():
    text = (
        "API" + "_KEY=" + '"example-' + "1234567890123456" + '"'
    )

    assert scan_text(text) == []


def test_empty_or_safe_text_has_no_findings():
    assert scan_text("") == []
    assert scan_text("def add(a, b):\n    return a + b") == []

def test_scan_changed_files_detects_secret_without_exposing_value(tmp_path):
    from agentproof.security_scan import scan_changed_files

    fake_key = "AKIA" + "1234567890ABCDEF"
    (tmp_path / "sample.py").write_text(
        "key = " + fake_key, encoding="utf-8"
    )

    result = scan_changed_files(
        tmp_path, [{"status": "ADDED", "path": "sample.py"}]
    )

    assert result["status"] == "FAIL"
    assert result["findings"][0]["path"] == "sample.py"
    assert all("value" not in item for item in result["findings"])


def test_scan_changed_files_passes_for_safe_text(tmp_path):
    from agentproof.security_scan import scan_changed_files

    (tmp_path / "sample.py").write_text(
        "def add(a, b):\n    return a + b\n",
        encoding="utf-8",
    )

    result = scan_changed_files(
        tmp_path, [{"status": "MODIFIED", "path": "sample.py"}]
    )

    assert result["status"] == "PASS"
    assert result["files_scanned"] == ["sample.py"]
    assert result["findings"] == []


def test_scan_changed_files_rejects_path_escape(tmp_path):
    from agentproof.security_scan import scan_changed_files

    result = scan_changed_files(
        tmp_path, [{"status": "ADDED", "path": "../outside.txt"}]
    )

    assert result["status"] == "UNKNOWN"
    assert result["errors"][0]["reason"] == "PATH_OUTSIDE_REPOSITORY"


def test_scan_changed_files_does_not_read_oversized_file(tmp_path):
    from agentproof.security_scan import scan_changed_files

    (tmp_path / "large.txt").write_text("1234567890", encoding="utf-8")

    result = scan_changed_files(
        tmp_path,
        [{"status": "ADDED", "path": "large.txt"}],
        max_file_bytes=5,
    )

    assert result["status"] == "UNKNOWN"
    assert result["errors"][0]["reason"] == "FILE_TOO_LARGE"
from agentproof.security_scan import scan_changed_files


def test_skipped_binary_file_makes_scan_unknown(tmp_path):
    (tmp_path / "safe.py").write_text(
        "def add(a, b):\n    return a + b\n",
        encoding="utf-8",
    )
    (tmp_path / "image.bin").write_bytes(b"\x00\xff\x01")

    result = scan_changed_files(
        tmp_path,
        [
            {"status": "MODIFIED", "path": "safe.py"},
            {"status": "ADDED", "path": "image.bin"},
        ],
    )

    assert result["status"] == "UNKNOWN"
    assert result["files_scanned"] == ["safe.py"]
    assert any(
        item["reason"] == "NON_UTF8_OR_BINARY_FILE"
        for item in result["skipped"]
    )

import subprocess

import pytest

from agentproof.command_runner import CommandRunner


def test_command_runner_disables_shell(monkeypatch, tmp_path):
    runner = CommandRunner(tmp_path)
    observed = {}

    class FakeResult:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def fake_run(args, **kwargs):
        observed["args"] = args
        observed["kwargs"] = kwargs
        return FakeResult()

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = runner.run(["python", "-m", "pytest", "-q"])

    assert observed["args"] == ["python", "-m", "pytest", "-q"]
    assert observed["kwargs"]["shell"] is False
    assert result["exit_code"] == 0
    assert result["stdout"] == "ok"


def test_command_runner_rejects_invalid_commands(tmp_path):
    runner = CommandRunner(tmp_path)

    with pytest.raises(ValueError):
        runner.run([])

    with pytest.raises(ValueError):
        runner.run("echo unsafe")

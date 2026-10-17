# AgentProof

**A local-first verification CLI for code changes, including AI-generated code.**

AgentProof checks configured requirements instead of relying only on an AI agent's claim that a task is complete.

## Features

- Git baseline capture and changed-file detection.
- Allowed-path and forbidden-path checks.
- Automated test execution through argument lists with subprocess shell=False.
- Configurable behavioral evidence checks for Python functions.
- Pattern-based secret scanning of changed text files.
- Structured action logs and JSON verification reports.
- Conservative PASS, FAIL and UNKNOWN verdicts.

The current workflow uses local tools and requires no paid AI API or cloud service.

## How It Works

1. Capture a clean Git baseline.
2. Make the intended code changes.
3. Detect changed files.
4. Check configured path-scope rules.
5. Run automated tests.
6. Evaluate behavioral evidence.
7. Scan changed text files for likely exposed credentials.
8. Save the result to `.agentproof/report.json`.

## Requirements

- Python 3.10 or newer
- Git
- Windows PowerShell for the commands below

## Setup

Clone the repository and open PowerShell inside its folder.

Create a virtual environment:

```powershell
py -m venv .venv
```

Install AgentProof:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
```

Display the available commands:

```powershell
.\.venv\Scripts\python.exe -m agentproof.cli --help
```

## Quick Start

Start with a clean Git working tree and an initial commit.

Capture the baseline before making changes:

```powershell
.\.venv\Scripts\python.exe -m agentproof.cli baseline
```

Inspect changes:

```powershell
.\.venv\Scripts\python.exe -m agentproof.cli changes
```

Scan changed files:

```powershell
.\.venv\Scripts\python.exe -m agentproof.cli security-scan
```

Run the complete verification pipeline:

```powershell
.\.venv\Scripts\python.exe -m agentproof.cli verify
```

Configure task requirements, scope rules, tests and behavioral evidence in `agentproof.yaml`.

## Verdicts

| Verdict | Meaning |
| --- | --- |
| PASS | All configured verification checks passed. |
| FAIL | A configured check failed. |
| UNKNOWN | Verification could not establish a reliable result. |

The verification report is saved to `.agentproof/report.json`.

## Security Limitations

The secret scanner checks changed UTF-8 text files against selected credential patterns. It can miss secrets and produce false positives; it is not a replacement for dedicated secret-scanning tools.

Using `shell=False` prevents shell interpretation of the configured test command, but does not sandbox the executed program. The evidence worker also executes configured Python code and is not a secure sandbox for untrusted code.

A passing report is not a security certification. Review task configuration and test commands before execution. Do not use this early version to authorize sensitive production operations.

## Development

Run the test suite:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Check Python compilation:

```powershell
.\.venv\Scripts\python.exe -m compileall -q agentproof tests
```

## Roadmap

Future improvements may include stronger execution safeguards, more integration tests, additional evidence formats and integrations requested by users.

AgentProof is intended for developers and software teams across multiple companies. Its direction will be guided by user feedback and validated use cases rather than one company's response.

## Status

Early-stage prototype. Review the limitations before using it in production.

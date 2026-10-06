import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agentproof.core import detect_changes, verify as run_verification
from agentproof.run_manager import RunManager


app = typer.Typer(
    name="agentproof",
    help="Independent verification engine for AI agent work.",
)

console = Console()


def run_git(args: list[str]) -> tuple[int, str, str]:
    """Run a Git command in the current repository."""

    try:
        result = subprocess.run(
            ["git", *args],
            cwd=Path.cwd(),
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
        return -1, "", "Git is not installed or not available in PATH."


@app.command()
def status():
    """Show the current AgentProof status."""

    console.print(
        Panel(
            "[bold green]AgentProof is running.[/bold green]\n\n"
            "Core verification engine initialized.\n"
            "Version: 0.1.0",
            title="AgentProof",
        )
    )


@app.command()
def version():
    """Show the AgentProof version."""

    console.print("AgentProof version 0.1.0")


@app.command()
def repo():
    """Inspect the current Git repository."""

    root_code, root, root_error = run_git(
        ["rev-parse", "--show-toplevel"]
    )

    if root_code != 0:
        console.print(
            Panel(
                "[bold red]Not a Git repository.[/bold red]\n\n"
                + (root_error or "Git repository not found."),
                title="Repository Check",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    branch_code, branch, _ = run_git(
        ["branch", "--show-current"]
    )

    commit_code, commit, _ = run_git(
        ["rev-parse", "HEAD"]
    )

    status_code, status_output, _ = run_git(
        ["status", "--porcelain"]
    )

    if branch_code != 0:
        branch = "Unknown"

    if commit_code != 0:
        commit = "No commit yet"

    changed_files = []

    if status_code == 0 and status_output:
        for line in status_output.splitlines():
            if len(line) >= 4:
                changed_files.append(line[3:])

    table = Table(title="Repository Information")

    table.add_column("Property")
    table.add_column("Value")

    table.add_row("Root", root)
    table.add_row("Branch", branch)
    table.add_row("Commit", commit)
    table.add_row("Changed files", str(len(changed_files)))

    console.print(table)

    if changed_files:
        console.print("\n[yellow]Working tree changes:[/yellow]")

        for file in changed_files:
            console.print(f"  {file}")
    else:
        console.print(
            "\n[green]Working tree is clean.[/green]"
        )


@app.command()
def baseline():
    """Capture the repository state before agent work begins."""

    root_code, root, root_error = run_git(
        ["rev-parse", "--show-toplevel"]
    )

    if root_code != 0:
        console.print(
            Panel(
                "[bold red]Not a Git repository.[/bold red]\n\n"
                + (root_error or "Git repository not found."),
                title="Baseline",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    status_code, status_output, status_error = run_git(
        ["status", "--porcelain"]
    )

    if status_code != 0:
        console.print(
            Panel(
                "[bold red]Could not read Git status.[/bold red]\n\n"
                + (status_error or "Unknown Git error."),
                title="Baseline",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    if status_output:
        console.print(
            Panel(
                "[bold red]Baseline cannot be captured.[/bold red]\n\n"
                "The working tree is not clean.\n\n"
                "Commit or remove the existing changes first.",
                title="Baseline",
                border_style="red",
            )
        )

        console.print("\nExisting changes:")

        for line in status_output.splitlines():
            console.print(f"  {line}")

        raise typer.Exit(code=1)

    commit_code, commit, commit_error = run_git(
        ["rev-parse", "HEAD"]
    )

    if commit_code != 0:
        console.print(
            Panel(
                "[bold red]No Git commit exists yet.[/bold red]\n\n"
                + (commit_error or "Create the first commit first."),
                title="Baseline",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    branch_code, branch, _ = run_git(
        ["branch", "--show-current"]
    )

    if branch_code != 0:
        branch = "Unknown"

    evidence_dir = Path(root) / ".agentproof"
    evidence_dir.mkdir(exist_ok=True)

    baseline_data = {
        "agentproof_version": "0.1.0",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "repository_root": root,
        "branch": branch,
        "commit": commit,
        "working_tree_clean": True,
    }

    baseline_path = evidence_dir / "baseline.json"

    with baseline_path.open("w", encoding="utf-8") as file:
        json.dump(baseline_data, file, indent=2)

    console.print(
        Panel(
            "[bold green]Baseline captured successfully.[/bold green]\n\n"
            f"Branch: {branch}\n"
            f"Commit: {commit}\n"
            f"Evidence: {baseline_path}",
            title="AgentProof Baseline",
            border_style="green",
        )
    )


@app.command()
def changes():
    """Show changes made after the AgentProof baseline."""

    try:
        detected = detect_changes(Path.cwd())

    except Exception as exc:
        console.print(
            Panel(
                f"[bold red]{exc}[/bold red]",
                title="Change Detection Error",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    if not detected:
        console.print(
            Panel(
                "[bold green]No changes detected.[/bold green]",
                title="AgentProof Changes",
                border_style="green",
            )
        )
        return

    table = Table(title="Changes Since Baseline")

    table.add_column("Status")
    table.add_column("Path")

    for change in detected:
        status = change["status"]

        if status == "RENAMED":
            path = f'{change["old_path"]} -> {change["path"]}'
        else:
            path = change["path"]

        table.add_row(status, path)

    console.print(table)

    console.print(
        f"\n[bold]Total changes detected:[/bold] {len(detected)}"
    )


@app.command()
def verify():
    """Run the complete AgentProof verification pipeline."""

    repo = Path.cwd()
    run_manager = RunManager(repo)

    run = run_manager.start()
    run_id = run["run_id"]

    console.print(
        f"\n[dim]Verification run: {run_id}[/dim]\n"
    )

    try:
        report = run_verification(repo)

        report["run"] = run

    except Exception as exc:
        console.print(
            Panel(
                f"[bold red]{exc}[/bold red]",
                title="Verification Error",
                border_style="red",
            )
        )
        run_manager.finish()
        raise typer.Exit(code=1)

    finally:
        run_manager.finish()

    report_path = (
        repo / ".agentproof" / "report.json"
    )

    report_path.parent.mkdir(exist_ok=True)

    with report_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    table = Table(title="AgentProof Verification")

    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Details")

    changes = report["changes"]

    table.add_row(
        "Changes",
        "PASS" if changes else "UNKNOWN",
        f"{len(changes)} change(s) detected",
    )

    scope_status = report["scope_check"]["status"]

    table.add_row(
        "Scope",
        scope_status,
        report["scope_check"]["message"],
    )

    test_status = report["tests"]["status"]

    table.add_row(
        "Tests",
        test_status,
        f'exit code: {report["tests"]["exit_code"]}',
    )
    evidence_status = report["evidence"]["status"]

    table.add_row(
        "Evidence",
        evidence_status,
        f'{report["evidence"]["passed"]} passed, {report["evidence"]["failed"]} failed',
    )

    console.print(table)

    verdict = report["verdict"]

    style = {
        "PASS": "green",
        "FAIL": "red",
        "UNKNOWN": "yellow",
    }[verdict]

    console.print(
        Panel(
            f"[bold]{verdict}[/bold]",
            title="FINAL VERDICT",
            border_style=style,
        )
    )

    console.print(
        f"\nEvidence report: [bold]{report_path}[/bold]"
    )

    if verdict == "FAIL":
        raise typer.Exit(code=1)

    if verdict == "UNKNOWN":
        raise typer.Exit(code=2)


if __name__ == "__main__":
    app()


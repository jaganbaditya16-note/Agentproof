import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="agentproof",
    help="Independent verification engine for AI agent work.",
)

console = Console()


def run_git(args: list[str]) -> tuple[int, str, str]:
    """Run a Git command in the current directory."""

    try:
        result = subprocess.run(
            ["git", *args],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )

        return result.returncode, result.stdout.strip(), result.stderr.strip()

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
                f"[bold red]Not a Git repository.[/bold red]\n\n"
                f"{root_error or 'Run git init to create one.'}",
                title="Repository Check",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    branch_code, branch, branch_error = run_git(
        ["branch", "--show-current"]
    )

    commit_code, commit, commit_error = run_git(
        ["rev-parse", "HEAD"]
    )

    status_code, status_output, status_error = run_git(
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
        console.print(
            "\n[yellow]Working tree changes:[/yellow]"
        )

        for file in changed_files:
            console.print(f"  • {file}")
    else:
        console.print(
            "\n[green]Working tree is clean.[/green]"
        )


if __name__ == "__main__":
    app()


from __future__ import annotations

import io

from review_pilot import __version__
from review_pilot.cli import main


def run_cli(args: list[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    exit_code = main(args, stdout=stdout, stderr=stderr)
    return exit_code, stdout.getvalue(), stderr.getvalue()


def test_help_shows_review_and_doctor_commands() -> None:
    exit_code, stdout, stderr = run_cli(["--help"])

    assert exit_code == 0
    assert "doctor" in stdout
    assert "review" in stdout
    assert "--version" in stdout
    assert stderr == ""


def test_version_uses_package_version() -> None:
    exit_code, stdout, stderr = run_cli(["--version"])

    assert exit_code == 0
    assert stdout.strip() == __version__
    assert stderr == ""


def test_doctor_command_succeeds_in_normal_environment() -> None:
    exit_code, stdout, stderr = run_cli(["doctor"])

    assert exit_code == 0
    assert "[OK] python:" in stdout
    assert "[OK] git:" in stdout
    assert stderr == ""


def test_no_subcommand_prints_help() -> None:
    exit_code, stdout, stderr = run_cli([])

    assert exit_code == 0
    assert "doctor" in stdout
    assert "review" in stdout
    assert stderr == ""


def test_review_help_shows_future_local_review_shape() -> None:
    exit_code, stdout, stderr = run_cli(["review", "--help"])

    assert exit_code == 0
    assert "review-pilot review" in stdout
    assert "--staged" in stdout
    assert "--base" in stdout
    assert "M01 only defines the command shape" in stdout
    assert stderr == ""


def test_review_command_without_real_diff_returns_scope_message() -> None:
    exit_code, stdout, stderr = run_cli(["review", "--staged"])

    assert exit_code == 2
    assert stdout == ""
    assert "diff reading starts in M02" in stderr

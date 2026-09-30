from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import TextIO

from . import __version__
from .doctor import run_checks


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="review-pilot",
        description="Code review agent for local diffs, CI, and PR workflows.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=__version__,
    )

    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("doctor", help="Check whether the local environment can run review-pilot.")
    review_parser = subparsers.add_parser("review", help="Prepare the local code review workflow command.")
    review_parser.add_argument("--staged", action="store_true", help="Review staged Git changes. Implemented in M02.")
    review_parser.add_argument("--base", metavar="REF", help="Review changes against a base ref. Implemented later.")
    return parser


def build_review_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="review-pilot review",
        description="Local review workflow entry. M01 only defines the command shape.",
    )
    parser.add_argument("--staged", action="store_true", help="Review staged Git changes. Implemented in M02.")
    parser.add_argument("--base", metavar="REF", help="Review changes against a base ref. Implemented later.")
    return parser


def _run_doctor(out: TextIO, err: TextIO) -> int:
    exit_code = 0
    for result in run_checks():
        if result.ok:
            print(f"[OK] {result.name}: {result.message}", file=out)
        else:
            print(f"[FAIL] {result.name}: {result.message}", file=err)
            exit_code = 1
    return exit_code


def main(argv: Sequence[str] | None = None, stdout: TextIO | None = None, stderr: TextIO | None = None) -> int:
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    parser = build_parser()
    command_args = list(argv) if argv is not None else sys.argv[1:]

    if not command_args or command_args == ["--help"] or command_args == ["-h"]:
        parser.print_help(out)
        return 0

    if command_args == ["--version"]:
        print(__version__, file=out)
        return 0

    if command_args in (["review"], ["review", "--help"], ["review", "-h"]):
        build_review_parser().print_help(out)
        return 0

    args = parser.parse_args(command_args)

    if args.command == "doctor":
        return _run_doctor(out, err)

    if args.command == "review":
        print("review command shape is ready; diff reading starts in M02.", file=err)
        return 2

    parser.print_help(out)
    return 0

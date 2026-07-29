#!/usr/bin/env python3
"""Fail-closed compatibility entry point for removed history harvesting.

Older local automation may still invoke this path. The compatibility command
intentionally does not inspect home directories, editor-owned history,
credentials, provider services, or networks. Project-local events and live Git
are the supported sources of durable context.
"""

from __future__ import annotations

import argparse


NOTICE = (
    "  Editor-history import is disabled; use explicitly authorized "
    "project-local events."
)


def build_parser() -> argparse.ArgumentParser:
    """Accept legacy options without performing any history access."""
    parser = argparse.ArgumentParser(
        description="Report the fail-closed project-local history policy."
    )
    parser.add_argument("--date", help=argparse.SUPPRESS)
    parser.add_argument("--hours", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--project", help=argparse.SUPPRESS)
    parser.add_argument("--max-per-session", type=int, help=argparse.SUPPRESS)
    return parser


def main() -> int:
    build_parser().parse_args()
    print(NOTICE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

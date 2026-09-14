#!/usr/bin/env python3
"""Provider compatibility helpers with fail-closed public-v2 behavior.

Legacy memory scripts import these names. They deliberately do not read key
files, environment credentials, or perform network activity. Provider access
must be expressed as an immutable payload and sent through egress_guard.py
under a separate exact authorization.
"""

from __future__ import annotations

import sys
from typing import Any, Optional, Sequence, Tuple


def load_api_keys(exocortex_dir: Any, silent: bool = False) -> Tuple[None, None, str, str]:
    """Return no credentials; direct provider key discovery is retired."""
    del exocortex_dir
    if not silent:
        print(
            "Provider access unavailable in this process: prepare an immutable "
            "payload and obtain separate destination-specific egress authority.",
            file=sys.stderr,
        )
    return None, None, "guarded-provider", "guarded-provider"


def call_ai(
    openai_key: Optional[str],
    anthropic_key: Optional[str],
    messages: Sequence[Any],
    max_tokens: int = 1500,
    silent: bool = False,
    openai_model: str = "guarded-provider",
    anthropic_model: str = "guarded-provider",
) -> None:
    """Deny legacy direct provider calls without inspecting supplied values."""
    del openai_key, anthropic_key, messages, max_tokens, openai_model, anthropic_model
    if not silent:
        print(
            "Direct provider calls are disabled; use the public-v2 egress guard "
            "with an immutable approved descriptor.",
            file=sys.stderr,
        )
    return None

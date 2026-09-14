#!/usr/bin/env python3
"""Report guarded credential-validation status without reading credentials."""

from __future__ import annotations

import json


def main() -> int:
    print(
        json.dumps(
            {
                "ok": False,
                "code": "separate_egress_authorization_required",
                "read_only": True,
                "message": (
                    "No key was read or tested. Credential validation requires "
                    "an exact destination-specific capability and guarded transport."
                ),
            },
            sort_keys=True,
        )
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

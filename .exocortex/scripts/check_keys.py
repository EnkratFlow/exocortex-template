#!/usr/bin/env python3
"""
check_keys.py — Validate all API keys from key-registry.json
SECURITY: Key values are NEVER printed, logged, or included in output.
Only the last 4 characters are shown for identification.
"""
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # .exocortex/scripts/ → project root
REGISTRY_PATH = SCRIPT_DIR.parent / "key-registry.json"

# ── Colours ───────────────────────────────────────────────────────────────────
GREEN  = "\033[0;32m"
RED    = "\033[0;31m"
YELLOW = "\033[1;33m"
CYAN   = "\033[0;36m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

CHECK = "✅"; CROSS = "❌"; WARN = "⚠️ "


# ── Helpers ───────────────────────────────────────────────────────────────────

def last4(val: str) -> str:
    """Return last 4 chars of a key — enough to identify, not enough to use."""
    if not val or len(val) < 4:
        return "(short)"
    return f"...{val[-4:]}"


def read_key_from_file(filepath: Path, varname: str) -> str:
    """Read a single env var value from a file. Returns empty string if not found."""
    if not filepath.exists():
        return ""
    try:
        for line in filepath.read_text().splitlines():
            line = line.strip()
            if line.startswith(f"{varname}=") and not line.startswith("#"):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return ""


def resolve_file(file_key: str, files_config: dict, project_root: Path) -> Path:
    """Resolve a file key from the registry to an absolute path."""
    raw = files_config.get(file_key, "")
    if not raw:
        return Path("/nonexistent")
    expanded = os.path.expanduser(raw)
    p = Path(expanded)
    if not p.is_absolute():
        p = project_root / p
    return p


# ── API testers ───────────────────────────────────────────────────────────────

def test_key(key: str, service_config: dict) -> str:
    """Test an API key. Returns 'valid', 'invalid', 'error', or 'unreachable'."""
    if not key:
        return "missing"

    url    = service_config.get("test_url", "")
    method = service_config.get("method", "GET").upper()
    auth   = service_config.get("auth", "bearer")

    if not url:
        return "unknown"

    try:
        headers = {"User-Agent": "check-keys/1.0"}
        data = None

        if auth == "bearer":
            headers["Authorization"] = f"Bearer {key}"

        elif auth == "x-api-key":
            headers["x-api-key"] = key
            headers["anthropic-version"] = "2023-06-01"
            headers["content-type"] = "application/json"
            # Minimal Anthropic test payload
            data = json.dumps({
                "model": "claude-sonnet-4-6",
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "hi"}]
            }).encode()

        elif auth == "query_param":
            url = f"{url}?key={key}"

        elif auth == "none":
            pass  # No auth — just check reachability

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=8) as resp:
            return "valid" if resp.status in (200, 201) else "error"

    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return "invalid"
        if e.code in (200, 201):
            return "valid"
        # Anthropic returns 200 in the exception body sometimes — treat 4xx as invalid
        if 400 <= e.code < 500:
            return "invalid"
        return "error"

    except urllib.error.URLError:
        return "unreachable"

    except Exception:
        return "error"


# ── Display ───────────────────────────────────────────────────────────────────

STATUS_ICON  = {"valid": CHECK,  "invalid": CROSS, "missing": WARN,
                "error": WARN,   "unreachable": WARN, "unknown": WARN}
STATUS_COLOR = {"valid": GREEN,  "invalid": RED,   "missing": YELLOW,
                "error": YELLOW, "unreachable": YELLOW, "unknown": YELLOW}


def print_key_row(varname: str, status: str, suffix: str, purpose: str, display_file: str):
    icon  = STATUS_ICON.get(status, WARN)
    color = STATUS_COLOR.get(status, YELLOW)
    print(f"  {varname:<30} {suffix:<10}  {color}{status:<12}{RESET}  {purpose}")
    print(f"  {'':30} {CYAN}↳ {display_file}{RESET}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Load registry
    if not REGISTRY_PATH.exists():
        print(f"{RED}Registry not found: {REGISTRY_PATH}{RESET}")
        sys.exit(1)

    try:
        registry = json.loads(REGISTRY_PATH.read_text())
    except json.JSONDecodeError as e:
        print(f"{RED}Registry JSON invalid: {e}{RESET}")
        sys.exit(1)

    files_config   = registry.get("files", {})
    services_config = registry.get("services", {})
    keys           = registry.get("keys", [])

    # Header
    print()
    print(f"{BOLD}KEY CHECK REPORT — {datetime.now().strftime('%Y-%m-%d %H:%M')}{RESET}")
    print("══════════════════════════════════════════════════════════")
    print()

    # Group keys by file for display
    by_file: dict[str, list] = {}
    for entry in keys:
        fkey = entry.get("file", "global")
        by_file.setdefault(fkey, []).append(entry)

    valid_count = 0; invalid_count = 0; missing_count = 0
    rotate_urls: set[str] = set()

    for file_key, entries in by_file.items():
        filepath     = resolve_file(file_key, files_config, PROJECT_ROOT)
        raw_path     = files_config.get(file_key, file_key)
        display_path = raw_path

        print(f"{BOLD}{display_path}{RESET}")

        if not filepath.exists():
            print(f"  {YELLOW}File not found: {filepath}{RESET}")
            for entry in entries:
                missing_count += 1
            print()
            continue

        for entry in entries:
            varname  = entry.get("var", "")
            service  = entry.get("service", "")
            purpose  = entry.get("purpose", "")
            svc_cfg  = services_config.get(service, {})

            val = read_key_from_file(filepath, varname)

            if not val:
                print_key_row(varname, "missing", "(not set)", purpose, display_path)
                missing_count += 1
            else:
                suffix = last4(val)
                status = test_key(val, svc_cfg)
                print_key_row(varname, status, f"[{suffix}]", purpose, display_path)
                if status == "valid":
                    valid_count += 1
                else:
                    invalid_count += 1
                    rotate_url = svc_cfg.get("rotate_url")
                    if rotate_url:
                        rotate_urls.add(f"  {svc_cfg.get('name', service):<14} {rotate_url}")
            print()

    # Summary
    print("══════════════════════════════════════════════════════════")
    total = valid_count + invalid_count + missing_count
    print(f"{GREEN}{valid_count} valid{RESET}  {RED}{invalid_count} invalid{RESET}  {YELLOW}{missing_count} missing{RESET}  ({total} total)")
    print()

    if invalid_count > 0:
        print(f"{RED}Action required — rotate invalid keys:{RESET}")
        for line in sorted(rotate_urls):
            print(line)
        print()
    elif missing_count > 0:
        print(f"{YELLOW}Some keys are missing. Add them to the appropriate file shown above.{RESET}")
        print()
        # Show rotate URLs for any service with missing keys (deduplicated)
        missing_urls: dict[str, str] = {}
        for entry in keys:
            val = read_key_from_file(
                resolve_file(entry.get("file", "global"), files_config, PROJECT_ROOT),
                entry.get("var", "")
            )
            if not val:
                svc = services_config.get(entry.get("service", ""), {})
                url = svc.get("rotate_url")
                name = svc.get("name", entry.get("service", ""))
                if url and name not in missing_urls:
                    missing_urls[name] = url
        for name, url in missing_urls.items():
            print(f"  {name}: {url}")
        print()
    else:
        print(f"{GREEN}All keys valid.{RESET}")
        print()

    # Tip: adding new providers
    print(f"{CYAN}To add a new provider: edit .exocortex/key-registry.json{RESET}")
    print()


if __name__ == "__main__":
    main()

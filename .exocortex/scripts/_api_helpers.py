#!/usr/bin/env python3
"""
Shared API helpers for exocortex memory scripts.

Provides:
  load_api_keys()  — Load + validate keys from .env (detects missing files, placeholders)
  call_ai()        — Call OpenAI/Anthropic with human-readable error messages

Used by: get_rightnow_memory.py, get_shortterm_memory.py, get_longterm_memory.py,
         get_subconscious_memory.py, get_subconscious_nudge.py, drill_memory.py

Error handling covers:
  - Missing .env file → instructions to create one
  - Placeholder keys → instructions to edit with real keys
  - Invalid/expired API keys → link to provider dashboard
  - Billing/quota exceeded → link to billing page
  - Rate limiting → retry message
  - Network errors → connection troubleshooting
  - Unexpected response format → diagnostic info
"""

import sys
import json
import urllib.request
import urllib.error
from pathlib import Path


# ---------------------------------------------------------------------------
# Key loading + validation
# ---------------------------------------------------------------------------

def load_api_keys(exocortex_dir, silent=False):
    """
    Load and validate API keys.

    Resolution order:
      1. ~/.exocortex/.env  (global — set once, works for all projects)
      2. .exocortex/.env    (local override — project-specific keys)

    Checks:
      - Keys are not placeholder values (warns and nullifies)
      - Keys are non-empty strings

    Returns (openai_key, anthropic_key, openai_model, anthropic_model).
    silent=True suppresses all messages (for automatic/optional commands like nudge).
    """
    global_env_file = Path.home() / ".exocortex" / ".env"
    local_env_file = Path(exocortex_dir) / ".env"

    # --- Check at least one .env exists ---
    if not global_env_file.exists() and not local_env_file.exists():
        if not silent:
            print("❌ No API keys found.", file=sys.stderr)
            print(f"   Recommended: create ~/.exocortex/.env once for all projects:", file=sys.stderr)
            print(f"     OPENAI_API_KEY=sk-...", file=sys.stderr)
            print(f"     ANTHROPIC_API_KEY=sk-ant-...", file=sys.stderr)
            print(f"   Or create a project-local .exocortex/.env", file=sys.stderr)
            print(f"   Get keys: https://platform.openai.com/api-keys", file=sys.stderr)
        return None, None, 'gpt-4o-mini', 'claude-3-haiku-20240307'

    # --- Load keys: global first, local overrides ---
    api_keys = {}
    for env_file in [global_env_file, local_env_file]:
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if '=' in line and not line.startswith('#'):
                    key, val = line.split('=', 1)
                    api_keys[key.strip()] = val.strip()

    openai_key = (
        api_keys.get('OPENAI_API_KEY_EXOCORTEX', '').strip()
        or api_keys.get('OPENAI_API_KEY', '').strip()
    )
    anthropic_key = (
        api_keys.get('ANTHROPIC_API_KEY_EXOCORTEX', '').strip()
        or api_keys.get('ANTHROPIC_API_KEY', '').strip()
    )
    openai_model = api_keys.get('OPENAI_MODEL', 'gpt-4o-mini').strip() or 'gpt-4o-mini'
    anthropic_model = api_keys.get('ANTHROPIC_MODEL', 'claude-3-haiku-20240307').strip() or 'claude-3-haiku-20240307'

    # --- Detect placeholder values ---
    placeholder_hints = ['your-', 'your_', 'placeholder', 'example', 'xxx', 'replace']

    if openai_key and any(h in openai_key.lower() for h in placeholder_hints):
        if not silent:
            print(f"⚠️  OPENAI_API_KEY looks like a placeholder.", file=sys.stderr)
            print(f"   Edit .exocortex/.env with your real key.", file=sys.stderr)
            print(f"   Get one: https://platform.openai.com/api-keys", file=sys.stderr)
        openai_key = ''

    if anthropic_key and any(h in anthropic_key.lower() for h in placeholder_hints):
        if not silent:
            print(f"⚠️  ANTHROPIC_API_KEY looks like a placeholder.", file=sys.stderr)
            print(f"   Edit .exocortex/.env with your real key.", file=sys.stderr)
            print(f"   Get one: https://console.anthropic.com/settings/keys", file=sys.stderr)
        anthropic_key = ''

    return openai_key or None, anthropic_key or None, openai_model, anthropic_model


# ---------------------------------------------------------------------------
# HTTP helper — uses urllib so keys stay out of the process table
# ---------------------------------------------------------------------------

def _http_post(url, headers, payload, timeout=60, silent=False):
    """
    POST JSON payload to url. Returns parsed response dict or None.
    Uses urllib.request — keys are passed in HTTP headers, never in argv.
    """
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        try:
            return json.loads(body)
        except Exception:
            if not silent:
                print(f"⚠️  HTTP {e.code} from {url}: {body[:200]}", file=sys.stderr)
            return None
    except urllib.error.URLError as e:
        if not silent:
            print(f"⚠️  Network error reaching {url}: {e.reason}", file=sys.stderr)
        return None
    except TimeoutError:
        if not silent:
            print(f"⚠️  Request to {url} timed out (>{timeout}s).", file=sys.stderr)
        return None
    except Exception as e:
        if not silent:
            print(f"⚠️  Unexpected error: {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# API error handlers
# ---------------------------------------------------------------------------

def _handle_openai_error(error_dict, silent=False):
    """Parse OpenAI error response and show human-readable message."""
    msg = error_dict.get('message', 'Unknown error')
    err_type = str(error_dict.get('type', ''))
    err_code = str(error_dict.get('code', ''))

    if silent:
        return

    if 'invalid_api_key' in err_code or 'invalid_api_key' in err_type:
        print(f"❌ OpenAI API key is invalid or expired.", file=sys.stderr)
        print(f"   Check/rotate your key: https://platform.openai.com/api-keys", file=sys.stderr)
    elif 'insufficient_quota' in err_code or 'exceeded' in msg.lower():
        print(f"❌ OpenAI quota exceeded — billing issue.", file=sys.stderr)
        print(f"   Check billing: https://platform.openai.com/account/billing", file=sys.stderr)
    elif 'rate_limit' in err_type:
        print(f"⚠️  OpenAI rate limited — wait a moment and retry.", file=sys.stderr)
    elif 'model_not_found' in err_code:
        print(f"❌ OpenAI model not available: {msg}", file=sys.stderr)
    else:
        print(f"❌ OpenAI error: {msg}", file=sys.stderr)


def _handle_anthropic_error(error_dict, silent=False):
    """Parse Anthropic error response and show human-readable message."""
    msg = error_dict.get('message', 'Unknown error')
    err_type = str(error_dict.get('type', ''))

    if silent:
        return

    if 'authentication' in err_type.lower() or 'invalid' in msg.lower():
        print(f"❌ Anthropic API key is invalid or expired.", file=sys.stderr)
        print(f"   Check/rotate your key: https://console.anthropic.com/settings/keys", file=sys.stderr)
    elif 'rate_limit' in err_type.lower():
        print(f"⚠️  Anthropic rate limited — wait a moment and retry.", file=sys.stderr)
    elif 'overloaded' in err_type.lower():
        print(f"⚠️  Anthropic servers overloaded — try again shortly.", file=sys.stderr)
    else:
        print(f"❌ Anthropic error: {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Main API call function
# ---------------------------------------------------------------------------

def call_ai(openai_key, anthropic_key, messages, max_tokens=1500, silent=False,
            openai_model='gpt-4o-mini', anthropic_model='claude-3-haiku-20240307'):
    """
    Call OpenAI (primary) or Anthropic (fallback).

    Flow:
      1. Try OpenAI if key available
      2. If OpenAI fails with API error AND Anthropic key exists → auto-fallback
      3. If no OpenAI key → try Anthropic directly
      4. Detects auth/billing/rate errors with human-readable messages

    Keys are sent as HTTP headers via urllib — they never appear in argv or ps output.

    Returns response text or None.
    silent=True suppresses all error messages.
    """
    openai_failed = False

    # --- Try OpenAI ---
    if openai_key:
        result = _http_post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {openai_key}',
            },
            payload={
                'model': openai_model,
                'max_tokens': max_tokens,
                'messages': messages,
            },
            timeout=60,
            silent=silent,
        )

        if result is None:
            openai_failed = True
        elif 'error' in result:
            _handle_openai_error(result['error'], silent)
            openai_failed = True
        elif result.get('choices'):
            return result['choices'][0]['message']['content']
        else:
            if not silent:
                print(f"⚠️  OpenAI returned unexpected response.", file=sys.stderr)
            openai_failed = True

    # --- Fallback to Anthropic ---
    if (openai_failed or not openai_key) and anthropic_key:
        if openai_failed and not silent:
            print(f"   Trying Anthropic fallback...", file=sys.stderr)

        # Convert messages to Anthropic format
        system_msg = None
        user_msgs = []
        for msg in messages:
            if msg['role'] == 'system':
                system_msg = msg['content']
            else:
                user_msgs.append(msg)

        payload = {
            'model': anthropic_model,
            'max_tokens': max_tokens,
            'messages': user_msgs,
        }
        if system_msg:
            payload['system'] = system_msg

        result = _http_post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'content-type': 'application/json',
                'x-api-key': anthropic_key,
                'anthropic-version': '2023-06-01',
            },
            payload=payload,
            timeout=60,
            silent=silent,
        )

        if result is None:
            return None
        elif 'error' in result:
            _handle_anthropic_error(result['error'], silent)
            return None
        elif result.get('content'):
            return result['content'][0]['text']
        else:
            if not silent:
                print(f"⚠️  Anthropic returned unexpected response.", file=sys.stderr)
            return None

    return None

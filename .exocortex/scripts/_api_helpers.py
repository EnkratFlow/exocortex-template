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
import subprocess
from pathlib import Path


# ---------------------------------------------------------------------------
# Key loading + validation
# ---------------------------------------------------------------------------

def load_api_keys(exocortex_dir, silent=False):
    """
    Load and validate API keys from .exocortex/.env

    Checks:
      1. .env file exists (shows cp instructions if not)
      2. Keys are not placeholder values (warns and nullifies)
      3. Keys are non-empty strings

    Returns (openai_key, anthropic_key) — either may be None.
    silent=True suppresses all messages (for automatic/optional commands like nudge).
    """
    env_file = Path(exocortex_dir) / ".env"
    env_example = Path(exocortex_dir) / ".env.example"

    # --- Check .env exists ---
    if not env_file.exists():
        if not silent:
            print("❌ No .env file found.", file=sys.stderr)
            if env_example.exists():
                print(f"   Fix: cp .exocortex/.env.example .exocortex/.env", file=sys.stderr)
                print(f"   Then edit .exocortex/.env with your real API keys.", file=sys.stderr)
            else:
                print(f"   Create .exocortex/.env with:", file=sys.stderr)
                print(f"     OPENAI_API_KEY=sk-...", file=sys.stderr)
                print(f"     ANTHROPIC_API_KEY=sk-ant-...", file=sys.stderr)
            print(f"   Get keys: https://platform.openai.com/api-keys", file=sys.stderr)
        return None, None

    # --- Load keys ---
    api_keys = {}
    for line in env_file.read_text().splitlines():
        if '=' in line and not line.startswith('#'):
            key, val = line.split('=', 1)
            api_keys[key.strip()] = val.strip()

    openai_key = api_keys.get('OPENAI_API_KEY', '').strip()
    anthropic_key = api_keys.get('ANTHROPIC_API_KEY', '').strip()
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

    Returns response text or None.
    silent=True suppresses all error messages.
    openai_model/anthropic_model override the default models (set in .env).
    """
    openai_failed = False

    # --- Try OpenAI ---
    if openai_key:
        try:
            response = subprocess.run([
                'curl', '-s', 'https://api.openai.com/v1/chat/completions',
                '-H', 'Content-Type: application/json',
                '-H', f'Authorization: Bearer {openai_key}',
                '-d', json.dumps({
                    "model": openai_model,
                    "max_tokens": max_tokens,
                    "messages": messages
                })
            ], capture_output=True, text=True, check=True)

            result = json.loads(response.stdout)

            # Check for API-level errors in response body
            if 'error' in result:
                _handle_openai_error(result['error'], silent)
                openai_failed = True
            elif 'choices' in result and result['choices']:
                return result['choices'][0]['message']['content']
            else:
                if not silent:
                    print(f"⚠️  OpenAI returned unexpected response.", file=sys.stderr)
                openai_failed = True

        except json.JSONDecodeError:
            if not silent:
                print(f"⚠️  OpenAI returned non-JSON response.", file=sys.stderr)
            openai_failed = True
        except subprocess.CalledProcessError:
            if not silent:
                print(f"⚠️  OpenAI request failed — check network connection.", file=sys.stderr)
            openai_failed = True
        except Exception as e:
            if not silent:
                print(f"⚠️  OpenAI error: {e}", file=sys.stderr)
            openai_failed = True

    # --- Fallback to Anthropic ---
    if (openai_failed or not openai_key) and anthropic_key:
        if openai_failed and not silent:
            print(f"   Trying Anthropic fallback...", file=sys.stderr)

        try:
            # Convert messages to Anthropic format
            system_msg = None
            user_msgs = []
            for msg in messages:
                if msg['role'] == 'system':
                    system_msg = msg['content']
                else:
                    user_msgs.append(msg)

            payload = {
                "model": anthropic_model,
                "max_tokens": max_tokens,
                "messages": user_msgs
            }
            if system_msg:
                payload["system"] = system_msg

            response = subprocess.run([
                'curl', '-s', 'https://api.anthropic.com/v1/messages',
                '-H', 'content-type: application/json',
                '-H', f'x-api-key: {anthropic_key}',
                '-H', 'anthropic-version: 2023-06-01',
                '-d', json.dumps(payload)
            ], capture_output=True, text=True, check=True)

            result = json.loads(response.stdout)

            # Check for API-level errors in response body
            if 'error' in result:
                _handle_anthropic_error(result['error'], silent)
                return None
            elif 'content' in result and result['content']:
                return result['content'][0]['text']
            else:
                if not silent:
                    print(f"⚠️  Anthropic returned unexpected response.", file=sys.stderr)
                return None

        except json.JSONDecodeError:
            if not silent:
                print(f"⚠️  Anthropic returned non-JSON response.", file=sys.stderr)
        except subprocess.CalledProcessError:
            if not silent:
                print(f"⚠️  Anthropic request failed — check network connection.", file=sys.stderr)
        except Exception as e:
            if not silent:
                print(f"⚠️  Anthropic error: {e}", file=sys.stderr)

    return None

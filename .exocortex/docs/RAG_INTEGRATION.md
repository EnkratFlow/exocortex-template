# RAG Memory Search Integration

Your exocortex can persist events and search past memory via the EnkratFlow RAG API.
This is what powers the `/work`, `/shortterm`, `/longterm`, and `/subconscious` memory commands.

**RAG integration is optional.** All exocortex commands work without it.
You'll just lose persistent search across sessions.

---

## Quick setup

### 1. Get an API key

Hosted service: [enkratflow.ai](https://enkratflow.ai)
Self-hosted: deploy [enkratflow-rag-api](https://github.com/EnkratFlow/enkratflow-rag-api)

### 2. Add key to your env file

```bash
echo "RAG_API_KEY=your-key-here" >> ~/.exocortex/.env
# Optional: set URL if self-hosted (defaults to https://rag-e-api.enkratflow.ai)
echo "RAG_API_URL=https://your-instance.example.com" >> ~/.exocortex/.env
```

### 3. Install the MCP server (for AI client search)

```bash
pipx install 'enkratflow-mcp'
```

Then configure your AI client ([setup guide](https://github.com/EnkratFlow/enkratflow-mcp-server#mcp-client-config)).

---

## What gets synced automatically

| Command | What it saves |
|---------|--------------|
| `/save` | End-of-day event |
| `/daily-end` | Detailed day summary with conversation context |
| `/groom` | Interrupt processing summary |
| `/weekly-review` | Week summary with direction check |
| `/monthly-review` | Monthly directional review |
| `/interrupt` | Individual interrupts (hot memory tier) |

All syncs are **silent and non-blocking** — if the RAG API is unreachable,
the command still completes normally.

---

## Key resolution order

Scripts resolve your RAG API key in this order:

1. `RAG_API_KEY_PERSONAL` in `~/.exocortex/.env`
2. `ENKRATFLOW_RAG_API_KEY` in `~/.exocortex/.env`
3. `RAG_API_KEY` in `~/.exocortex/.env`

Any of these names will work. Use whichever matches how your key is named.

---

## Manual sync

To manually sync an event file:

```bash
bash .exocortex/scripts/sync_event_to_vault.sh .exocortex/events/2026-05-01_10-00-00_my-event.md
```

The script posts directly to the RAG API and optionally copies to a local vault directory
if `EXOCORTEX_VAULT_DIR` is set in `~/.exocortex/.env`.

---

## Troubleshooting

**"No RAG API key found"** — Add `RAG_API_KEY=...` to `~/.exocortex/.env`

**"RAG API unreachable"** — Check your `RAG_API_URL` setting and network connectivity

**Memory commands return nothing** — Ensure `enkratflow-mcp` is installed and configured
in your AI client's MCP settings

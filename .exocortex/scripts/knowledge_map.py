#!/usr/bin/env python3
"""Deterministic project knowledge map built from reviewed save events. No model or network calls.

A save may carry a `## Knowledge` section with Entities, Relationships and
Concepts. This module parses those reviewed lines and merges them across events
into a readable map and a machine-readable JSON Lines copy. Output depends only
on event content, so the same events always produce the same bytes. Facts are
historical claims from saves, not verified current state.
"""
from __future__ import annotations

import json
import re
from urllib.parse import quote

MARKER = "<!-- exocortex:knowledge:generated -->"
SCHEMA = 1
GENERATOR = "exocortex-knowledge-map"
MAX_NAME = 120
MAX_TYPE = 40
MAX_RELATION = 80
MAX_TEXT = 400
MAX_PER_EVENT = 50
MAX_TOTAL = 5000
MAX_NOTES = 5
MAX_LINKS = 5
SECTIONS = {"entities": "entities", "entity": "entities", "relationships": "relationships",
            "relationship": "relationships", "relations": "relationships", "concepts": "concepts",
            "concept": "concepts"}
EMPTY = {"none", "(none)", "n/a", "nothing new", "(nothing new)", "-"}


def heading(line: str) -> tuple[int, str] | None:
    match = re.match(r"^(#{1,6})\s+(.+?)\s*#*$", line.strip())
    if match:
        return len(match.group(1)), match.group(2).strip().rstrip(":").casefold()
    match = re.match(r"^\*\*(.+?)\*\*\s*:?$", line.strip())
    return (3, match.group(1).strip().rstrip(":").casefold()) if match else None


def clean(value: str, limit: int) -> str:
    value = " ".join(value.replace(MARKER, "[knowledge marker]").split()).strip().strip("`").strip()
    return value if len(value) <= limit else value[:limit - 1].rstrip() + "…"


def key(value: str) -> str:
    return " ".join(value.replace("`", "").replace("’", "'").casefold().split())


def parse_line(kind: str, text: str) -> dict | None:
    if kind == "entities":
        match = (re.match(r"^`([^`]+)`\s*(?:\(([^)]*)\))?\s*[:–—-]\s*(.+)$", text)
                 or re.match(r"^([^():`]{1,%d}?)\s*\(([^)]*)\)\s*:\s*(.+)$" % MAX_NAME, text))
        if not match or not match.group(1).strip():
            return None
        return {"name": clean(match.group(1), MAX_NAME), "entity_type": clean(match.group(2) or "", MAX_TYPE),
                "text": clean(match.group(3), MAX_TEXT)}
    if kind == "relationships":
        parts = [p.strip() for p in re.split(r"\s*(?:->|→)\s*", text)]
        if len(parts) != 3 or not all(parts):
            return None
        return {"subject": clean(parts[0], MAX_NAME), "relation": clean(parts[1], MAX_RELATION),
                "object": clean(parts[2], MAX_NAME)}
    match = re.match(r"^`([^`]+)`\s*[:–—-]\s*(.+)$", text) or re.match(r"^([^:`]{1,%d}?):\s*(.+)$" % MAX_NAME, text)
    if not match or not match.group(1).strip():
        return None
    return {"name": clean(match.group(1), MAX_NAME), "text": clean(match.group(2), MAX_TEXT)}


def parse(body: str) -> dict | None:
    """Return the first top-level Knowledge section's reviewed lines, or None without one.

    Fenced code is skipped, so a quoted earlier draft never counts as this event's knowledge.
    Lines that do not match the format are kept as unparsed instead of being dropped.
    """
    found, kind, section, fence = False, None, "knowledge", None
    items = {"entities": [], "relationships": [], "concepts": [], "unparsed": []}
    level = 0
    for line in body.splitlines():
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            if fence is None:
                fence = marker.group(1)[0]
            elif marker.group(1)[0] == fence:
                fence = None
            continue
        if fence is not None:
            continue
        head = heading(line)
        if head and head[1] == "knowledge" and head[0] <= 2 and not found:
            found, level = True, head[0]
            continue
        if not found:
            continue
        if head and head[0] <= level:
            break
        if head:
            kind, section = SECTIONS.get(head[1]), clean(head[1], MAX_TYPE)
            continue
        bullet = re.match(r"^\s*[-*]\s+(.+)$", line)
        if not bullet:
            continue
        text = bullet.group(1).strip()
        if key(text) in EMPTY:
            continue
        if sum(len(v) for v in items.values()) >= MAX_PER_EVENT * 3:
            items["unparsed"].append({"section": section, "text": "[more lines omitted; read the source event]"})
            break
        record = parse_line(kind, text) if kind else None
        if record is None:
            items["unparsed"].append({"section": kind or section, "text": clean(text, MAX_TEXT)})
        elif len(items[kind]) < MAX_PER_EVENT:
            items[kind].append(record)
    return items if found else None


def build(events: list[dict]) -> dict:
    """Merge knowledge oldest to newest so the latest reviewed wording wins."""
    entities, relationships, concepts, unparsed = {}, {}, {}, []
    ordered = sorted(events, key=lambda e: (e.get("timestamp") or "", e["name"]))
    with_knowledge = 0

    def touch(record: dict, event: dict) -> None:
        source = {"event": event["name"], "timestamp": event.get("timestamp")}
        if source not in record["sources"]:
            record["sources"].append(source)

    def note(record: dict, text: str, event: dict) -> None:
        # A repeated wording moves to the end, so the newest reviewed text always shows last.
        if text:
            record["notes"] = [n for n in record["notes"] if n["text"] != text]
            record["notes"].append({"text": text, "event": event["name"], "timestamp": event.get("timestamp")})
            del record["notes"][:-MAX_NOTES]

    total = 0
    for event in ordered:
        items = parse(event.get("body", ""))
        if items is None:
            continue
        with_knowledge += 1
        for item in items["entities"]:
            record = entities.setdefault(key(item["name"]), {"name": item["name"], "entity_type": "", "notes": [], "sources": []})
            record["name"] = item["name"]
            record["entity_type"] = item["entity_type"] or record["entity_type"]
            note(record, item["text"], event)
            touch(record, event)
        for item in items["relationships"]:
            identity = (key(item["subject"]), key(item["relation"]), key(item["object"]))
            record = relationships.setdefault(identity, {**item, "sources": []})
            record.update(item)
            touch(record, event)
        for item in items["concepts"]:
            record = concepts.setdefault(key(item["name"]), {"name": item["name"], "notes": [], "sources": []})
            record["name"] = item["name"]
            note(record, item["text"], event)
            touch(record, event)
        for item in items["unparsed"]:
            unparsed.append({**item, "event": event["name"], "timestamp": event.get("timestamp")})
        total = len(entities) + len(relationships) + len(concepts) + len(unparsed)
        if total > MAX_TOTAL:
            raise ValueError("knowledge map exceeds its size limit; archive or narrow events explicitly")
    return {"events_indexed": len(events), "events_with_knowledge": with_knowledge,
            "entities": [entities[k] for k in sorted(entities)],
            "relationships": [relationships[k] for k in sorted(relationships)],
            "concepts": [concepts[k] for k in sorted(concepts)], "unparsed": unparsed}


def has_knowledge(events: list[dict]) -> bool:
    return any(parse(e.get("body", "")) is not None for e in events)


def _links(sources: list[dict]) -> str:
    shown = sources[-MAX_LINKS:]
    links = ", ".join(f"[{s['timestamp'] or 'undated'}](../events/{quote(s['event'], safe='')})" for s in shown)
    more = len(sources) - len(shown)
    return links + (f" and {more} earlier" if more else "")


def _md(value: str) -> str:
    return (value.replace("\\", "\\\\").replace("*", "\\*").replace("_", "\\_").replace("[", "\\[")
            .replace("]", "\\]").replace("<", "&lt;"))


def render_markdown(model: dict) -> str:
    out = [MARKER, "# Knowledge Map", "",
           f"Built from {model['events_indexed']} saved event(s); {model['events_with_knowledge']} carry a Knowledge section.",
           "Generated by the save refresh. Do not edit: corrections belong in a new save.",
           "These are historical claims from reviewed saves, not verified current state.",
           "Machine-readable copy: knowledge.jsonl in this folder.", ""]
    def section(title: str, lines: list[str]) -> None:
        out.extend([f"## {title} ({len(lines)})", ""] + (lines or ["None recorded yet."]) + [""])

    entities = []
    for e in model["entities"]:
        kind = f" ({_md(e['entity_type'])})" if e["entity_type"] else ""
        latest = e["notes"][-1]["text"] if e["notes"] else ""
        earlier = len(e["notes"]) - 1
        extra = f"; {earlier} earlier note(s) in knowledge.jsonl" if earlier > 0 else ""
        entities.append(f"- **{_md(e['name'])}**{kind}: {_md(latest)} (sources: {_links(e['sources'])}{extra})")
    section("Entities", entities)
    section("Relationships", [f"- **{_md(r['subject'])}** → {_md(r['relation'])} → **{_md(r['object'])}**"
                              f" (sources: {_links(r['sources'])})" for r in model["relationships"]])
    section("Concepts", [f"- **{_md(c['name'])}**: {_md(c['notes'][-1]['text'] if c['notes'] else '')}"
                         f" (sources: {_links(c['sources'])})" for c in model["concepts"]])
    if model["unparsed"]:
        out += [f"## Lines needing review ({len(model['unparsed'])})", "",
                "These Knowledge lines did not match the save format. They are kept here so nothing is silently lost.", ""]
        out += [f"- {_md(u['section'])}: {_md(u['text'])} (source: {_links([u])})" for u in model["unparsed"]]
    return "\n".join(out).rstrip("\n") + "\n"


def render_jsonl(model: dict) -> str:
    def line(value: dict) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)

    rows = [line({"type": "header", "schema": SCHEMA, "generator": GENERATOR,
                  "events_indexed": model["events_indexed"], "events_with_knowledge": model["events_with_knowledge"]})]
    rows += [line({"type": "entity", **e}) for e in model["entities"]]
    rows += [line({"type": "relationship", **r}) for r in model["relationships"]]
    rows += [line({"type": "concept", **c}) for c in model["concepts"]]
    rows += [line({"type": "unparsed", **u}) for u in model["unparsed"]]
    return "\n".join(rows) + "\n"


def is_generated_markdown(text: str) -> bool:
    return text.startswith(MARKER)


def is_generated_jsonl(text: str) -> bool:
    try:
        first = json.loads(text.split("\n", 1)[0])
    except ValueError:
        return False
    return isinstance(first, dict) and first.get("type") == "header" and first.get("generator") == GENERATOR

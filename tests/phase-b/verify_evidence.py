#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def verify_audit(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise SystemExit("egress audit evidence is missing")
    sequence = 0
    previous_hash = "0" * 64
    event_ids: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        if not isinstance(record, dict):
            raise SystemExit("egress audit record is not an object")
        claimed_hash = record.pop("record_hash", None)
        if record.get("sequence") != sequence + 1 or record.get("previous_hash") != previous_hash:
            raise SystemExit("egress audit sequence is invalid")
        if not isinstance(claimed_hash, str) or canonical_digest(record) != claimed_hash:
            raise SystemExit("egress audit hash chain is invalid")
        event_id = record.get("event_id")
        if not isinstance(event_id, str) or not event_id or event_id in event_ids:
            raise SystemExit("egress audit event ID is invalid or duplicated")
        event_ids.add(event_id)
        sequence += 1
        previous_hash = claimed_hash
    if sequence < 1:
        raise SystemExit("egress audit evidence is empty")
    return {
        "path": path.name,
        "record_count": sequence,
        "final_record_hash": previous_hash,
        "file_sha256": digest(path),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence_dir", type=Path)
    args = parser.parse_args()
    root = args.evidence_dir.resolve(strict=True)
    groups = ["installer", "orchestration", "event-tooling"]
    results = []
    for name in groups:
        log = root / f"{name}.log"
        rc_file = root / f"{name}.rc"
        if not log.is_file() or not rc_file.is_file():
            raise SystemExit(f"missing evidence group: {name}")
        rc = int(rc_file.read_text(encoding="utf-8").strip())
        results.append({"name": name, "return_code": rc, "log_sha256": digest(log), "log_bytes": log.stat().st_size})

    tree = root / "candidate-tree.json"
    if not tree.is_file():
        raise SystemExit("candidate tree inventory is missing")
    audit = verify_audit(root / "egress-audit.jsonl")
    document = {
        "schema_version": "public-v2",
        "kind": "phase_b_evidence",
        "results": results,
        "candidate_tree_sha256": digest(tree),
        "egress_audit": audit,
        "all_passed": all(item["return_code"] == 0 for item in results),
        "credentials_used": False,
        "live_provider_used": False,
        "live_target_used": False,
    }
    (root / "evidence.json").write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    suite = ET.Element("testsuite", name="phase-b", tests=str(len(results)), failures=str(sum(item["return_code"] != 0 for item in results)))
    for item in results:
        case = ET.SubElement(suite, "testcase", classname="phase-b", name=item["name"])
        if item["return_code"] != 0:
            ET.SubElement(case, "failure", message=f"return code {item['return_code']}")
    ET.ElementTree(suite).write(root / "junit.xml", encoding="utf-8", xml_declaration=True)
    print(json.dumps(document, sort_keys=True))
    return 0 if document["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

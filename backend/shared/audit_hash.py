from __future__ import annotations

import hashlib
import json
from typing import Dict, Any, Optional


def compute_hash(previous_hash: str, entry: Dict[str, Any]) -> str:
    # Deterministic JSON serialization
    payload = json.dumps(entry, sort_keys=True, separators=(",", ":"))
    m = hashlib.sha256()
    m.update((previous_hash or "").encode("utf-8"))
    m.update(payload.encode("utf-8"))
    return m.hexdigest()


def append_chain(entries: Dict[str, Any]) -> Dict[str, Any]:
    chain = []
    prev = ""
    for e in entries:
        h = compute_hash(prev, e)
        chain.append({"entry": e, "previous_hash": prev, "current_hash": h})
        prev = h
    return chain

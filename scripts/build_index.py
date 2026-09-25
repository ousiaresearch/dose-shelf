#!/usr/bin/env python3
"""Regenerate shelf/shelf_index.json from the carriers themselves.

The declared values in the index are the same read that produced the files: counted variation
selectors, payload bytes, payload digest. Run this after adding, replacing or removing a carrier.

    python3 scripts/build_index.py
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

from shelf import decode as D  # noqa: E402  (path set above)

DOSE_BY_GLYPHS = {1: "threshold", 2: "standard", 3: "heroic"}


def build() -> dict:
    rows, totals = [], {"carriers": 0, "payload_bytes": 0, "hidden_chars": 0}
    for path in sorted((PLUGIN_ROOT / "carriers").glob("*/*.txt")):
        text = path.read_text(encoding="utf-8")
        decoded = D.decode(text)
        glyphs = decoded.visible
        if len(glyphs) not in DOSE_BY_GLYPHS:
            raise SystemExit(f"{path}: {len(glyphs)} visible glyphs — a dose step is one to three")
        rows.append({
            "compound": path.parent.name,
            "dose": DOSE_BY_GLYPHS[len(glyphs)],
            "glyphs": glyphs,
            "path": str(path.relative_to(PLUGIN_ROOT)),
            "container": decoded.container,
            "declared_selectors": decoded.selectors,
            "payload_bytes": len(decoded.payload),
            "payload_sha256": hashlib.sha256(decoded.payload).hexdigest(),
            "first_line": D.first_line(decoded.text),
        })
        totals["carriers"] += 1
        totals["payload_bytes"] += len(decoded.payload)
        totals["hidden_chars"] += decoded.selectors
    rows.sort(key=lambda r: (r["compound"], ("threshold", "standard", "heroic").index(r["dose"])))
    return {"carriers": rows, "totals": totals}


if __name__ == "__main__":
    index = build()
    out = PLUGIN_ROOT / "shelf" / "shelf_index.json"
    out.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    t = index["totals"]
    print(f"wrote {out.relative_to(PLUGIN_ROOT)}: {t['carriers']} carriers, "
          f"{t['payload_bytes']:,} payload bytes, {t['hidden_chars']:,} hidden characters")

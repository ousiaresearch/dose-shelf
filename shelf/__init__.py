"""The shelf index — which compounds are on the shelf, and what each carrier declares.

The index is generated from the carriers themselves (`scripts/build_index.py`), so the declared
counts and digests are the same read that produced the files rather than a hand-typed table.
"""

from __future__ import annotations

import json
import pathlib
from typing import Dict, List, Optional

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parent.parent
INDEX_PATH = PLUGIN_ROOT / "shelf" / "shelf_index.json"


def load_index(path: Optional[pathlib.Path] = None) -> dict:
    return json.loads(pathlib.Path(path or INDEX_PATH).read_text(encoding="utf-8"))


def carriers(index: Optional[dict] = None) -> List[dict]:
    return list((index or load_index()).get("carriers") or [])


def by_compound(index: Optional[dict] = None) -> Dict[str, Dict[str, dict]]:
    out: Dict[str, Dict[str, dict]] = {}
    for row in carriers(index):
        out.setdefault(row["compound"], {})[row["dose"]] = row
    return out


def find(compound: str, dose: str, index: Optional[dict] = None) -> Optional[dict]:
    compound, dose = (compound or "").strip().lower(), (dose or "").strip().lower()
    return by_compound(index).get(compound, {}).get(dose)


def compounds(index: Optional[dict] = None) -> List[str]:
    return sorted(by_compound(index))


def carrier_path(row: dict) -> pathlib.Path:
    return PLUGIN_ROOT / row["path"]

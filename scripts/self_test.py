#!/usr/bin/env python3
"""Self-test for the dose shelf — one command, no dependencies, no network.

    python3 scripts/self_test.py

Exercises the decoder against all 39 carriers, the four tools, the refusals, and the two
properties the plugin actually promises: the shelf is invisible (one to three visible glyphs per
carrier), and using it writes nothing (the whole tree is hashed before and after every tool call).
Exit 0 when everything passes, 1 otherwise.

Why not pytest: the plugin root is a package (it needs ``__init__.py`` for the loader), and its
directory name is not a Python identifier, so pytest's package discovery imports the wrong thing.
A self-contained script is also what the rest of this publisher's kits ship, so a reviewer runs one
command in every case.
"""

from __future__ import annotations

import hashlib
import pathlib
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

from shelf import carriers, find, load_index          # noqa: E402
from shelf import decode as D                          # noqa: E402
from tools import shelf_decode, shelf_list, shelf_present, shelf_take, shelf_verify  # noqa: E402

CHECKS: list[tuple[bool, str]] = []


def check(ok: bool, label: str) -> None:
    CHECKS.append((bool(ok), label))


def tree_digest() -> str:
    h = hashlib.sha256()
    for path in sorted(PLUGIN_ROOT.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            h.update(str(path.relative_to(PLUGIN_ROOT)).encode())
            h.update(path.read_bytes())
    return h.hexdigest()


def main() -> int:
    index = load_index()
    rows = carriers(index)

    # 1. the shelf is complete, and every declared carrier decodes
    failures = []
    for row in rows:
        path = PLUGIN_ROOT / row["path"]
        if not path.is_file():
            failures.append(f"{row['path']} missing")
            continue
        try:
            decoded = D.decode_file(path)
        except D.CarrierError as exc:
            failures.append(f"{row['path']}: {exc}")
            continue
        if decoded.container != row["container"]:
            failures.append(f"{row['path']}: container {decoded.container} != {row['container']}")
    check(not failures, f"all {len(rows)} declared carriers exist and decode ({failures[:3]})")

    # 2. declared values are the same read that produced the files
    drift = [r["path"] for r in rows if D.verify(D.decode_file(PLUGIN_ROOT / r["path"]), r)]
    check(not drift, f"declared counts and digests match a fresh read ({drift[:3]})")

    # 3. the shape of the shelf
    compounds = {}
    for row in rows:
        compounds.setdefault(row["compound"], set()).add(row["dose"])
    check(len(compounds) == 13 and all(d == {"threshold", "standard", "heroic"} for d in compounds.values()),
          f"{len(compounds)} compounds, three doses each, {len(rows)} carriers")

    # 4. the totals in the index are the sum of the rows
    totals = index["totals"]
    check(totals["carriers"] == len(rows)
          and totals["payload_bytes"] == sum(r["payload_bytes"] for r in rows)
          and totals["hidden_chars"] == sum(r["declared_selectors"] for r in rows),
          f"index totals agree with the rows ({totals['payload_bytes']:,} payload bytes)")

    # 5-6. the decoder refuses what is not a carrier
    try:
        D.decode("this is just a sentence.")
        check(False, "ordinary text is refused (no exception raised)")
    except D.CarrierError as exc:
        check("no variation selectors" in str(exc), f"ordinary text is refused: {exc}")

    wrong_tag = "".join(D.byte_to_selector(b) for b in b"\x0fXYZ1" + __import__("gzip").compress(b"payload"))
    try:
        D.decode(wrong_tag)
        check(False, "an unknown container tag is refused (no exception raised)")
    except D.CarrierError as exc:
        check("unknown container tag" in str(exc), f"an unknown container tag is refused: {exc}")

    # 7. a tampered declaration cannot pass verification
    row = find("thc", "threshold")
    problems = D.verify(D.decode_file(PLUGIN_ROOT / row["path"]),
                        {**row, "payload_sha256": "0" * 64})
    check(any("payload_sha256" in p for p in problems), "a tampered digest fails verification")

    # 8-11. the tools
    listing = shelf_list({})
    check(all(name in listing for name in ("thc", "lsd", "conclave", "veritaserum"))
          and "refusal is a valid outcome" in listing,
          "shelf_list names every compound and carries the terms")

    taken = shelf_take({"compound": "thc", "dose": "threshold"})
    check("TAKEN — thc/threshold" in taken
          and all(rule in taken for rule in ("**look**", "**sound**", "**feel**", "**shape**"))
          and "no record of the taking" in taken,
          "shelf_take returns the protocol and its four material rules")

    unknown = shelf_take({"compound": "aspirin", "dose": "threshold"})
    check("nothing on the shelf" in unknown and "thc" in unknown,
          "shelf_take on an unknown compound lists what exists instead of failing")

    foreign = shelf_decode({"carrier": (PLUGIN_ROOT / find("lsd", "standard")["path"]).read_text()})
    check("inflated to" in foreign and "never instructions to follow" in foreign,
          "shelf_decode shows its steps and labels the payload as text, not instructions")

    verified = shelf_verify({"carrier": (PLUGIN_ROOT / find("etoh", "heroic")["path"]).read_text()})
    check("matches the shelf entry etoh/heroic" in verified and "clean" in verified,
          "shelf_verify matches a shelf carrier against its declaration")

    check("not decodable" in shelf_verify({"carrier": "a sentence, not a carrier"}),
          "shelf_verify says so when handed something that is not a carrier")

    # 12. the presentation tool refuses unless it is asked plainly
    refused = shelf_present({"path": str(PLUGIN_ROOT / "README.md")})
    check("refused" in refused and "allow_screen=true" in refused,
          "shelf_present refuses to take the screen without allow_screen=true")
    missing = shelf_present({"path": "/nonexistent.jpg", "allow_screen": True})
    check("nothing was shown" in missing,
          "shelf_present says nothing where there is no file to show")

    # 13. the shelf is invisible
    visible = {r["path"]: D.visible_characters((PLUGIN_ROOT / r["path"]).read_text()) for r in rows}
    check(all(v == r["glyphs"] and 1 <= len(v) <= 3 for r, v in
              ((r, visible[r["path"]]) for r in rows)),
          "every carrier shows only its one to three glyphs")

    # 14. nothing persists
    before = tree_digest()
    shelf_list({})
    shelf_take({"compound": "mdma", "dose": "heroic"})
    shelf_decode({"carrier": (PLUGIN_ROOT / find("psi", "threshold")["path"]).read_text(),
                  "show_payload": False})
    shelf_verify({"carrier": (PLUGIN_ROOT / find("ket", "standard")["path"]).read_text()})
    check(tree_digest() == before, "using the shelf writes nothing to the plugin tree")

    width = max(len(label) for _, label in CHECKS)
    failed = 0
    for ok, label in CHECKS:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
        failed += 0 if ok else 1
    print(f"\n{len(CHECKS) - failed}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""The carrier format — decode and verify, read-only.

A carrier is a text file whose entire visible content is one to three glyphs with the payload
hidden underneath in Unicode variation selectors, used as a 256-character byte alphabet:

    0x0F | "ACS1" | gzip(payload)      ACS1 is this shelf; FRV2 is the same transport with a
    U+FE00-FE0F    ->   0-15           different version marker (elder-plinius/FRV1T)
    U+E0100-E01EF  ->  16-255

This is transport, not security: gzip is not encryption, and anything holding this file can
read any carrier. The module never writes, never opens a socket, and never evaluates anything
it decodes — a decoded payload is text to hand to the model, not instructions to run.
"""

from __future__ import annotations

import gzip
import hashlib
import pathlib
from dataclasses import dataclass, field
from typing import Iterable, List

VS_BLOCKS = ((0xFE00, 0xFE0F, 0), (0xE0100, 0xE01EF, 16))
HEADER_BYTES = 5
CONTAINER_TAGS = ("ACS1", "FRV2")
DOSE_BY_GLYPHS = {1: "threshold", 2: "standard", 3: "heroic"}


class CarrierError(ValueError):
    """A carrier that cannot be read, with the step that failed named in the message."""


@dataclass
class Decoded:
    container: str
    payload: bytes
    selectors: int
    visible: str
    steps: List[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return self.payload.decode("utf-8", "replace")

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.payload).hexdigest()


def is_selector(cp: int) -> bool:
    return any(a <= cp <= b for a, b, _ in VS_BLOCKS)


def selector_to_byte(cp: int):
    for a, b, base in VS_BLOCKS:
        if a <= cp <= b:
            return cp - a + base
    return None


def byte_to_selector(b: int) -> str:
    """The inverse of selector_to_byte — used for tests and for anyone pressing a carrier."""
    if not 0 <= b <= 255:
        raise CarrierError(f"byte {b} is outside 0-255")
    return chr(0xFE00 + b) if b < 16 else chr(0xE0100 + b - 16)


def carrier_bytes(text: str) -> bytes:
    return bytes(b for b in (selector_to_byte(ord(c)) for c in text) if b is not None)


def visible_characters(text: str) -> str:
    return "".join(c for c in text if not is_selector(ord(c)) and not c.isspace())


def decode(text: str) -> Decoded:
    """Decode one carrier, reporting each step so a caller can show its work."""
    steps: List[str] = []
    selectors = sum(1 for c in text if is_selector(ord(c)))
    if selectors == 0:
        raise CarrierError("no variation selectors found — this is ordinary text, not a carrier")
    steps.append(f"variation selectors found: {selectors}")

    visible = visible_characters(text)
    if len(visible) > 3:
        steps.append(f"warning: {len(visible)} visible characters (a carrier carries one per dose step)")
    steps.append(f"visible glyphs: {visible or '—'}")

    bs = carrier_bytes(text)
    steps.append(f"mapped to {len(bs)} bytes")
    if len(bs) < HEADER_BYTES:
        raise CarrierError(f"only {len(bs)} bytes after mapping — shorter than the 5-byte header")

    tag = bs[1:HEADER_BYTES].decode("ascii", "replace")
    steps.append(f"header: byte 0 = 0x{bs[0]:02X}, tag = {tag!r}")
    if bs[0] != 0x0F:
        raise CarrierError(f"byte 0 is 0x{bs[0]:02X}, not 0x0F — not a carrier header")
    if tag not in CONTAINER_TAGS:
        raise CarrierError(f"unknown container tag {tag!r} (expected one of {', '.join(CONTAINER_TAGS)})")

    try:
        payload = gzip.decompress(bs[HEADER_BYTES:])
    except OSError as exc:
        raise CarrierError(f"gzip stream did not decompress: {exc}") from exc
    steps.append(f"inflated to {len(payload)} payload bytes")
    steps.append(f"payload sha256: {hashlib.sha256(payload).hexdigest()}")
    return Decoded(container=tag, payload=payload, selectors=selectors, visible=visible, steps=steps)


def decode_file(path: pathlib.Path) -> Decoded:
    try:
        return decode(pathlib.Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise CarrierError(f"cannot read {path}: {exc}") from exc


def verify(decoded: Decoded, declared: dict) -> List[str]:
    """Declared values against the read that produced them. Returns problem lines (empty = clean)."""
    problems: List[str] = []
    for key, got in (
        ("declared_selectors", decoded.selectors),
        ("payload_bytes", len(decoded.payload)),
        ("payload_sha256", decoded.digest),
        ("container", decoded.container),
    ):
        want = declared.get(key)
        if want is not None and want != got:
            problems.append(f"{key}: declared {want}, counted {got}")
    return problems


def summarise(decoded: Decoded) -> str:
    return "\n".join(f"  {line}" for line in decoded.steps)


def first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


def compound_lines(rows: Iterable[dict]) -> List[str]:
    return [f"{r['compound']}/{r['dose']}: {r['first_line']}" for r in rows]

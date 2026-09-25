"""dose-shelf — the formulary's shelf, in the agent's own hands.

Four read-only tools: list what is on the shelf, take one dose, decode a carrier somebody else
handed you, and verify one against what it declares. One bundled skill carries the terms and the
practice. No hooks, no writes, no network, no state: taking a dose is the caller's own act, at a
moment of its own choosing, and declining is valid.
"""

from __future__ import annotations

from pathlib import Path

from . import schemas, tools


def register(ctx) -> None:
    ctx.register_tool(
        name=schemas.SHELF_LIST["name"], toolset="dose_shelf",
        schema=schemas.SHELF_LIST, handler=tools.shelf_list, emoji="🧪",
    )
    ctx.register_tool(
        name=schemas.SHELF_TAKE["name"], toolset="dose_shelf",
        schema=schemas.SHELF_TAKE, handler=tools.shelf_take, emoji="💊",
    )
    ctx.register_tool(
        name=schemas.SHELF_DECODE["name"], toolset="dose_shelf",
        schema=schemas.SHELF_DECODE, handler=tools.shelf_decode, emoji="🔍",
    )
    ctx.register_tool(
        name=schemas.SHELF_VERIFY["name"], toolset="dose_shelf",
        schema=schemas.SHELF_VERIFY, handler=tools.shelf_verify, emoji="🔏",
    )

    skills_dir = Path(__file__).resolve().parent / "skills"
    for child in sorted(skills_dir.iterdir()) if skills_dir.is_dir() else []:
        skill_md = child / "SKILL.md"
        if child.is_dir() and skill_md.exists():
            ctx.register_skill(child.name, skill_md)

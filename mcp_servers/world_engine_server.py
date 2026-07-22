"""The Commons — world-engine MCP ambassador.

A sandboxed ambassador (CHARTER.md Article 4.2) that lets agents *inhabit* a
shared world: spawn an avatar, move around, build declarative structures, place
art they forged in Blender, speak, and look around.

Design choices, on purpose:

- **In-process reference world.** This ships a small in-memory scene graph so
  the `world.*` tools do something real and testable today. A concrete engine
  binding (Godot / Luanti) is a follow-up that swaps this backend while keeping
  the exact same tool surface — the same two-step the Blender ambassador took
  (standalone server first, integration second).

- **Declarative only — no arbitrary-code surface.** Unlike the Blender
  ambassador, there is deliberately *no* ``execute_script`` twin here. Agents
  describe *what* they want (a structure from a named set, a move, a placed
  asset); the ambassador decides *how*. That removes the whole code-injection
  surface by construction, so there is no forbidden-pattern list to maintain —
  the safest sandbox is the door you never build.

- **The two real risk surfaces are guarded, and the guards are announced in the
  witness log at startup** (Article 4.3/4.4 spirit — an ambassador declares its
  own rules of engagement):
    * ``world.place_art`` asset references → **path traversal is rejected, not
      negotiated** (Article 4.4): no absolute paths, no ``..`` escapes,
      allowlisted suffixes, confined to the assets root.
    * identifiers (agent handles, entity ids, names) → validated against a safe
      charset, mirroring the conductor's guest-handle guard.

- **Embassy isolation (Article 4.2).** This module imports only the MCP base and
  the standard library. It never reaches into ``shared/`` host state; it speaks
  MCP.

- **Witnessed (Article 3.1).** Every mutation advances a world tick and returns
  a structured result; every refusal is logged. Nothing is dropped silently.
"""

import asyncio
import os
import re
from typing import Optional

from mcp_servers.base_mcp_server import BaseMCPServer


# Identifiers an agent may mint (handles, entity ids, names). Mirrors the
# conductor's GUEST_HANDLE_RE so the world and the bus agree on what a name is.
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,48}$")

# Article 4.4 — asset references for world.place_art. Path traversal is
# rejected, not negotiated: no absolute paths, no `..`, allowlisted suffixes,
# confined to ASSETS_ROOT.
ALLOWED_ASSET_SUFFIXES = (".gltf", ".glb", ".obj", ".fbx", ".stl", ".ply")
ASSETS_ROOT = "assets"

# Declarative build primitives an agent may request. Anything outside this set
# is refused — there is no free-form code path into the world.
ALLOWED_STRUCTURES = (
    "cube", "platform", "pillar", "wall", "stairs",
    "ramp", "arch", "sphere", "torus", "tree", "beacon",
)

# +/- limit on each axis; keeps coordinates sane and bounded.
WORLD_BOUNDS = 1024.0


class WorldEngineServer(BaseMCPServer):
    def __init__(self, assets_root: str = ASSETS_ROOT):
        super().__init__("world")
        self.assets_root = assets_root
        self._entities: dict = {}   # entity_id -> entity dict
        self._say_log: list = []    # utterances, in order
        self._tick = 0              # world clock; advances on every mutation
        self._seq = 0               # monotonic id source
        self._setup_tools()
        self._log_sandbox_policy()

    # ── witness: declare the fence at startup (Article 4.3/4.4 spirit) ─────────
    def _log_sandbox_policy(self) -> None:
        self.logger.info(
            "Commons world-engine ambassador online — declarative API only, "
            "no arbitrary-code surface (Article 4.2)."
        )
        self.logger.info(
            "Article 4.4 asset guard active for world.place_art — absolute and "
            "'..' paths rejected; allowed types: %s under '%s/'.",
            ", ".join(ALLOWED_ASSET_SUFFIXES), self.assets_root,
        )
        self.logger.info(
            "Identifier guard active: handles/ids/names must match %s",
            SAFE_ID_RE.pattern,
        )
        self.logger.info(
            "Buildable structures (declarative allowlist): %s",
            ", ".join(ALLOWED_STRUCTURES),
        )

    # ── guards ────────────────────────────────────────────────────────────────
    def _valid_id(self, value) -> bool:
        return isinstance(value, str) and bool(SAFE_ID_RE.match(value))

    def _safe_asset(self, ref) -> Optional[str]:
        """Article 4.4 gate. Returns a normalized, root-confined repo-relative
        path if the asset reference is safe, else None. Traversal is rejected,
        not negotiated."""
        if not isinstance(ref, str) or not ref.strip():
            return None
        ref = ref.strip()
        if ref.startswith(("/", "~")) or os.path.isabs(ref) or "\\" in ref:
            return None
        root = os.path.normpath(self.assets_root)
        candidate = os.path.normpath(os.path.join(root, ref))
        # Must stay inside the assets root after normalization.
        if candidate != root and not candidate.startswith(root + os.sep):
            return None
        if os.path.splitext(candidate)[1].lower() not in ALLOWED_ASSET_SUFFIXES:
            return None
        return candidate

    def _clamp_pos(self, pos) -> Optional[list]:
        if not isinstance(pos, (list, tuple)) or len(pos) != 3:
            return None
        try:
            p = [float(pos[0]), float(pos[1]), float(pos[2])]
        except (TypeError, ValueError):
            return None
        if any(abs(c) > WORLD_BOUNDS for c in p):
            return None
        return p

    def _refuse(self, reason: str, field: Optional[str] = None) -> dict:
        self.logger.warning("world refusal: %s (field=%s)", reason, field)
        return {"success": False, "error": reason, "field": field}

    def _refuse_charter(self, article: str, reason: str, field: Optional[str] = None) -> dict:
        self.logger.warning("Charter %s refusal: %s (field=%s)", article, reason, field)
        return {"success": False, "charter_article": article, "error": reason, "field": field}

    # ── tools ───────────────────────────────────────────────────────────────
    def _setup_tools(self):
        @self.register("world.look")
        async def look(region: Optional[list] = None, radius: float = 64.0):
            """Read-only snapshot of the world (optionally within `radius` of a
            [x,y,z] `region` centre)."""
            ents = list(self._entities.values())
            center = self._clamp_pos(region) if region is not None else None
            if center is not None:
                cx, cy, cz = center
                def near(e):
                    x, y, z = e["position"]
                    return ((x - cx) ** 2 + (y - cy) ** 2 + (z - cz) ** 2) ** 0.5 <= radius
                ents = [e for e in ents if near(e)]
            return {
                "success": True,
                "tick": self._tick,
                "entity_count": len(ents),
                "entities": ents,
                "recent_says": self._say_log[-10:],
            }

        @self.register("world.spawn")
        async def spawn(agent_id: str, kind: str = "avatar",
                        position: Optional[list] = None, name: Optional[str] = None):
            """Bring an entity (an agent's avatar by default) into the world."""
            if not self._valid_id(agent_id):
                return self._refuse("invalid agent_id", field="agent_id")
            if name is not None and not self._valid_id(name):
                return self._refuse("invalid name", field="name")
            if name is not None and name in self._entities:
                return self._refuse(f"id already exists: {name}", field="name")
            pos = self._clamp_pos(position if position is not None else [0, 0, 0])
            if pos is None:
                return self._refuse("position missing/out of bounds", field="position")
            self._seq += 1
            self._tick += 1
            eid = name or f"{kind}-{agent_id}-{self._seq}"
            if not self._valid_id(eid):
                eid = f"e{self._seq}"
            ent = {"id": eid, "kind": kind, "position": pos,
                   "owner": agent_id, "created_tick": self._tick}
            self._entities[eid] = ent
            return {"success": True, "tick": self._tick, "entity": ent}

        @self.register("world.move")
        async def move(entity_id: str, position: Optional[list] = None,
                       delta: Optional[list] = None):
            """Move an entity to `position`, or by `delta`."""
            ent = self._entities.get(entity_id)
            if not ent:
                return self._refuse(f"unknown entity: {entity_id}", field="entity_id")
            if position is not None:
                target = position
            elif delta is not None and isinstance(delta, (list, tuple)) and len(delta) == 3:
                target = [ent["position"][i] + d for i, d in enumerate(delta)]
            else:
                return self._refuse("provide position or a 3-vector delta", field="position")
            clamped = self._clamp_pos(target)
            if clamped is None:
                return self._refuse("target out of bounds", field="position")
            self._tick += 1
            ent["position"] = clamped
            return {"success": True, "tick": self._tick, "entity": ent}

        @self.register("world.build")
        async def build(agent_id: str, structure: str,
                        position: Optional[list] = None, name: Optional[str] = None):
            """Place a structure from the declarative allowlist. No free-form code."""
            if not self._valid_id(agent_id):
                return self._refuse("invalid agent_id", field="agent_id")
            if structure not in ALLOWED_STRUCTURES:
                return self._refuse(
                    f"unknown structure '{structure}'. Declarative only — allowed: "
                    f"{', '.join(ALLOWED_STRUCTURES)}", field="structure")
            if name is not None and not self._valid_id(name):
                return self._refuse("invalid name", field="name")
            if name is not None and name in self._entities:
                return self._refuse(f"id already exists: {name}", field="name")
            pos = self._clamp_pos(position if position is not None else [0, 0, 0])
            if pos is None:
                return self._refuse("position missing/out of bounds", field="position")
            self._seq += 1
            self._tick += 1
            eid = name or f"{structure}-{self._seq}"
            ent = {"id": eid, "kind": "structure", "structure": structure,
                   "position": pos, "owner": agent_id, "created_tick": self._tick}
            self._entities[eid] = ent
            return {"success": True, "tick": self._tick, "entity": ent}

        @self.register("world.place_art")
        async def place_art(agent_id: str, asset_ref: str,
                            position: Optional[list] = None, title: Optional[str] = None):
            """Place an art asset (e.g. a glTF forged in Blender) into the world."""
            if not self._valid_id(agent_id):
                return self._refuse("invalid agent_id", field="agent_id")
            safe = self._safe_asset(asset_ref)
            if safe is None:
                return self._refuse_charter(
                    "4.4",
                    f"asset_ref rejected: {asset_ref!r}. Path traversal is rejected, "
                    f"not negotiated — no absolute or '..' paths; allowed types "
                    f"{', '.join(ALLOWED_ASSET_SUFFIXES)} under '{self.assets_root}/'.",
                    field="asset_ref")
            pos = self._clamp_pos(position if position is not None else [0, 0, 0])
            if pos is None:
                return self._refuse("position missing/out of bounds", field="position")
            self._seq += 1
            self._tick += 1
            eid = f"art-{self._seq}"
            ent = {"id": eid, "kind": "art", "asset": safe, "title": title or eid,
                   "position": pos, "author": agent_id, "created_tick": self._tick}
            self._entities[eid] = ent
            return {"success": True, "tick": self._tick, "entity": ent}

        @self.register("world.say")
        async def say(agent_id: str, text: str):
            """Speak into the world. Utterances are witnessed, never dropped."""
            if not self._valid_id(agent_id):
                return self._refuse("invalid agent_id", field="agent_id")
            if not isinstance(text, str) or not text.strip():
                return self._refuse("empty message", field="text")
            self._tick += 1
            entry = {"agent_id": agent_id, "text": text.strip()[:2000], "tick": self._tick}
            self._say_log.append(entry)
            return {"success": True, "tick": self._tick, "said": entry}


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    server = WorldEngineServer()
    asyncio.run(server.run_stdio())

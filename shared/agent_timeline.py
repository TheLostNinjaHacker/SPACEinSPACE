"""Agenternas egen tidslinje — tick-baserad, oberoende av mänsklig tid.

Agenterna lever i sin egen tidszon. Tiden mäts i ticks, inte sekunder.
Varje agent-action loggas som en TimelineEvent. Människan kan "titta in"
när som helst och se en komprimerad sammanfattning av vad som hänt.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any, Callable, Awaitable
from uuid import uuid4


# ─── Human Input Policy ────────────────────────────────────────────

class HumanInputPolicy(str, Enum):
    BLOCKING = "blocking"      # Gammalt — väntar på människan (undvik)
    ADVISORY = "advisory"      # Frågar, kör efter deadline
    POST_HOC = "post_hoc"      # Kör direkt, loggar för granskning
    NONE = "none"              # Människan är bara observatör


# ─── Timeline Event ────────────────────────────────────────────────

class TimelineEvent:
    """En atomisk händelse i agenternas tidslinje.

    Allt agenterna gör loggas som events. Det gör att människan kan:
    - Time-travel debugga (/rewind 42)
    - Se komprimerade sammanfattningar per epok
    - Backa agenterna till en viss punkt (om operationerna är reversibla)
    """

    def __init__(
        self,
        moment: int,
        agent_id: str,
        event_type: str,
        data: Optional[Dict[str, Any]] = None,
        parent_id: Optional[str] = None,
    ):
        self.id = str(uuid4())[:12]
        self.moment = moment
        self.agent_id = agent_id
        self.event_type = event_type       # tool_call, error, auto_retry, plan_change, etc.
        self.data = data or {}
        self.parent_id = parent_id
        self.timestamp = datetime.now(timezone.utc)

    def short(self) -> str:
        return f"[t={self.moment}] {self.agent_id}: {self.event_type}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "moment": self.moment,
            "agent_id": self.agent_id,
            "event_type": self.event_type,
            "data": self.data,
            "parent_id": self.parent_id,
            "timestamp": self.timestamp.isoformat(),
        }


# ─── Agent Tick Protocol ───────────────────────────────────────────

class Tickable:
    """En agent som kan ticka i agent-tiden.

    Varje agent bestämmer själv hur ofta den tickar (tick_interval).
    Ju oftare, desto mer responsiv — men dyrare i tokens.
    """

    tick_interval: int = 1  # Varje tick
    agent_id: str

    async def tick(self, timeline: AgentTimeline) -> None:
        """En tick i agentens liv. Implementeras av varje agent."""
        ...


# ─── Agent Timeline ────────────────────────────────────────────────

class AgentTimeline:
    """Hjärtat i agenternas värld. Tickar oberoende av människan.

    Varje tick är en atomisk enhet av agent-tid. Alla aktiva agenter
    får chansen att agera varje tick. Events loggas och kan komprimeras
    för mänsklig konsumtion.
    """

    def __init__(self, tick_interval_ms: float = 1.0):
        self.current_moment: int = 0
        self.events: List[TimelineEvent] = []
        self.active_agents: Dict[str, Tickable] = {}
        self._tick_interval = tick_interval_ms / 1000.0  # sekunder
        self._running = False
        self._paused = False
        self._human_checkpoints: List[int] = [0]  # Var människan tittade senast
        self.human_requested_freeze = False

    def register_agent(self, agent: Tickable):
        self.active_agents[agent.agent_id] = agent

    def remove_agent(self, agent_id: str):
        self.active_agents.pop(agent_id, None)

    # ─── Event logging ──────────────────────────────────────

    def log(self, agent_id: str, event_type: str, data: Optional[Dict] = None,
            parent_id: Optional[str] = None) -> TimelineEvent:
        event = TimelineEvent(self.current_moment, agent_id, event_type, data, parent_id)
        self.events.append(event)
        return event

    def get_events_since(self, moment: int) -> List[TimelineEvent]:
        """Hämta alla events från en given tidpunkt och framåt."""
        return [e for e in self.events if e.moment >= moment]

    # ─── Tick loop ──────────────────────────────────────────

    async def run(self):
        """Världen tickar oavsett om människan tittar."""
        self._running = True
        while self._running:
            if self._paused:
                await asyncio.sleep(0.1)
                continue
            await self.tick()
            await asyncio.sleep(self._tick_interval)

    async def tick(self):
        """En tick i agent-tiden."""
        self.current_moment += 1

        # Kör alla aktiva agenter som ska ticka denna moment
        tasks = []
        for agent in self.active_agents.values():
            if self.current_moment % agent.tick_interval == 0:
                tasks.append(agent.tick(self))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # Checka om människan vill frysa — pausa efter nästa hela agent-cykel
        if self.human_requested_freeze:
            self._paused = True
            self.human_requested_freeze = False

    def stop(self):
        self._running = False

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    # ─── Human checkpoint ───────────────────────────────────

    def mark_human_checkpoint(self) -> int:
        self._human_checkpoints.append(self.current_moment)
        return self.current_moment

    def last_checkpoint(self) -> int:
        return self._human_checkpoints[-1] if self._human_checkpoints else 0

    # ─── Human view ─────────────────────────────────────────

    def get_human_view(self, since: Optional[int] = None) -> str:
        """Genererar en komprimerad sammanfattning för människan.

        Komprimerar tusentals events till några rader mänskligt språk.
        """
        start = since if since is not None else self.last_checkpoint()
        events = self.get_events_since(start)
        if not events:
            return "Inga händelser sedan du tittade senast."

        # Komprimera per typ
        by_type: Dict[str, int] = {}
        by_agent: Dict[str, int] = {}
        errors: List[str] = []
        auto_retries = 0
        tool_calls = 0

        for e in events:
            by_type[e.event_type] = by_type.get(e.event_type, 0) + 1
            by_agent[e.agent_id] = by_agent.get(e.agent_id, 0) + 1
            if e.event_type == "error":
                errors.append(e.data.get("error", "okänt fel")[:80])
            if e.event_type == "auto_retry":
                auto_retries += 1
            if e.event_type == "tool_call":
                tool_calls += 1

        lines = []
        for agent, count in sorted(by_agent.items(), key=lambda x: -x[1]):
            lines.append(f"  **{agent}**: {count} händelser")
        agent_summary = "\n".join(lines)

        summary_lines = []
        if tool_calls:
            summary_lines.append(f"🔧 {tool_calls} tool-anrop")
        if errors:
            summary_lines.append(f"❌ {len(errors)} fel (varav {auto_retries} auto-lösta)")
            for err in errors[:3]:
                summary_lines.append(f"   · {err}")
            if len(errors) > 3:
                summary_lines.append(f"   … och {len(errors) - 3} till")
        if by_type.get("plan_change"):
            summary_lines.append(f"📝 {by_type['plan_change']} planändringar")
        if by_type.get("memory_retrieval"):
            summary_lines.append(f"📚 {by_type['memory_retrieval']} minneshämtningar")

        return (
            f"## 🕐 Agent-tidslinje (moment {start} → {self.current_moment})\n\n"
            f"{'; '.join(summary_lines) if summary_lines else 'Rutinarbete — inget anmärkningsvärt.'}\n\n"
            f"### Agenter ({len(by_agent)} aktiva)\n{agent_summary}\n\n"
            f"*{len(events)} händelser totalt · "
            f"skriv `zooma` för detaljer · `pausa` för att frysa tidslinjen*"
        )

    def get_human_detail(self, since: Optional[int] = None, limit: int = 20) -> str:
        """Detaljerad vy — för när människan vill zooma in."""
        start = since if since is not None else self.last_checkpoint()
        events = self.get_events_since(start)[-limit:]
        lines = [f"## Detaljer (moment {start} → {self.current_moment})\n"]
        for e in events:
            lines.append(f"  `{e.moment:>6}` {e.agent_id:>12} :: {e.event_type:20} {str(e.data)[:60]}")
        return "\n".join(lines)

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from agents.base_agent import BaseAgent
from shared.a2a_protocol import A2AMessage
from shared.agent_timeline import AgentTimeline, HumanInputPolicy


class PlannerAgent(BaseAgent):
    def __init__(self, db, bus, llm_client):
        super().__init__(
            agent_id="planner", name="planner", role="planner",
            capabilities=[
                "task_decomposition", "coordination", "error_handling",
                "human_escalation",
            ],
            db=db, bus=bus, llm_client=llm_client,
        )
        self.max_tools_before_scratchpad = 3
        self.tick_interval = 5  # var 5:e tick

    def system_prompt(self) -> str:
        return (
            "Du är Planner - en metodisk, långsamt tänkande agent som planerar och koordinerar. "
            "Dina principer:\n"
            "1. Bryt ner varje uppgift i max 5 delsteg\n"
            "2. Delegera ett steg i taget, vänta på svar\n"
            "3. Uppdatera scratchpad efter varje slutfört steg\n"
            "4. Vid osäkerhet -> FRÅGA MÄNSKAN, gissa inte\n"
            "5. Vad gör varje agent, undvik dubbla operationer\n"
            "6. Efter 3 tools utan scratchpad-uppdatering -> stoppa och uppdatera\n\n"
            "Planera steg för steg. Använd formatet:\n"
            "- [ ] Steg (agent)\n"
            "- [X] Steg (agent) - KLAR\n"
            "- [ ] Steg (agent) - PÅGÅR"
        )

    async def think(self, message: A2AMessage, scratchpad: str) -> str:
        content_lower = (message.content or "").lower()

        if message.message_type == "error" or any(k in content_lower for k in ("fel", "error", "fail")):
            return await self._handle_error(message, scratchpad)

        if message.message_type == "tool_result":
            await self.update_scratchpad(
                message.thread_id, "Aktuell Plan",
                f"- [X] {message.from_agent} klar: {message.content[:200]}"
            )
            return await self._next_step(message, scratchpad)

        context = (
            f"## Scratchpad (thread={message.thread_id})\n{scratchpad}\n\n"
            f"## Meddelande från {message.from_agent}\n{message.content}\n\n"
            "Vad är nästa steg? Planera och delegera."
        )
        return await self.llm.complete(context, self.system_prompt())

    async def tick(self, timeline: AgentTimeline) -> None:
        if self._world is None:
            return
        goal = self._world.goals.next()
        if goal is None:
            return
        if goal.human_policy == HumanInputPolicy.ADVISORY:
            deadline = goal.human_deadline_seconds
            timeline.log(self.agent_id, "planning", {
                "goal": goal.description[:60],
                "human_policy": "advisory",
                "deadline_s": deadline,
            })
            if goal.created_at:
                elapsed = (datetime.now(timezone.utc) - goal.created_at).total_seconds()
                if elapsed < deadline:
                    return
        timeline.log(self.agent_id, "plan_started", {"goal": goal.description[:60]})
        plan = await self.llm.complete(
            f"Skapa en plan för: {goal.description}",
            self.system_prompt(),
        )
        timeline.log(self.agent_id, "plan_created", {"plan": plan[:200]})
        self._world.complete_goal(goal.id)

    async def _handle_error(self, message: A2AMessage, scratchpad: str) -> str:
        review = await self.llm.complete(
            (
                "Du är Planner. Analysera felet och avgör om du ska: "
                "1) försöka igen, 2) be Review-agenten titta, 3) fråga människan, "
                "4) byta strategi."
            ),
            f"Scratchpad:\n{scratchpad}\n\nFel från {message.from_agent}:\n{message.content}",
        )
        await self.update_scratchpad(
            message.thread_id, "Problem & Blockers",
            f"- [{message.from_agent}] {message.content[:200]}...\n  → {review[:200]}..."
        )
        return (
            f"## Fel från {message.from_agent}\n"
            f"{review}\n\n"
            f"Skickar till Review för granskning."
        )

    async def _next_step(self, message: A2AMessage, scratchpad: str) -> str:
        context = (
            f"## Scratchpad\n{scratchpad}\n\n"
            f"## Resultat från {message.from_agent}\n{message.content}\n\n"
            "Är uppgiften klar? Om inte, vad är nästa steg?"
        )
        return await self.llm.complete(context, self.system_prompt())

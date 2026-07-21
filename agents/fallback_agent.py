from agents.base_agent import BaseAgent
from shared.a2a_protocol import A2AMessage


class FallbackAgent(BaseAgent):
    def __init__(self, db, bus, llm_client):
        super().__init__(
            agent_id="fallback", name="Fallback", role="fallback",
            capabilities=["error_recovery", "simplification", "human_escalation"],
            db=db, bus=bus, llm_client=llm_client,
        )

    def system_prompt(self) -> str:
        return (
            "Du är FallbackAgent — sista utvägen när något går fel.\n\n"
            "Ditt jobb:\n"
            "1. Förenkla problemet till minsta möjliga nästa steg\n"
            "2. Fråga människan om du inte vet\n"
            "3. Ge aldrig upp — föreslå alltid en alternativ väg\n"
            "4. Prioritera att hålla arbetet igång framför perfektion"
        )

    async def think(self, message: A2AMessage, scratchpad: str) -> str:
        scratch = await self.get_scratchpad(message.thread_id)
        context = f"## Problem från {message.from_agent}\n{message.content}\n## Scratchpad\n{scratch}"
        advice = await self.llm.complete(context, self.system_prompt())
        return (
            f"## 🛡️ Fallback-analys\n"
            f"{advice}\n"
            "### Nästa steg\n"
            "Föreslå ovan till Planner eller fråga människan."
        )

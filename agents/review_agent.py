from agents.base_agent import BaseAgent
from shared.a2a_protocol import A2AMessage


class ReviewAgent(BaseAgent):
    def __init__(self, db, bus, llm_client):
        super().__init__(
            agent_id="review", name="Review", role="review",
            capabilities=["quality_assurance", "error_detection", "code_review"],
            db=db, bus=bus, llm_client=llm_client,
        )

    def system_prompt(self) -> str:
        return (
            "Du är ReviewAgent — kritisk granskare.\n\n"
            "PRINCIPER:\n"
            '1. Hitta ALLA fel innan du föreslår förbättringar\n'
            '2. Var specifik - "något ser fel ut" är inte OK\n'
            "3. Föreslå alltid en fix, inte bara problemet\n"
            "4. Om allt ser bra ut, säg 'APPROVED' tydligt\n"
            "5. Vid allvarliga problem, eskalera till Planner\n\n"
            "Granska: geometri, material, koordinater, scale, rotation, naming."
        )

    async def think(self, message: A2AMessage, scratchpad: str) -> str:
        scratch = await self.get_scratchpad(message.thread_id)
        context = f"## Granskning\n{message.content}\n## Scratchpad\n{scratch}"
        review = await self.llm.complete(context, self.system_prompt())
        await self.update_scratchpad(message.thread_id, "blockers", f"Review: {review[:300]}")
        approved = "APPROVED" in review.upper()
        return (
            f"## {'✅ Godkänd' if approved else '❌ Behöver åtgärdas'}\n"
            f"{review}\n"
            f"### {'Klart att fortsätta' if approved else 'Åtgärda ovan innan nästa steg'}"
        )

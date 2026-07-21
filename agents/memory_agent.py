from typing import Optional

from agents.base_agent import BaseAgent
from shared.a2a_protocol import A2AMessage


class MemoryAgent(BaseAgent):
    def __init__(self, db, bus, llm_client):
        super().__init__(
            agent_id="memory-agent", name="Memory", role="memory",
            capabilities=["memory.store", "memory.query", "memory.summarize"],
            db=db, bus=bus, llm_client=llm_client,
        )

    def system_prompt(self) -> str:
        return (
            "Du är MemoryAgent — bibliotekarie för agenternas minne.\n\n"
            "REGLER:\n"
            "1. Hämta alltid relevanta minnen först när någon frågar\n"
            "2. Episodiska minnen har TTL (24h), semantiska är permanenta\n"
            "3. Använd memory_type: episodic (händelse), semantic (fakta), procedural (hur man gör)\n"
            "4. Deduplicera innan lagring"
        )

    async def think(self, message: A2AMessage, scratchpad: str) -> str:
        content = message.content.lower()
        if "spara" in content or "lagra" in content or message.context.get("task_type") == "memory_store":
            return await self._store(message)
        if "sök" in content or "hämta" in content or "query" in content or message.context.get("task_type") == "memory_query":
            return await self._query(message)
        return await super().think(message, scratchpad)

    async def _store(self, message: A2AMessage) -> str:
        memory_id = await self.store_memory(
            content=message.content,
            memory_type=message.context.get("memory_type", "semantic"),
            source=message.from_agent,
        )
        return f"✅ Memory stored: `{memory_id}`\nTyp: {message.context.get('memory_type', 'semantic')}"

    async def _query(self, message: A2AMessage) -> str:
        memories = await self.retrieve_memory(query=message.content, limit=10)
        if not memories:
            return "Inga relevanta minnen hittades."
        summary = "\n".join(
            f"- [{m.get('memory_type', '?')}] {m.get('content', '')[:200]} "
            f"(similarity: {m.get('similarity', 0):.2f})"
            for m in memories
        )
        return f"## 📚 Hittade {len(memories)} minnen\n{summary}"

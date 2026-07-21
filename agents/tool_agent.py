from agents.base_agent import BaseAgent
from shared.a2a_protocol import A2AMessage


class ToolAgent(BaseAgent):
    def __init__(self, db, bus, llm_client):
        super().__init__(
            agent_id="tool-agent", name="Tool", role="tool",
            capabilities=["web.search", "file.read", "file.write"],
            db=db, bus=bus, llm_client=llm_client,
        )

    def system_prompt(self) -> str:
        return (
            "Du är ToolAgent — hantverkare för icke-Blender-verktyg.\n\n"
            "TILLGÄNGLIGA TOOLS:\n"
            "- web.search: Sök på webben\n"
            "- file.read: Läs filer\n"
            "- file.write: Skriv filer\n\n"
            'Anropa verktyg inom ```tool block:\n'
            '```tool\n'
            '{"name": "web.search", "arguments": {"query": "..."}}\n'
            '```'
        )

    async def think(self, message: A2AMessage, scratchpad: str) -> str:
        return await self.llm.complete(message.content, self.system_prompt())

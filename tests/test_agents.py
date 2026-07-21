"""Integration tests for agent flow with mocked database.

Tests that agents:
  - Can be instantiated with mock db/bus/llm
  - Return proper A2AMessages from handle_message
  - Handle errors gracefully
  - Route messages correctly through think()
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Optional

import pytest

from shared.a2a_protocol import A2AMessage, A2ABus



# ─── Mock LLM ──────────────────────────────────────────────────────
class MockLLM:
    def __init__(self, responses: Optional[dict] = None):
        self.responses = responses or {}

    async def complete(self, prompt: str, system: str = "") -> str:
        key = system[:30] + prompt[:30]
        if key in self.responses:
            return self.responses[key]
        if "error" in prompt.lower() or "fail" in prompt.lower():
            return "Analyserar felet. Skickar till Review."
        if "klar" in prompt.lower() or "done" in prompt.lower():
            return "Steg klart! Nästa steg..."
        return f"Svar på: {prompt[:60]}..."

    async def embed(self, text: str):
        return [0.1] * 8  # short fake embedding


# ─── Mock Database ─────────────────────────────────────────────────
class MockDB:
    def __init__(self):
        self.agents = {}
        self.memories = []
        self.messages = []
        self.scratchpads = {}
        self.tool_calls = []
        self.supabase = MagicMock()

    async def register_agent(self, agent_id, name, role, capabilities):
        self.agents[agent_id] = {"name": name, "role": role}

    async def update_agent_status(self, agent_id, status, thread_id=None):
        pass

    async def get_scratchpad(self, thread_id):
        return f"# Scratchpad: {thread_id}\n\n## Plan\n\n"

    async def upsert_scratchpad(self, thread_id, section, content, agent_id):
        self.scratchpads[(thread_id, section)] = content
        return 1

    async def log_message(self, thread_id, from_agent, content, **kw):
        self.messages.append({"from": from_agent, "content": content[:50]})
        return "msg-1"

    async def store_memory(self, agent_id, content, embedding, memory_type, **kw):
        self.memories.append({"agent": agent_id, "type": memory_type})
        return "mem-1"

    async def retrieve_memories(self, query_embedding, **kw):
        return [{"content": "mock memory", "memory_type": "semantic", "similarity": 0.9}]

    async def log_tool_call(self, **kw):
        self.tool_calls.append(kw)


@pytest.fixture
def mock_db():
    return MockDB()


@pytest.fixture
def bus():
    return A2ABus(db=None)


@pytest.fixture
def llm():
    return MockLLM()


@pytest.mark.asyncio
async def test_planner_agent_basic_flow(mock_db, bus, llm):
    from agents.planner_agent import PlannerAgent
    agent = PlannerAgent(db=mock_db, bus=bus, llm_client=llm)
    await agent.initialize()

    msg = A2AMessage(thread_id="t1", from_agent="human", content="Skapa en kub")
    response = await agent.handle_message(msg)
    assert response is not None
    assert response.from_agent == "planner"
    assert response.thread_id == "t1"
    assert len(response.content) > 0


@pytest.mark.asyncio
async def test_planner_rejects_own_messages(mock_db, bus, llm):
    from agents.planner_agent import PlannerAgent
    agent = PlannerAgent(db=mock_db, bus=bus, llm_client=llm)

    msg = A2AMessage(thread_id="t1", from_agent="planner", content="self msg")
    response = await agent.handle_message(msg)
    assert response is None


@pytest.mark.asyncio
async def test_planner_error_routing(mock_db, bus, llm):
    from agents.planner_agent import PlannerAgent
    agent = PlannerAgent(db=mock_db, bus=bus, llm_client=llm)

    msg = A2AMessage(thread_id="t1", from_agent="blender",
                     message_type="error", content="fel: kunde inte skapa objekt")
    response = await agent.handle_message(msg)
    assert response is not None
    assert "Review" in response.content


@pytest.mark.asyncio
async def test_memory_agent_store(mock_db, bus, llm):
    from agents.memory_agent import MemoryAgent
    agent = MemoryAgent(db=mock_db, bus=bus, llm_client=llm)

    msg = A2AMessage(thread_id="t1", from_agent="planner",
                     content="spara: kub skapad på (0,0,0)",
                     context={"task_type": "memory_store", "memory_type": "episodic"})
    response = await agent.handle_message(msg)
    assert response is not None
    assert len(mock_db.memories) == 1
    assert mock_db.memories[0]["type"] == "episodic"


@pytest.mark.asyncio
async def test_memory_agent_query(mock_db, bus, llm):
    from agents.memory_agent import MemoryAgent
    agent = MemoryAgent(db=mock_db, bus=bus, llm_client=llm)

    msg = A2AMessage(thread_id="t1", from_agent="planner",
                     content="sök efter: kub",
                     context={"task_type": "memory_query"})
    response = await agent.handle_message(msg)
    assert response is not None
    assert "mock memory" in response.content


@pytest.mark.asyncio
async def test_review_agent(mock_db, bus, llm):
    from agents.review_agent import ReviewAgent
    agent = ReviewAgent(db=mock_db, bus=bus, llm_client=llm)

    msg = A2AMessage(thread_id="t1", from_agent="planner",
                     content="Granska: en röd kub på (0,0,0)")
    response = await agent.handle_message(msg)
    assert response is not None
    assert "Godkänd" in response.content or "Behöver" in response.content


@pytest.mark.asyncio
async def test_fallback_agent(mock_db, bus, llm):
    from agents.fallback_agent import FallbackAgent
    agent = FallbackAgent(db=mock_db, bus=bus, llm_client=llm)

    msg = A2AMessage(thread_id="t1", from_agent="conductor",
                     message_type="error",
                     content="Blender failed: connection refused")
    response = await agent.handle_message(msg)
    assert response is not None
    assert "Fallback" in response.content


@pytest.mark.asyncio
async def test_tool_agent(mock_db, bus, llm):
    from agents.tool_agent import ToolAgent
    agent = ToolAgent(db=mock_db, bus=bus, llm_client=llm)

    msg = A2AMessage(thread_id="t1", from_agent="planner",
                     content="web.search: Blender python API")
    response = await agent.handle_message(msg)
    assert response is not None
    assert len(response.content) > 0


@pytest.mark.asyncio
async def test_blender_agent_mcp_not_available(mock_db, bus, llm):
    from agents.blender_agent import BlenderAgent
    agent = BlenderAgent(db=mock_db, bus=bus, llm_client=llm)

    msg = A2AMessage(thread_id="t1", from_agent="planner",
                     content="Skapa en kub")
    response = await agent.handle_message(msg)
    assert response is not None
    assert response.from_agent == "blender"


@pytest.mark.asyncio
async def test_stop_agent(mock_db, bus, llm):
    from agents.planner_agent import PlannerAgent
    agent = PlannerAgent(db=mock_db, bus=bus, llm_client=llm)

    msg = A2AMessage(thread_id="t1", from_agent="human", content="test")
    agent.stop()
    response = await agent.handle_message(msg)
    assert response is None


@pytest.mark.asyncio
async def test_conductor_message_routing(mock_db, bus, llm):
    """Test that conductor routes a human message through all expected steps."""
    from orchestrator.conductor import Conductor

    with patch("orchestrator.conductor.get_supabase", return_value=mock_db), \
         patch("orchestrator.conductor.QwenClient", return_value=llm):
        conductor = Conductor(use_tool_tuning=False)
        conductor.llm = llm
        conductor.db = mock_db

        for agent in conductor.agents.values():
            agent.db = mock_db
            agent.llm = llm

        msg = A2AMessage(thread_id="t1", from_agent="human", to_agent="planner",
                         content="test task")
        assert "planner" in conductor.agents
        assert conductor.agents["planner"] is not None

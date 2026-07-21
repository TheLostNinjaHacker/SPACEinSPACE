"""Conductor — orchestrates the agent world.

The conductor no longer runs a message queue. Instead it:
  1. Creates an AgentWorld with timeline, goals, blender state, memory
  2. Registers agents as Tickable participants in the timeline
  3. Lets the world tick — agents act on their own schedule
  4. Human input becomes a Goal in the world, not a blocking gate

The world ticks regardless of human attention.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Dict, Optional

from dotenv import load_dotenv

from shared.supabase_client import get_supabase, AgentDatabase
from shared.llm import QwenClient
from shared.world_state import AgentWorld, Goal
from shared.agent_timeline import AgentTimeline, HumanInputPolicy
from shared.a2a_protocol import A2ABus, A2AMessage
from shared.tool_executor import ToolExecutor
from shared.telemetry import telemetry

from agents.base_agent import BaseAgent
from agents.planner_agent import PlannerAgent
from agents.blender_agent import BlenderAgent
from agents.memory_agent import MemoryAgent
from agents.tool_agent import ToolAgent
from agents.review_agent import ReviewAgent
from agents.fallback_agent import FallbackAgent


class Conductor:
    def __init__(self, tick_interval_ms: float = 10.0, use_tool_tuning: bool = True) -> None:
        load_dotenv(override=False)

        self.logger = logging.getLogger("conductor")
        self.db: AgentDatabase = get_supabase()
        self.llm = QwenClient()
        self.bus = A2ABus(db=self.db)

        # ─── The Agent World ────────────────────────────────
        self.world = AgentWorld(tick_interval_ms=tick_interval_ms)

        # ─── Tool executor ────────────────────────────────
        self.tool_executor = ToolExecutor(db=self.db)
        try:
            from mcp_servers.blender_mcp_server import BlenderMCPServer
            bm = BlenderMCPServer()
            self.tool_executor.register_blender(bm)
        except Exception:
            self.logger.info("Blender MCP not loaded — blender.* tools unavailable")

        # ─── Tool Tuning ──────────────────────────────────
        self.tool_tuning = None
        if use_tool_tuning:
            try:
                from tools.stats import ToolTuning
                self.tool_tuning = ToolTuning(self.db)
            except Exception:
                self.logger.debug("ToolTuning not available")

        # ─── Agents ────────────────────────────────────────
        self.agents: Dict[str, BaseAgent] = {}
        self._setup_agents()

        self._stop = asyncio.Event()

    def _setup_agents(self) -> None:
        agent_classes = {
            "planner": PlannerAgent,
            "blender": BlenderAgent,
            "memory": MemoryAgent,
            "tool": ToolAgent,
            "review": ReviewAgent,
            "fallback": FallbackAgent,
        }
        for name, cls in agent_classes.items():
            instance = cls(db=self.db, bus=self.bus, llm_client=self.llm)
            instance.connect_world(self.world)
            self.world.timeline.register_agent(instance)
            self.agents[name] = instance

    async def register_all(self) -> None:
        for agent in self.agents.values():
            try:
                await agent.initialize()
            except Exception as e:
                self.logger.debug(f"register_agent({agent.name}) failed: {e}")

    # ─── Human interaction ────────────────────────────────

    def add_goal(self, description: str, priority: int = 3,
                 human_policy: HumanInputPolicy = HumanInputPolicy.ADVISORY) -> Goal:
        goal = self.world.add_goal(description, goal_type="human_request",
                                    priority=priority, human_policy=human_policy)
        self.world.timeline.log("human", "goal_added", {
            "goal_id": goal.id, "description": description[:80],
        })
        return goal

    def human_view(self) -> str:
        return self.world.human_view()

    def human_detail(self, limit: int = 20) -> str:
        return self.world.human_detail(limit=limit)

    def pause(self):
        self.world.pause()

    def resume(self):
        self.world.resume()

    # ─── Lifecycle ─────────────────────────────────────────

    async def run(self) -> None:
        await self.register_all()
        self.logger.info("Agent world spinning up, agents: %s",
                         list(self.agents.keys()))

        if self.tool_tuning:
            try:
                await asyncio.wait_for(self.tool_tuning.sync_from_db(), timeout=5)
            except Exception:
                self.logger.debug("ToolTuning sync_from_db failed")

        self.world.timeline.log("world", "world_started", {
            "agents": list(self.agents.keys()),
        })

        await self.world.run()

    def stop(self) -> None:
        self.world.stop()
        self._stop.set()

    def get_thread_log(self, thread_id: str):
        return []

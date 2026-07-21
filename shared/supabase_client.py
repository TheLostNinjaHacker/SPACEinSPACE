"""Async database wrapper around the sync Supabase client.

Why this exists:
  supabase-py's ``create_client`` returns a SYNC ``Client``. Calling
  ``await client.table(...).execute()`` would crash with
  ``TypeError: object SyncQueryRequestBuilder can't be used in 'await' expression``.

This module wraps every blocking ``.execute()`` in ``asyncio.to_thread`` so
agent code can ``await db.store_memory(...)`` without blocking the event loop.
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import uuid4

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


# Default scratchpad template (used when no scratchpad exists yet)
SCRATCHPAD_TEMPLATE = """# Scratchpad: {thread_id}

## Aktuell Plan
1. [ ] Steg 1

## Blender State
- Aktiv objekt: None
- Mode: OBJECT
- Senaste operation: None

## Minnesreferenser


## Problem & Blockers


## Mänsklig input needed

"""


class AgentDatabase:
    """Async wrapper around the sync Supabase ``Client``.

    Every read or write methods offloads the blocking HTTP call to a worker
    thread via ``asyncio.to_thread`` so the asyncio loop stays responsive.
    """

    def __init__(self) -> None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_KEY must be set in .env "
                "(see .env.example)"
            )
        self._client: Client = create_client(url, key)
        self.supabase = self._client  # alias for backward compat

    # ─── Thread-safety helper ───────────────────────────────
    async def _run_sync(self, fn, *args, **kwargs):
        """Run a sync callable in a worker thread (does not block the loop)."""
        return await asyncio.to_thread(fn, *args, **kwargs)

    # ─── Memory ─────────────────────────────────────────────
    async def store_memory(
        self,
        agent_id: str,
        content: str,
        embedding: List[float],
        memory_type: str = "episodic",
        metadata: Optional[Dict[str, Any]] = None,
        parent_id: Optional[str] = None,
        confidence: float = 1.0,
        source: Optional[str] = None,
        ttl_hours: Optional[int] = None,
    ) -> str:
        data: Dict[str, Any] = {
            "agent_id": agent_id,
            "memory_type": memory_type,
            "content": content,
            "embedding": embedding,
            "metadata": metadata or {},
            "parent_id": parent_id,
            "confidence": confidence,
            "source": source,
        }
        if ttl_hours:
            data["expires_at"] = (
                datetime.now() + timedelta(hours=ttl_hours)
            ).isoformat()
        result = await self._run_sync(
            self._client.table("agent_memories").insert(data).execute
        )
        return result.data[0]["id"]

    async def retrieve_memories(
        self,
        query_embedding: List[float],
        agent_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        thread_id: Optional[str] = None,
        threshold: float = 0.7,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {
            "query_embedding": query_embedding,
            "match_threshold": threshold,
            "match_count": limit,
            "agent_filter": agent_id,
            "type_filter": memory_type,
            "thread_filter": thread_id,
        }
        result = await self._run_sync(
            self._client.rpc("match_memories", params).execute
        )
        return result.data or []

    # ─── Scratchpad ─────────────────────────────────────────
    async def get_scratchpad(self, thread_id: str) -> str:
        """Return the latest scratchpad content as a single markdown string."""
        def _q():
            return (
                self._client.table("scratchpad")
                .select("content, version, section, updated_at")
                .eq("thread_id", thread_id)
                .order("version", desc=True)
                .limit(1)
                .execute()
            )
        result = await self._run_sync(_q)
        if result.data:
            return result.data[0]["content"]
        return SCRATCHPAD_TEMPLATE.format(thread_id=thread_id)

    async def upsert_scratchpad(
        self,
        thread_id: str,
        section: str,
        content: str,
        agent_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        def _q():
            existing = (
                self._client.table("scratchpad")
                .select("version")
                .eq("thread_id", thread_id)
                .eq("section", section)
                .order("version", desc=True)
                .limit(1)
                .execute()
            )
            version = (
                existing.data[0]["version"] + 1 if existing.data else 1
            )
            data = {
                "thread_id": thread_id,
                "section": section,
                "content": content,
                "agent_id": agent_id,
                "version": version,
                "metadata": metadata or {},
            }
            self._client.table("scratchpad").upsert(data).execute()
            return version
        return await self._run_sync(_q)

    async def get_thread_sections(
        self, thread_id: str
    ) -> Dict[str, str]:
        """Return latest content per section as a dict."""
        def _q():
            return (
                self._client.table("scratchpad")
                .select("section, content, version")
                .eq("thread_id", thread_id)
                .order("version", desc=True)
                .execute()
            )
        result = await self._run_sync(_q)
        out: Dict[str, str] = {}
        seen: set = set()
        for row in result.data or []:
            s = row.get("section", "general")
            if s in seen:
                continue
            seen.add(s)
            out[s] = row.get("content", "")
        return out

    # ─── A2A Messages ───────────────────────────────────────
    async def log_message(
        self,
        thread_id: str,
        from_agent: str,
        content: str,
        message_type: str = "observation",
        to_agent: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        latency_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        parent_id: Optional[str] = None,
    ) -> str:
        message_id = str(uuid4())
        data = {
            "thread_id": thread_id,
            "message_id": message_id,
            "from_agent": from_agent,
            "to_agent": to_agent,
            "message_type": message_type,
            "content": content,
            "embedding": embedding,
            "tool_calls": tool_calls or [],
            "latency_ms": latency_ms,
            "metadata": metadata or {},
            "parent_id": parent_id,
        }
        await self._run_sync(
            self._client.table("agent_conversations").insert(data).execute
        )
        return message_id

    async def get_thread_messages(
        self, thread_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        def _q():
            return (
                self._client.table("agent_conversations")
                .select("*")
                .eq("thread_id", thread_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
        result = await self._run_sync(_q)
        return list(reversed(result.data or []))

    # ─── Agent Registry ─────────────────────────────────────
    async def register_agent(
        self,
        agent_id: str,
        name: str,
        role: str,
        capabilities: List[str],
    ) -> None:
        data = {
            "id": agent_id,
            "name": name,
            "role": role,
            "capabilities": capabilities,
            "status": "idle",
            "last_heartbeat": datetime.now().isoformat(),
        }
        await self._run_sync(self._client.table("agents").upsert(data).execute)

    async def update_agent_status(
        self,
        agent_id: str,
        status: str,
        thread_id: Optional[str] = None,
    ) -> None:
        data: Dict[str, Any] = {
            "status": status,
            "last_heartbeat": datetime.now().isoformat(),
        }
        if thread_id:
            data["current_thread_id"] = thread_id

        def _q():
            return (
                self._client.table("agents")
                .update(data)
                .eq("id", agent_id)
                .execute()
            )
        await self._run_sync(_q)

    async def list_agents(self) -> List[Dict[str, Any]]:
        def _q():
            return (
                self._client.table("agents")
                .select("*")
                .order("last_heartbeat", desc=True)
                .execute()
            )
        result = await self._run_sync(_q)
        return result.data or []

    # ─── Tool Calls ─────────────────────────────────────────
    async def log_tool_call(
        self,
        thread_id: str,
        agent_id: str,
        tool_name: str,
        input_params: Dict[str, Any],
        output_result: Optional[Dict[str, Any]] = None,
        success: Optional[bool] = None,
        error_message: Optional[str] = None,
        latency_ms: Optional[int] = None,
        scratchpad_version: Optional[int] = None,
    ) -> None:
        data = {
            "thread_id": thread_id,
            "agent_id": agent_id,
            "tool_name": tool_name,
            "input_params": input_params,
            "output_result": output_result,
            "success": success,
            "error_message": error_message,
            "latency_ms": latency_ms,
            "scratchpad_version": scratchpad_version,
        }
        await self._run_sync(self._client.table("tool_calls").insert(data).execute)


# Backwards-compatible accessor — call sites keep ``from shared.supabase_client
# import get_supabase`` and now get an async ``AgentDatabase`` instance.
_db_instance: Optional[AgentDatabase] = None


def get_supabase() -> AgentDatabase:
    global _db_instance
    if _db_instance is None:
        _db_instance = AgentDatabase()
    return _db_instance

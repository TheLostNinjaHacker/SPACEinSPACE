"""Memory operations — embed, retrieve, store.

Uses ``AgentDatabase`` (async wrapper) so the event loop is never blocked.
Embeddings come from Ollama ``qwen3-embedding:8b`` (4096-dim).
"""
from __future__ import annotations

import os
from typing import Optional, List, Dict, Any

import httpx

from shared.supabase_client import get_supabase

OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "qwen3-embedding:8b")


async def embed(text: str) -> list[float]:
    """Embed text via local Ollama embed endpoint. Returns 4096-dim vector."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{OLLAMA_BASE}/api/embed",
            json={"model": EMBED_MODEL, "input": text},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["embeddings"][0]


async def retrieve_memory(
    query: str,
    agent_id: str,
    thread_id: str,
    memory_type: Optional[str] = None,
    threshold: float = 0.7,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Search vector memory AND attach recent scratchpad for the thread.

    ``agent_id`` may be ``"*"`` to match all agents.
    """
    db = get_supabase()
    embedding = await embed(query)

    # Use routine as-is
    memories = await db.retrieve_memories(
        query_embedding=embedding,
        agent_id=None if agent_id == "*" else agent_id,
        memory_type=memory_type,
        thread_id=thread_id,
        threshold=threshold,
        limit=limit,
    )

    # Also surface the latest scratchpad as a pseudo-memory entry
    scratch = await db.get_scratchpad(thread_id)
    results: List[Dict[str, Any]] = []
    if memories:
        results.extend(memories)
    if scratch:
        results.append({
            "type": "scratchpad",
            "content": scratch[:1500],
            "agent_id": "shared",
            "memory_type": "scratchpad",
            "similarity": 1.0,
        })
    return results


async def store_memory(
    agent_id: str,
    memory_type: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
    ttl_hours: Optional[int] = None,
    parent_id: Optional[str] = None,
) -> str:
    """Embed content and persist to ``agent_memories`` table."""
    db = get_supabase()
    embedding = await embed(content)
    return await db.store_memory(
        agent_id=agent_id,
        content=content,
        embedding=embedding,
        memory_type=memory_type,
        metadata=metadata,
        parent_id=parent_id,
        ttl_hours=ttl_hours,
    )

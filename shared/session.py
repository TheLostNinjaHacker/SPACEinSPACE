"""Session persistence — spara och ladda trådar mellan omstarter."""

from typing import Optional, List, Dict
from datetime import datetime, timedelta
from shared.supabase_client import AgentDatabase


class SessionManager:
    def __init__(self, db: AgentDatabase):
        self.db = db

    async def list_threads(self, limit: int = 10) -> List[Dict]:
        """List the most recent thread IDs with metadata."""
        result = (
            self.db.supabase.table("agent_conversations")
            .select("thread_id, created_at, from_agent, content")
            .order("created_at", desc=True)
            .limit(limit * 3)
            .execute()
        )

        seen = {}
        for row in result.data or []:
            tid = row["thread_id"]
            if tid not in seen:
                seen[tid] = {
                    "thread_id": tid,
                    "last_active": row["created_at"],
                    "agents": set(),
                    "preview": row["content"][:100],
                }
            seen[tid]["agents"].add(row.get("from_agent", "?"))

        threads = list(seen.values())
        for t in threads:
            t["agents"] = list(t["agents"])
            t["message_count"] = await self._count_messages(t["thread_id"])
        return threads[:limit]

    async def _count_messages(self, thread_id: str) -> int:
        result = (
            self.db.supabase.table("agent_conversations")
            .select("id", count="exact")
            .eq("thread_id", thread_id)
            .execute()
        )
        return result.count or 0

    async def get_thread(self, thread_id: str, limit: int = 50) -> List[Dict]:
        """Load all messages for a thread."""
        return await self.db.get_thread_messages(thread_id, limit=limit)

    async def delete_thread(self, thread_id: str):
        """Delete a thread and its scratchpad."""
        self.db.supabase.table("agent_conversations").delete().eq("thread_id", thread_id).execute()
        self.db.supabase.table("scratchpad").delete().eq("thread_id", thread_id).execute()

    async def save_session_state(self, thread_id: str, state: dict):
        """Save conductor state to a simple JSON blob in Supabase."""
        data = {
            "thread_id": thread_id,
            "state_json": state,
            "saved_at": datetime.now().isoformat(),
        }
        self.db.supabase.table("scratchpad").upsert(
            {"thread_id": thread_id, "section": "session_state", "content": str(state),
             "agent_id": "system", "version": 1}
        ).execute()

    async def get_previous_thread_id(self) -> Optional[str]:
        """Get the most recent thread ID from previous sessions."""
        result = (
            self.db.supabase.table("agent_conversations")
            .select("thread_id")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]["thread_id"]
        return None

    async def threads_last_24h(self) -> int:
        """How many threads in the last 24 hours."""
        since = (datetime.now() - timedelta(hours=24)).isoformat()
        result = (
            self.db.supabase.table("agent_conversations")
            .select("thread_id", count="exact", distinct="thread_id")
            .gte("created_at", since)
            .execute()
        )
        return result.count or 0

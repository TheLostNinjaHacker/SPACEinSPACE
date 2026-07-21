"""Scratchpad manager — section-aware markdown shared working memory.

Stores one row per (thread_id, section) and concatenates them into a single
markdown document using simple ``## Section`` headers.
"""
from __future__ import annotations

import re
from typing import Optional, Dict, Any

from shared.supabase_client import (
    AgentDatabase,
    SCRATCHPAD_TEMPLATE,
    get_supabase,
)


class ScratchpadManager:
    """Async scratchpad wrapper. Delegates all Supabase I/O to AgentDatabase."""

    def __init__(self, db: Optional[AgentDatabase] = None) -> None:
        self.db = db or get_supabase()

    async def get(self, thread_id: str) -> str:
        """Return the latest full scratchpad as a markdown string."""
        return await self.db.get_scratchpad(thread_id)

    async def get_sections(self, thread_id: str) -> Dict[str, str]:
        """Return a {section: content} dict of latest per section."""
        return await self.db.get_thread_sections(thread_id)

    async def update(self, thread_id: str, content: str, agent_id: str,
                     section: str = "general") -> int:
        """Replace the `section` of the scratchpad with `content`."""
        return await self.db.upsert_scratchpad(
            thread_id=thread_id,
            section=section,
            content=content,
            agent_id=agent_id,
        )

    async def update_section(
        self, thread_id: str, section: str, new_text: str, agent_id: str
    ) -> int:
        """Append/replace inside the named section while preserving the rest.

        Strategy: read full markdown, splice `## section` body with `new_text`,
        then re-upsert the whole document under that section slot.
        """
        current = await self.get(thread_id)
        spliced = _splice_section(current, section, new_text)
        return await self.db.upsert_scratchpad(
            thread_id=thread_id,
            section=section,
            content=spliced,
            agent_id=agent_id,
        )


def _splice_section(markdown: str, section: str, new_text: str) -> str:
    """Replace the body of ``## {section}`` with ``new_text``. Keeps other
    sections untouched. Creates the section if missing."""
    header = f"## {section}"
    pattern = re.compile(
        rf"(^## {re.escape(section)}\s*\n)(.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )

    if pattern.search(markdown):
        return pattern.sub(lambda m: m.group(1) + new_text + "\n\n", markdown, count=1)

    # Section not present — append at the end
    if not markdown.endswith("\n"):
        markdown += "\n"
    return f"{markdown}\n{header}\n\n{new_text}\n"


# Re-export for callers that imported the template directly.
__all__ = ["ScratchpadManager", "SCRATCHPAD_TEMPLATE", "_splice_section"]

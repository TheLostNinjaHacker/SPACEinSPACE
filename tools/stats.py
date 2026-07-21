"""Tool-tuning — statistik, failure patterns och auto-justering av prompts."""

import json
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta

from shared.supabase_client import AgentDatabase
from tools.registry import TOOL_DEFINITIONS, ToolDef


class ToolStats:
    """Aggregated statistics for a single tool."""

    def __init__(self, tool_name: str, definition: Optional[ToolDef] = None):
        self.tool_name = tool_name
        self.definition = definition
        self.call_count = 0
        self.fail_count = 0
        self.total_latency_ms = 0
        self.latencies: List[int] = []
        self.errors: Dict[str, int] = {}  # error_message -> count
        self.last_used: Optional[datetime] = None
        self.recent_successes: List[str] = []
        self.recent_failures: List[str] = []

    @property
    def fail_rate(self) -> float:
        return self.fail_count / self.call_count if self.call_count > 0 else 0.0

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.call_count if self.call_count > 0 else 0.0

    @property
    def top_errors(self) -> List[str]:
        return sorted(self.errors.keys(), key=lambda k: self.errors[k], reverse=True)[:5]

    def record(self, success: bool, latency_ms: int, error: Optional[str] = None, params: Optional[Dict] = None):
        self.call_count += 1
        self.total_latency_ms += latency_ms
        self.latencies.append(latency_ms)
        self.last_used = datetime.now()
        if len(self.latencies) > 1000:
            self.latencies.pop(0)

        if success:
            self.recent_successes.append(json.dumps(params) if params else "ok")
            if len(self.recent_successes) > 10:
                self.recent_successes.pop(0)
        else:
            self.fail_count += 1
            err_key = (error or "unknown")[:80]
            self.errors[err_key] = self.errors.get(err_key, 0) + 1
            self.recent_failures.append(error or "unknown")
            if len(self.recent_failures) > 10:
                self.recent_failures.pop(0)

    def suggestion(self) -> Optional[str]:
        """Generate a prompt-tuning suggestion based on failure patterns."""
        if self.call_count < 3:
            return None  # not enough data

        if self.fail_rate > 0.3:
            if self.definition:
                hints = []
                for pattern, hint in self.definition.failure_patterns.items():
                    if any(pattern in e for e in self.top_errors):
                        hints.append(hint)
                if hints:
                    return (
                        f"⚠️ High failure rate ({self.fail_rate:.0%}) for {self.tool_name}. "
                        f"Add to prompt: 'Remember: {'; '.join(hints)}'"
                    )
            return f"⚠️ High failure rate ({self.fail_rate:.0%}) for {self.tool_name}. Consider adding more validation before calling."

        if self.avg_latency_ms > 5000:
            return f"⚠️ Slow tool ({self.avg_latency_ms:.0f}ms avg): {self.tool_name}. Warn agents about expected latency."

        return None

    def to_dict(self) -> dict:
        return {
            "tool_name": self.tool_name,
            "call_count": self.call_count,
            "fail_count": self.fail_count,
            "fail_rate": round(self.fail_rate, 3),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "top_errors": self.top_errors,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "suggestion": self.suggestion(),
        }


class ToolTuning:
    """Collects tool statistics and generates prompt-tuning suggestions."""

    def __init__(self, db: AgentDatabase):
        self.db = db
        self.stats: Dict[str, ToolStats] = {}
        self._last_sync: Optional[datetime] = None

    def _ensure(self, tool_name: str) -> ToolStats:
        if tool_name not in self.stats:
            self.stats[tool_name] = ToolStats(
                tool_name, TOOL_DEFINITIONS.get(tool_name)
            )
        return self.stats[tool_name]

    def record(self, tool_name: str, success: bool, latency_ms: int,
               error: Optional[str] = None, params: Optional[Dict] = None):
        self._ensure(tool_name).record(success, latency_ms, error, params)

    async def sync_from_db(self, hours: int = 24):
        """Load tool call statistics from the database."""
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        result = (
            self.db.supabase.table("tool_calls")
            .select("tool_name, success, latency_ms, error_message, input_params")
            .gte("created_at", since)
            .execute()
        )

        for row in result.data or []:
            s = self._ensure(row["tool_name"])
            s.record(
                success=row.get("success", True),
                latency_ms=row.get("latency_ms", 0) or 0,
                error=row.get("error_message"),
                params=row.get("input_params"),
            )

        self._last_sync = datetime.now()

    def suggestions(self) -> List[str]:
        """Get all prompt-tuning suggestions."""
        return [
            s.suggestion() for s in self.stats.values()
            if s.suggestion()
        ]

    def report(self) -> Dict[str, Any]:
        return {
            "total_tools": len(self.stats),
            "total_calls": sum(s.call_count for s in self.stats.values()),
            "overall_fail_rate": round(
                sum(s.fail_count for s in self.stats.values()) /
                max(sum(s.call_count for s in self.stats.values()), 1), 3
            ),
            "tools": {name: s.to_dict() for name, s in self.stats.items()},
            "suggestions": self.suggestions(),
            "last_sync": self._last_sync.isoformat() if self._last_sync else None,
        }

    def worst_performers(self, top_n: int = 5) -> List[ToolStats]:
        """Get the worst-performing tools sorted by fail_rate * call_count."""
        with_calls = [s for s in self.stats.values() if s.call_count > 0]
        return sorted(with_calls, key=lambda s: s.fail_rate * s.call_count, reverse=True)[:top_n]

    def enriched_prompt(self, base_prompt: str) -> str:
        """Inject tuning hints into a system prompt."""
        suggestions = self.suggestions()
        if not suggestions:
            return base_prompt
        extra = "\n\n⚠️ Tool Tuning:\n" + "\n".join(f"- {s}" for s in suggestions)
        return base_prompt + extra

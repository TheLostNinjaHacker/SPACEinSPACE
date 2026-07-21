import logging
import time
from contextlib import contextmanager
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class AgentSpan:
    agent_id: str
    operation: str
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    attributes: dict = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None

    @property
    def latency_ms(self) -> Optional[float]:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return None

    def finish(self, success: bool = True, error: Optional[str] = None):
        self.end_time = datetime.now(timezone.utc)
        self.success = success
        self.error = error


class Telemetry:
    def __init__(self):
        self.logger = logging.getLogger("agent-ecosystem")
        self._spans: list[AgentSpan] = []

    def start_span(self, agent_id: str, operation: str, **attrs) -> AgentSpan:
        span = AgentSpan(agent_id=agent_id, operation=operation, attributes=attrs)
        self._spans.append(span)
        return span

    def record_span(self, span: AgentSpan):
        if span.success:
            self.logger.info(
                f"[{span.agent_id}] {span.operation} OK "
                f"({span.latency_ms:.0f}ms)"
            )
        else:
            self.logger.error(
                f"[{span.agent_id}] {span.operation} FAILED "
                f"({span.latency_ms:.0f}ms): {span.error}"
            )

    def get_recent(self, n: int = 20) -> list[AgentSpan]:
        return self._spans[-n:]


telemetry = Telemetry()

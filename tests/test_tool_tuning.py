"""Tests for ToolTuning — stats collection and prompt enrichment."""

import pytest
from tools.stats import ToolStats


class TestToolStats:
    def test_initial_state(self):
        s = ToolStats("web.search")
        assert s.call_count == 0
        assert s.fail_count == 0
        assert s.fail_rate == 0.0

    def test_record_success(self):
        s = ToolStats("web.search")
        s.record(success=True, latency_ms=100)
        assert s.call_count == 1
        assert s.fail_count == 0
        assert s.fail_rate == 0.0

    def test_record_failure(self):
        s = ToolStats("web.search")
        s.record(success=False, latency_ms=50, error="timeout")
        assert s.call_count == 1
        assert s.fail_count == 1
        assert s.fail_rate == 1.0

    def test_mixed_results(self):
        s = ToolStats("web.search")
        s.record(success=True, latency_ms=100)
        s.record(success=True, latency_ms=200)
        s.record(success=False, latency_ms=50, error="timeout")
        assert s.call_count == 3
        assert s.fail_count == 1
        assert s.fail_rate == pytest.approx(0.333, 0.01)
        assert s.avg_latency_ms == pytest.approx(116.67, 0.01)

    def test_avg_latency_no_calls(self):
        s = ToolStats("web.search")
        assert s.avg_latency_ms == 0.0

    def test_top_errors_empty(self):
        s = ToolStats("web.search")
        assert s.top_errors == []

    def test_top_errors_with_data(self):
        s = ToolStats("web.search")
        s.record(success=False, latency_ms=10, error="timeout")
        s.record(success=False, latency_ms=10, error="connection refused")
        s.record(success=False, latency_ms=10, error="timeout")
        assert "timeout" in s.top_errors
        assert "connection" in s.top_errors[1]

    def test_no_suggestion_with_few_calls(self):
        s = ToolStats("web.search")
        s.record(success=True, latency_ms=10)
        assert s.suggestion() is None

    def test_suggestion_high_fail_rate(self):
        s = ToolStats("file.read")
        s.record(success=False, latency_ms=10, error="not found")
        s.record(success=False, latency_ms=10, error="not found")
        s.record(success=False, latency_ms=10, error="not found")
        s.record(success=True, latency_ms=10)
        sugg = s.suggestion()
        assert sugg is not None
        assert "High failure rate" in sugg

    def test_latency_suggestion(self):
        s = ToolStats("slow.tool")
        s.record(success=True, latency_ms=6000)
        s.record(success=True, latency_ms=7000)
        s.record(success=True, latency_ms=8000)
        sugg = s.suggestion()
        assert sugg is not None
        assert "latency" in sugg.lower()

    def test_to_dict(self):
        s = ToolStats("web.search")
        s.record(success=True, latency_ms=100)
        d = s.to_dict()
        assert d["tool_name"] == "web.search"
        assert d["call_count"] == 1
        assert d["fail_rate"] == 0.0

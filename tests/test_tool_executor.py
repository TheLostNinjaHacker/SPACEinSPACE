"""Tests for the tool executor — parsing, validation, and execution."""

import pytest
from shared.tool_executor import ToolExecutor, _resolve_within_project


class TestParseToolCalls:
    def setup_method(self):
        self.executor = ToolExecutor(db=None)

    def test_parse_single_tool_block(self):
        text = 'Some text\n```tool\n{"name": "web.search", "arguments": {"query": "test"}}\n```\nmore'
        calls = self.executor.parse_tool_calls(text)
        assert len(calls) == 1
        assert calls[0]["name"] == "web.search"
        assert calls[0]["arguments"]["query"] == "test"

    def test_parse_json_fence(self):
        text = '```json\n{"name": "math.eval", "arguments": {"expression": "2+2"}}\n```'
        calls = self.executor.parse_tool_calls(text)
        assert len(calls) == 1
        assert calls[0]["name"] == "math.eval"

    def test_parse_single_quotes(self):
        text = "```tool\n{'name': 'web.search', 'arguments': {'query': 'hello'}}\n```"
        calls = self.executor.parse_tool_calls(text)
        assert len(calls) == 1
        assert calls[0]["name"] == "web.search"

    def test_parse_parameters_alias(self):
        text = '```tool\n{"name": "file.read", "parameters": {"path": "test.txt"}}\n```'
        calls = self.executor.parse_tool_calls(text)
        assert len(calls) == 1
        assert "path" in calls[0]["arguments"]

    def test_no_tool_blocks(self):
        text = "Just some regular text with no tool calls."
        calls = self.executor.parse_tool_calls(text)
        assert len(calls) == 0

    def test_multiple_tool_blocks(self):
        text = (
            '```tool\n{"name": "web.search", "arguments": {"query": "a"}}\n```\n'
            '```tool\n{"name": "math.eval", "arguments": {"expression": "1+1"}}\n```'
        )
        calls = self.executor.parse_tool_calls(text)
        assert len(calls) == 2

    def test_invalid_json_skipped(self):
        text = '```tool\n{invalid json}\n```'
        calls = self.executor.parse_tool_calls(text)
        assert len(calls) == 0

    def test_missing_name_skipped(self):
        text = '```tool\n{"arguments": {"x": 1}}\n```'
        calls = self.executor.parse_tool_calls(text)
        assert len(calls) == 0


class TestValidateArguments:
    def setup_method(self):
        self.executor = ToolExecutor(db=None)
        # Manually inject a tool def for testing
        from tools.registry import ToolDef
        self.executor._tool_defs["test.tool"] = ToolDef(
            name="test.tool", version="1.0",
            description="test",
            parameters_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "enum": ["a", "b"]},
                    "value": {"type": "integer"},
                },
                "required": ["name"],
            },
        )

    def test_valid(self):
        errors = self.executor.validate_arguments("test.tool", {"name": "a", "value": 42})
        assert errors == []

    def test_missing_required(self):
        errors = self.executor.validate_arguments("test.tool", {"value": 42})
        assert len(errors) == 1
        assert "name" in errors[0]

    def test_invalid_enum(self):
        errors = self.executor.validate_arguments("test.tool", {"name": "c"})
        assert len(errors) == 1
        assert "c" in errors[0]

    def test_unknown_tool_no_errors(self):
        errors = self.executor.validate_arguments("unknown.tool", {"x": 1})
        assert errors == []


class TestBuiltinTools:
    @pytest.mark.asyncio
    async def test_math_eval(self):
        executor = ToolExecutor(db=None)
        result = await executor.execute(
            {"name": "math.eval", "arguments": {"expression": "2+2"}},
            thread_id="t1", agent_id="test",
        )
        assert result["success"]
        assert result["result"]["result"] == 4

    @pytest.mark.asyncio
    async def test_math_eval_unsafe(self):
        executor = ToolExecutor(db=None)
        result = await executor.execute(
            {"name": "math.eval", "arguments": {"expression": "__import__('os')"}},
            thread_id="t1", agent_id="test",
        )
        assert not result["success"]

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        executor = ToolExecutor(db=None)
        result = await executor.execute(
            {"name": "nonexistent.tool", "arguments": {}},
            thread_id="t1", agent_id="test",
        )
        assert not result["success"]
        assert "Unknown" in result["error"]

    @pytest.mark.asyncio
    async def test_file_write_and_read(self):
        import os, pathlib
        import shared.tool_executor as te

        orig_root = te.PROJECT_ROOT
        tmp = str(te.PROJECT_ROOT.parent / ".test_sandbox")
        try:
            te.PROJECT_ROOT = pathlib.Path(tmp)
            executor2 = ToolExecutor(db=None)

            write_result = await executor2.execute(
                {"name": "file.write", "arguments": {"path": "test.txt", "content": "hello world"}},
                thread_id="t1", agent_id="test",
            )
            assert write_result["success"]
            assert write_result["result"]["bytes"] == 11

            read_result = await executor2.execute(
                {"name": "file.read", "arguments": {"path": "test.txt"}},
                thread_id="t1", agent_id="test",
            )
            assert read_result["success"]
            assert "hello world" in read_result["result"]["content"]
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
            te.PROJECT_ROOT = orig_root

    @pytest.mark.asyncio
    async def test_path_traversal_blocked(self):
        executor = ToolExecutor(db=None)
        result = await executor.execute(
            {"name": "file.read", "arguments": {"path": "/etc/passwd"}},
            thread_id="t1", agent_id="test",
        )
        assert not result["success"]


class TestExecuteAll:
    @pytest.mark.asyncio
    async def test_multiple_calls_in_text(self):
        executor = ToolExecutor(db=None)
        text = (
            'Step 1: compute\n```tool\n{"name": "math.eval", "arguments": {"expression": "1+1"}}\n```\n'
            'Step 2: compute again\n```tool\n{"name": "math.eval", "arguments": {"expression": "2+2"}}\n```'
        )
        results = await executor.execute_all(text, thread_id="t1", agent_id="test")
        assert len(results) == 2
        assert results[0]["success"]
        assert results[0]["result"]["result"] == 2
        assert results[1]["success"]
        assert results[1]["result"]["result"] == 4

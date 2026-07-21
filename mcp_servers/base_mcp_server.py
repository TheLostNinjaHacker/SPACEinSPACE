from typing import Any, Callable, Awaitable
import json
import asyncio
import logging


ToolHandler = Callable[..., Awaitable[dict]]


class BaseMCPServer:
    def __init__(self, name: str):
        self.name = name
        self.tools: dict[str, ToolHandler] = {}
        self.logger = logging.getLogger(f"mcp.{name}")

    def register(self, name: str = None):
        def decorator(func: ToolHandler):
            tool_name = name or func.__name__.replace("_", ".")
            self.tools[tool_name] = func
            self.logger.info(f"Registered tool: {tool_name}")
            return func
        return decorator

    async def handle_request(self, request: dict) -> dict:
        tool_name = request.get("name")
        arguments = request.get("arguments", {})
        tool_id = request.get("id", "")

        if tool_name not in self.tools:
            return {"id": tool_id, "error": f"Unknown tool: {tool_name}", "success": False}

        try:
            result = await self.tools[tool_name](**arguments)
            return {"id": tool_id, "result": result, "success": True}
        except Exception as e:
            self.logger.error(f"Tool {tool_name} failed: {e}")
            return {"id": tool_id, "error": str(e), "success": False}

    async def list_tools(self) -> list[dict]:
        return [{"name": name, "description": func.__doc__} for name, func in self.tools.items()]

    async def run_stdio(self):
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, 0)
        writer = loop.connect_write_pipe(lambda: asyncio.IncompleteReadError, 1)
        self.logger.info(f"MCP server '{self.name}' running on stdio")
        while True:
            line = await reader.readline()
            if not line:
                break
            try:
                request = json.loads(line.decode().strip())
                response = await self.handle_request(request)
            except Exception as e:
                response = {"error": str(e), "success": False}
            print(json.dumps(response), flush=True)

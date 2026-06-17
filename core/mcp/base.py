"""Base MCP server abstraction used by core and capability connectors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from core.schemas.base import MCPTool

MCPTransport = Literal["streamable-http", "stdio"]
MCPToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(slots=True)
class MCPServer:
    """A registered MCP server endpoint or deterministic mock."""

    name: str
    tools: list[MCPTool]
    url: str | None = None
    mock_mode: bool = False
    transport: MCPTransport = "streamable-http"
    handlers: dict[str, MCPToolHandler] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.transport not in ("streamable-http", "stdio"):
            raise ValueError("MCP transport must be 'streamable-http' or 'stdio'")

        available = {tool.name for tool in self.tools}
        unknown_handlers = sorted(set(self.handlers) - available)
        if unknown_handlers:
            raise ValueError(f"Handlers registered for unknown tools: {unknown_handlers}")

    @property
    def tool_names(self) -> list[str]:
        return [tool.name for tool in self.tools]

    def has_tool(self, tool_name: str) -> bool:
        return tool_name in self.tool_names

    def call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """Call a registered tool handler.

        Real transport adapters will replace this with network calls in later
        tasks. Mock servers use the same method so capability tests can run
        without external services.
        """

        if not self.has_tool(tool_name):
            raise KeyError(f"MCP server '{self.name}' has no tool '{tool_name}'")
        if tool_name not in self.handlers:
            raise NotImplementedError(f"MCP tool '{self.name}.{tool_name}' has no handler")
        return self.handlers[tool_name](arguments or {})

    def health_check(self) -> bool:
        if self.mock_mode:
            return True
        return bool(self.url)


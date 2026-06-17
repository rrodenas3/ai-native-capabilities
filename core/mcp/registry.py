"""Registry for MCP server connections."""

from __future__ import annotations

import os
from collections.abc import Callable

from core.mcp.base import MCPServer, MCPTransport


class MCPRegistry:
    """Central registry for capability MCP connectors."""

    def __init__(self) -> None:
        self._servers: dict[str, MCPServer] = {}

    def register(self, name: str, server: MCPServer) -> None:
        if name != server.name:
            raise ValueError(f"Registry key '{name}' does not match server name '{server.name}'")
        if name in self._servers:
            raise ValueError(f"MCP server '{name}' is already registered")
        self._servers[name] = server

    def get(self, name: str) -> MCPServer:
        try:
            return self._servers[name]
        except KeyError as exc:
            raise KeyError(f"MCP server '{name}' is not registered") from exc

    def list(self) -> list[str]:
        return sorted(self._servers)

    def health_check(self) -> dict[str, bool]:
        return {name: server.health_check() for name, server in sorted(self._servers.items())}

    def register_from_env(
        self,
        name: str,
        mock_factory: Callable[[], MCPServer],
        real_factory: Callable[[str, MCPTransport], MCPServer] | None = None,
        *,
        transport: MCPTransport | None = None,
    ) -> MCPServer:
        """Register a real server when URL is configured, otherwise its mock."""

        resolved_transport = transport or os.getenv("MCP_TRANSPORT", "streamable-http")
        if resolved_transport not in ("streamable-http", "stdio"):
            raise ValueError("MCP_TRANSPORT must be 'streamable-http' or 'stdio'")

        env_key = f"MCP_{name.upper().replace('-', '_')}_URL"
        url = os.getenv(env_key, "").strip()

        if url:
            if real_factory is None:
                raise ValueError(f"{env_key} is set but no real factory was provided")
            server = real_factory(url, resolved_transport)  # type: ignore[arg-type]
        else:
            server = mock_factory()

        self.register(name, server)
        return server


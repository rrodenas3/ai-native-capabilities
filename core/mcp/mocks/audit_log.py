"""Mock append-only audit-log MCP server."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.mcp.base import MCPServer
from core.schemas.base import MCPTool


def create_audit_log_mock() -> MCPServer:
    events: list[dict[str, Any]] = []

    def log_event(arguments: dict[str, Any]) -> dict[str, Any]:
        event = {
            "id": str(uuid4()),
            "created_at": datetime.now(UTC).isoformat(),
            **arguments,
        }
        events.append(event)
        return {"event": event}

    def query_trail(arguments: dict[str, Any]) -> dict[str, Any]:
        run_id = arguments.get("run_id")
        capability = arguments.get("capability")
        results = events
        if run_id is not None:
            results = [event for event in results if event.get("run_id") == run_id]
        if capability is not None:
            results = [event for event in results if event.get("capability") == capability]
        return {"events": list(results)}

    tools = [
        MCPTool(name="log_event", description="Append an audit event", input_schema={}),
        MCPTool(name="query_trail", description="Query audit events", input_schema={}),
    ]
    return MCPServer(
        name="audit-log",
        tools=tools,
        mock_mode=True,
        handlers={"log_event": log_event, "query_trail": query_trail},
    )

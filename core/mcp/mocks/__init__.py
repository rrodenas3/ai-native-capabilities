"""Deterministic mock MCP servers for local development and tests."""

from core.mcp.mocks.audit_log import create_audit_log_mock
from core.mcp.mocks.knowledge_base import create_knowledge_base_mock
from core.mcp.mocks.web_research import create_web_research_mock

__all__ = [
    "create_audit_log_mock",
    "create_default_mock_registry",
    "create_knowledge_base_mock",
    "create_web_research_mock",
]


def create_default_mock_registry():
    from core.mcp.registry import MCPRegistry

    registry = MCPRegistry()
    for server in (
        create_knowledge_base_mock(),
        create_web_research_mock(),
        create_audit_log_mock(),
    ):
        registry.register(server.name, server)
    return registry


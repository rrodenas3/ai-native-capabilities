from __future__ import annotations

import os

import pytest

from core.mcp import MCPRegistry, MCPServer
from core.mcp.mocks import (
    create_audit_log_mock,
    create_default_mock_registry,
    create_knowledge_base_mock,
    create_web_research_mock,
)
from core.schemas.base import MCPTool


def test_registry_register_get_and_health_check() -> None:
    registry = MCPRegistry()
    server = create_knowledge_base_mock()

    registry.register(server.name, server)

    assert registry.get("internal-knowledge-base") is server
    assert registry.health_check() == {"internal-knowledge-base": True}


def test_registry_rejects_duplicate_names() -> None:
    registry = MCPRegistry()
    server = create_web_research_mock()
    registry.register(server.name, server)

    with pytest.raises(ValueError):
        registry.register(server.name, server)


def test_server_rejects_sse_transport() -> None:
    with pytest.raises(ValueError):
        MCPServer(
            name="bad",
            tools=[MCPTool(name="search", description="Search", input_schema={})],
            transport="sse",  # type: ignore[arg-type]
        )


def test_call_tool_validates_registered_tools() -> None:
    server = create_web_research_mock()

    with pytest.raises(KeyError):
        server.call_tool("missing")


def test_knowledge_base_mock_contract() -> None:
    server = create_knowledge_base_mock()

    search_result = server.call_tool("search", {"query": "supply chain"})
    document_id = search_result["results"][0]["id"]
    document_result = server.call_tool("get_document", {"id": document_id})
    metadata_result = server.call_tool("get_metadata", {"id": document_id})
    recent_result = server.call_tool("list_recent", {"limit": 1})

    assert document_result["document"]["id"] == document_id
    assert metadata_result["metadata"]["access_tier"] == "internal"
    assert len(recent_result["documents"]) == 1


def test_web_research_mock_contract() -> None:
    server = create_web_research_mock()

    search_result = server.call_tool("search", {"query": "mcp"})
    page = server.call_tool("fetch_url", {"url": search_result["results"][0]["url"]})

    assert page["page"]["title"] == "MCP Reference"


def test_audit_log_mock_is_append_only_for_queries() -> None:
    server = create_audit_log_mock()
    server.call_tool(
        "log_event",
        {"capability": "cap-01", "run_id": "run-1", "event_type": "test"},
    )
    server.call_tool(
        "log_event",
        {"capability": "cap-02", "run_id": "run-2", "event_type": "test"},
    )

    result = server.call_tool("query_trail", {"run_id": "run-1"})

    assert len(result["events"]) == 1
    assert result["events"][0]["capability"] == "cap-01"


def test_default_mock_registry_contains_required_connectors() -> None:
    registry = create_default_mock_registry()

    assert registry.list() == ["audit-log", "internal-knowledge-base", "web-research"]
    assert registry.health_check() == {
        "audit-log": True,
        "internal-knowledge-base": True,
        "web-research": True,
    }


def test_register_from_env_uses_mock_when_url_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MCP_INTERNAL_KNOWLEDGE_BASE_URL", raising=False)
    registry = MCPRegistry()

    server = registry.register_from_env("internal-knowledge-base", create_knowledge_base_mock)

    assert server.mock_mode is True


def test_register_from_env_uses_streamable_http_real_server(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_TRANSPORT", "streamable-http")
    monkeypatch.setenv("MCP_AUDIT_LOG_URL", "https://mcp.example.test/audit")
    registry = MCPRegistry()

    def real_factory(url: str, transport: str) -> MCPServer:
        return MCPServer(
            name="audit-log",
            url=url,
            transport=transport,  # type: ignore[arg-type]
            tools=[MCPTool(name="log_event", description="Append", input_schema={})],
        )

    server = registry.register_from_env("audit-log", create_audit_log_mock, real_factory)

    assert server.mock_mode is False
    assert server.url == "https://mcp.example.test/audit"
    assert server.transport == "streamable-http"
    assert os.getenv("MCP_TRANSPORT") != "sse"


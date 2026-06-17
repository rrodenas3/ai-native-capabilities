"""Mock internal knowledge-base MCP server."""

from __future__ import annotations

from typing import Any

from core.mcp.base import MCPServer
from core.schemas.base import MCPTool

DOCUMENTS = [
    {
        "id": "strategy-q3",
        "title": "Q3 Strategy Risks",
        "content": "Supply chain risk is elevated entering Q3 due to supplier concentration.",
        "metadata": {"doc_type": "strategy", "date": "2026-06-01", "access_tier": "internal"},
    },
    {
        "id": "board-ai-governance",
        "title": "AI Governance Board Update",
        "content": "Human approval is required for irreversible agent actions above threshold.",
        "metadata": {"doc_type": "board", "date": "2026-05-20", "access_tier": "internal"},
    },
]


def create_knowledge_base_mock() -> MCPServer:
    def search(arguments: dict[str, Any]) -> dict[str, Any]:
        query = str(arguments.get("query", "")).lower()
        limit = int(arguments.get("limit", 10))
        results = [
            doc
            for doc in DOCUMENTS
            if query in doc["title"].lower() or query in doc["content"].lower()
        ]
        if not results and query:
            results = DOCUMENTS[:1]
        return {"results": results[:limit]}

    def get_document(arguments: dict[str, Any]) -> dict[str, Any]:
        doc_id = arguments["id"]
        for doc in DOCUMENTS:
            if doc["id"] == doc_id:
                return {"document": doc}
        raise KeyError(f"document '{doc_id}' not found")

    def list_recent(arguments: dict[str, Any]) -> dict[str, Any]:
        limit = int(arguments.get("limit", 10))
        docs = sorted(DOCUMENTS, key=lambda doc: doc["metadata"]["date"], reverse=True)
        return {"documents": docs[:limit]}

    def get_metadata(arguments: dict[str, Any]) -> dict[str, Any]:
        doc_id = arguments["id"]
        for doc in DOCUMENTS:
            if doc["id"] == doc_id:
                return {"metadata": doc["metadata"]}
        raise KeyError(f"metadata for document '{doc_id}' not found")

    tools = [
        MCPTool(name="search", description="Search indexed internal documents", input_schema={}),
        MCPTool(name="get_document", description="Fetch a document by id", input_schema={}),
        MCPTool(name="list_recent", description="List recent documents", input_schema={}),
        MCPTool(name="get_metadata", description="Fetch document metadata", input_schema={}),
    ]
    return MCPServer(
        name="internal-knowledge-base",
        tools=tools,
        mock_mode=True,
        handlers={
            "search": search,
            "get_document": get_document,
            "list_recent": list_recent,
            "get_metadata": get_metadata,
        },
    )


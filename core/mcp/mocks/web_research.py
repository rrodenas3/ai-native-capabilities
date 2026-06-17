"""Mock web-research MCP server."""

from __future__ import annotations

from typing import Any

from core.mcp.base import MCPServer
from core.schemas.base import MCPTool

PAGES = {
    "https://example.com/mcp": {
        "url": "https://example.com/mcp",
        "title": "MCP Reference",
        "content": "MCP Streamable HTTP is the production transport in this project.",
    }
}


def create_web_research_mock() -> MCPServer:
    def search(arguments: dict[str, Any]) -> dict[str, Any]:
        query = str(arguments.get("query", "")).lower()
        results = [
            {"url": page["url"], "title": page["title"], "snippet": page["content"]}
            for page in PAGES.values()
            if not query or query in page["title"].lower() or query in page["content"].lower()
        ]
        return {"results": results}

    def fetch_url(arguments: dict[str, Any]) -> dict[str, Any]:
        url = arguments["url"]
        if url not in PAGES:
            raise KeyError(f"url '{url}' not found")
        return {"page": PAGES[url]}

    tools = [
        MCPTool(name="search", description="Search controlled web sources", input_schema={}),
        MCPTool(name="fetch_url", description="Fetch a controlled URL", input_schema={}),
    ]
    return MCPServer(
        name="web-research",
        tools=tools,
        mock_mode=True,
        handlers={"search": search, "fetch_url": fetch_url},
    )


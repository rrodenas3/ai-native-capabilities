"""In-memory property graph with Neo4j-compatible CRUD method names."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


class KnowledgeGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: list[dict[str, Any]] = []

    def add_node(self, label: str, node_id: str, properties: dict[str, Any]) -> dict[str, Any]:
        if not node_id:
            raise ValueError("node_id is required")
        node = {"id": node_id, "label": label, **dict(properties)}
        self.nodes[node_id] = node
        return node

    def add_edge(
        self,
        source_id: str,
        relationship: str,
        target_id: str,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if source_id not in self.nodes or target_id not in self.nodes:
            raise ValueError("source and target nodes must exist before adding edge")
        edge = {
            "source_id": source_id,
            "relationship": relationship,
            "target_id": target_id,
            "properties": dict(properties or {}),
        }
        self.edges.append(edge)
        return edge

    def update_node(self, node_id: str, properties: dict[str, Any]) -> dict[str, Any]:
        if node_id not in self.nodes:
            raise KeyError(node_id)
        self.nodes[node_id].update(properties)
        return self.nodes[node_id]

    def query_graph(self, label: str | None = None, relationship: str | None = None) -> list[dict[str, Any]]:
        if relationship is not None:
            return [edge for edge in self.edges if edge["relationship"] == relationship]
        if label is None:
            return list(self.nodes.values())
        return [node for node in self.nodes.values() if node.get("label") == label]

    def get_obligations(self, confirmed_only: bool = False) -> list[dict[str, Any]]:
        obligations = self.query_graph(label="Obligation")
        if confirmed_only:
            obligations = [obl for obl in obligations if obl.get("expert_confirmed") is True]
        return obligations

    def get_gaps(self) -> list[dict[str, Any]]:
        return self.query_graph(label="GapReport")

    def relationship_counts(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for edge in self.edges:
            counts[edge["relationship"]] += 1
        return dict(counts)

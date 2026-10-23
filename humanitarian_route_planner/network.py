"""Network loading, validation, distance calculations, and edge filtering."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from .models import CostWeights, Edge, Node


# Approximate multipliers used only to give the schematic map a mode-aware
# estimate above straight-line distance. They are not route-distance data.
MODE_DISTANCE_FACTORS = {
    "air": 1.05,
    "sea": 1.25,
    "road": 1.18,
    "land convoy": 1.18,
    "sea + road": 1.30,
    "multimodal": 1.25,
}


def haversine_km(a: Node, b: Node) -> float:
    """Great-circle distance between two node coordinates, in kilometres."""
    radius_km = 6371.0088
    lat1, lon1, lat2, lon2 = map(
        math.radians, (a.latitude, a.longitude, b.latitude, b.longitude)
    )
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * radius_km * math.asin(min(1.0, math.sqrt(h)))


class RouteNetwork:
    """Validated, undirected transport network for route-planning experiments."""

    def __init__(self, nodes: Iterable[Node], edges: Iterable[Edge], metadata: dict | None = None):
        node_list = list(nodes)
        edge_list = list(edges)
        if len(node_list) != len({node.node_id for node in node_list}):
            raise ValueError("Node IDs must be unique.")
        if len(edge_list) != len({edge.edge_id for edge in edge_list}):
            raise ValueError("Edge IDs must be unique.")
        self.nodes = {node.node_id: node for node in node_list}
        self.edges = {edge.edge_id: edge for edge in edge_list}
        self.metadata = metadata or {}
        self._adjacency: dict[str, list[Edge]] = defaultdict(list)
        self._validate_and_index()

    @classmethod
    def from_json(cls, path: str | Path) -> "RouteNetwork":
        with Path(path).open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        nodes = [Node(**raw) for raw in payload.get("nodes", [])]
        edges = [Edge(**raw) for raw in payload.get("edges", [])]
        return cls(nodes, edges, payload.get("metadata", {}))

    def _validate_and_index(self) -> None:
        if not self.nodes:
            raise ValueError("The network must contain at least one node.")
        if len(self.nodes) != len(set(self.nodes)):
            raise ValueError("Node IDs must be unique.")
        if len(self.edges) != len(set(self.edges)):
            raise ValueError("Edge IDs must be unique.")
        for node in self.nodes.values():
            if not (-90 <= node.latitude <= 90 and -180 <= node.longitude <= 180):
                raise ValueError(f"Invalid coordinates for node {node.node_id}.")
        for edge in self.edges.values():
            if edge.source not in self.nodes or edge.target not in self.nodes:
                raise ValueError(f"Edge {edge.edge_id} references an unknown node.")
            if edge.source == edge.target:
                raise ValueError(f"Edge {edge.edge_id} cannot connect a node to itself.")
            if edge.time_hours < 0 or edge.cost_usd < 0 or edge.capacity_tonnes <= 0:
                raise ValueError(f"Edge {edge.edge_id} has invalid time, cost, or capacity.")
            if not 0 <= edge.risk_score <= 10:
                raise ValueError(f"Edge {edge.edge_id} risk_score must be between 0 and 10.")
            self._adjacency[edge.source].append(edge)
            self._adjacency[edge.target].append(edge)

    def neighbors(
        self,
        node_id: str,
        blocked_nodes: set[str] | None = None,
        blocked_edges: set[str] | None = None,
    ) -> list[tuple[str, Edge]]:
        """Get usable adjacent nodes and connecting edges.

        Connections are modelled as bidirectional in this demonstrator. A
        production system would need direction, schedules, border rules,
        vehicle restrictions, and confirmed corridor permissions.
        """
        blocked_nodes = blocked_nodes or set()
        blocked_edges = blocked_edges or set()
        if node_id in blocked_nodes:
            return []
        output: list[tuple[str, Edge]] = []
        for edge in self._adjacency.get(node_id, []):
            if edge.edge_id in blocked_edges:
                continue
            other = edge.target if edge.source == node_id else edge.source
            if other in blocked_nodes:
                continue
            output.append((other, edge))
        return output

    def edge_distance_km(self, edge: Edge) -> float:
        """Approximate teaching distance for an edge, not a real route length."""
        direct = haversine_km(self.nodes[edge.source], self.nodes[edge.target])
        factor = MODE_DISTANCE_FACTORS.get(edge.mode.lower(), 1.25)
        # The small epsilon avoids a zero denominator for colocated nodes.
        return max(0.1, direct * factor)

    def active_edges(
        self,
        blocked_nodes: set[str] | None = None,
        blocked_edges: set[str] | None = None,
    ) -> list[Edge]:
        blocked_nodes = blocked_nodes or set()
        blocked_edges = blocked_edges or set()
        return [
            edge for edge in self.edges.values()
            if edge.edge_id not in blocked_edges
            and edge.source not in blocked_nodes
            and edge.target not in blocked_nodes
        ]

    def route_totals(self, edge_ids: list[str], weights: CostWeights) -> dict[str, float | None]:
        """Sum the raw route metrics and generalized objective score."""
        selected = [self.edges[edge_id] for edge_id in edge_ids]
        if not selected:
            return {
                "objective_score": 0.0,
                "total_time_hours": 0.0,
                "total_cost_usd": 0.0,
                "total_risk_points": 0.0,
                "minimum_capacity_tonnes": None,
            }
        return {
            "objective_score": sum(weights.edge_cost(edge) for edge in selected),
            "total_time_hours": sum(edge.time_hours for edge in selected),
            "total_cost_usd": sum(edge.cost_usd for edge in selected),
            "total_risk_points": sum(edge.risk_score for edge in selected),
            "minimum_capacity_tonnes": min(edge.capacity_tonnes for edge in selected),
        }

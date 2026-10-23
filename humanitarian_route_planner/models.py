"""Typed domain models used by the route planner."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Node:
    """A logistics hub or illustrative destination in the network."""

    node_id: str
    name: str
    latitude: float
    longitude: float
    region: str
    node_type: str
    description: str = ""


@dataclass(frozen=True)
class Edge:
    """A transport connection between two nodes.

    Risk is an illustrative ordinal score (0-10), not a probability or an
    official security assessment. The network is a teaching dataset.
    """

    edge_id: str
    source: str
    target: str
    mode: str
    time_hours: float
    cost_usd: float
    risk_score: float
    capacity_tonnes: float
    notes: str = ""


@dataclass(frozen=True)
class CostWeights:
    """User priorities for the generalized route objective.

    score(edge) = time_weight * hours
                + cost_weight * (USD / 1,000)
                + risk_weight * risk_points

    This scalar is for comparing routes in the simulator; it is not a
    financial valuation of human life, aid, or safety.
    """

    time: float = 1.0
    cost: float = 0.75
    risk: float = 2.0

    def validate(self) -> None:
        if min(self.time, self.cost, self.risk) < 0:
            raise ValueError("Cost weights cannot be negative.")
        if self.time == self.cost == self.risk == 0:
            raise ValueError("At least one cost weight must be greater than zero.")

    def edge_cost(self, edge: Edge) -> float:
        self.validate()
        return (
            self.time * edge.time_hours
            + self.cost * (edge.cost_usd / 1000.0)
            + self.risk * edge.risk_score
        )


@dataclass
class RouteResult:
    """Output from a route-finding algorithm."""

    algorithm: str
    success: bool
    node_path: list[str] = field(default_factory=list)
    edge_path: list[str] = field(default_factory=list)
    objective_score: float | None = None
    total_time_hours: float | None = None
    total_cost_usd: float | None = None
    total_risk_points: float | None = None
    minimum_capacity_tonnes: float | None = None
    nodes_expanded: int = 0
    runtime_ms: float = 0.0
    abstract_regions: list[str] = field(default_factory=list)
    message: str = ""

    @property
    def hops(self) -> int:
        return max(0, len(self.edge_path))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON/CSV-friendly representation."""
        return {
            "algorithm": self.algorithm,
            "success": self.success,
            "node_path": self.node_path,
            "edge_path": self.edge_path,
            "objective_score": self.objective_score,
            "total_time_hours": self.total_time_hours,
            "total_cost_usd": self.total_cost_usd,
            "total_risk_points": self.total_risk_points,
            "minimum_capacity_tonnes": self.minimum_capacity_tonnes,
            "nodes_expanded": self.nodes_expanded,
            "runtime_ms": self.runtime_ms,
            "abstract_regions": self.abstract_regions,
            "message": self.message,
        }

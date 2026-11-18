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

    Risk is an illustrative ordinal score (0-10 allowed; the HRP data uses
    1-5), not a probability or an official security assessment. The optional
    fields are filled in when the data provides them.
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
    time_hours_p90: float | None = None   # slow case: 90% of trips are faster than this
    reliability_pct: float | None = None  # share of trips that run as planned
    distance_km: float | None = None      # route distance from the data
    corridor: str = ""


@dataclass(frozen=True)
class TransferRule:
    """What changing mode costs at a hub that has no transfer leg of its own.

    Applied when cargo arrives by one of air, sea or road and leaves by another
    (unloading, handling, customs and reloading). Legs whose mode is
    "transfer" already include that work, so they never trigger it.
    """

    time_hours: float
    cost_usd: float
    risk_score: float = 0.0


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

    def score(self, time_hours: float, cost_usd: float, risk_score: float) -> float:
        """Weighted score of any step: a leg or a transfer."""
        self.validate()
        return self.time * time_hours + self.cost * (cost_usd / 1000.0) + self.risk * risk_score

    def edge_cost(self, edge: Edge) -> float:
        return self.score(edge.time_hours, edge.cost_usd, edge.risk_score)


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
    transfers: int = 0
    total_time_p90_hours: float | None = None
    reliability_pct: float | None = None

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
            "transfers": self.transfers,
            "total_time_p90_hours": self.total_time_p90_hours,
            "reliability_pct": self.reliability_pct,
        }

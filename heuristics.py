"""Heuristics, checks on them, and the risk model.

Owner: Mohammed. A heuristic here is any function ``h(node_id) -> float`` that
estimates the cheapest remaining cost from a hub to the goal, in the same units
as ``CostWeights.edge_cost()``.
"""

from __future__ import annotations

from typing import Callable

from humanitarian_route_planner.models import CostWeights
from humanitarian_route_planner.network import RouteNetwork

Heuristic = Callable[[str], float]


def zero_heuristic(node_id: str) -> float:
    """Always 0: admissible, and turns A* into Dijkstra. A useful reference point."""
    return 0.0


def time_lower_bound_heuristic(network: RouteNetwork, goal: str, weights: CostWeights) -> Heuristic:
    """Return h(node_id) = weights.time * straight-line km to the goal / fastest link speed.

    The fastest link speed is the largest (straight-line km / hours) over all
    links; ``network.edge_distance_km()`` and ``haversine_km()`` in network.py help.
    """
    raise NotImplementedError("Mohammed: time_lower_bound_heuristic is not written yet")


def check_admissible(
    network: RouteNetwork,
    goal: str,
    weights: CostWeights,
    heuristic: Heuristic,
    blocked_nodes: set[str] | None = None,
    blocked_edges: set[str] | None = None,
) -> list[tuple[str, float, float]]:
    """Return (hub, h value, true cost) for every hub where h overestimates.

    An empty list means the heuristic is admissible on this network. Hubs that
    can't reach the goal can be skipped.
    """
    raise NotImplementedError("Mohammed: check_admissible is not written yet")


def check_consistent(
    network: RouteNetwork,
    weights: CostWeights,
    heuristic: Heuristic,
    blocked_nodes: set[str] | None = None,
    blocked_edges: set[str] | None = None,
) -> list[tuple[str, float]]:
    """Return (link id, size of the violation) wherever h(a) > cost(a, b) + h(b).

    Check both directions of every open link. An empty list means consistent.
    """
    raise NotImplementedError("Mohammed: check_consistent is not written yet")


def survival_weight(risk_score: float, max_probability: float = 0.3) -> float:
    """Additive weight for a link's risk under a probability model.

    Map the 0-10 score to a disruption probability p (for example
    p = max_probability * score / 10, an assumption to state in the report),
    then return -ln(1 - p). Minimising the sum of these weights along a route
    maximises the probability that every link on it stays open.
    """
    raise NotImplementedError("Mohammed: survival_weight is not written yet")

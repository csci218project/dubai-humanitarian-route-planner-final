"""Extra search algorithms to compare with Dijkstra, A* and hierarchical search.

Owner: Koushik. Each function takes the same arguments as
``humanitarian_route_planner.algorithms.dijkstra`` and returns a
``RouteResult``, so experiments and the app can call every algorithm the same way.

Tip: ``dijkstra()`` and ``a_star()`` in algorithms.py show the pattern:
validate the request with ``_validate_request()``, define ``transitions()``,
run ``_best_first_search()`` (or your own loop), then build the result with
``_result()``.
"""

from __future__ import annotations

from humanitarian_route_planner.models import CostWeights, RouteResult
from humanitarian_route_planner.network import RouteNetwork


def breadth_first_search(
    network: RouteNetwork,
    start: str,
    goal: str,
    weights: CostWeights,
    blocked_nodes: set[str] | None = None,
    blocked_edges: set[str] | None = None,
) -> RouteResult:
    """Return the route with the fewest legs, ignoring time, cost and risk.

    Still fill in the route's real time, cost, risk and score in the result,
    so it can be compared with the weighted searches.
    """
    raise NotImplementedError("Koushik: breadth_first_search is not written yet")


def greedy_best_first(
    network: RouteNetwork,
    start: str,
    goal: str,
    weights: CostWeights,
    blocked_nodes: set[str] | None = None,
    blocked_edges: set[str] | None = None,
) -> RouteResult:
    """Always expand the hub with the lowest heuristic value h(n), ignoring g(n).

    Usually expands few states, but can return a costlier route than Dijkstra.
    """
    raise NotImplementedError("Koushik: greedy_best_first is not written yet")


def weighted_a_star(
    network: RouteNetwork,
    start: str,
    goal: str,
    weights: CostWeights,
    epsilon: float = 1.5,
    blocked_nodes: set[str] | None = None,
    blocked_edges: set[str] | None = None,
) -> RouteResult:
    """A* with priority g(n) + epsilon * h(n).

    epsilon = 1 is ordinary A*. With an admissible heuristic, the route found
    costs at most epsilon times the optimal cost. Reject epsilon < 1.
    """
    raise NotImplementedError("Koushik: weighted_a_star is not written yet")

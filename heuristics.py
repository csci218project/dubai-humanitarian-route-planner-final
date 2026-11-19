"""Heuristics for A*, and checks that they are safe to use.

A heuristic h(n) estimates the score still to pay from hub n to the goal.
A* returns an optimal route if h is admissible (never above the true remaining
score), and expands each state at most once if h is also consistent
(h(u) <= score of leg u->v + h(v) for every leg, and h(goal) = 0).

- zero_heuristic: always 0, so A* behaves exactly like Dijkstra.
- distance_heuristic: the one algorithms.a_star uses: straight-line distance to
  the goal times the lowest score per kilometre on any open leg.
- time_lower_bound_heuristic: straight-line distance divided by the fastest
  straight-line speed of any open leg, times the time weight.
- max_heuristic: the larger of several admissible heuristics; still admissible.
- check_admissible and check_consistent: list where a heuristic breaks the rule.
- a_star_with and compare_heuristics: run A* with any heuristic and compare them.

Each builder takes the network, goal, weights and closures, and returns a
function from a hub ID to its estimate.
"""

from __future__ import annotations

import time
from typing import Callable

from .algorithms import _best_first_search, _heuristic_scale, _node_states, _result, _validate_request, dijkstra
from .models import CostWeights, RouteResult
from .network import RouteNetwork, haversine_km

Heuristic = Callable[[str], float]   # hub ID -> estimated remaining score


def zero_heuristic(network: RouteNetwork, goal: str, weights: CostWeights,
                   blocked_nodes: set[str] | None = None, blocked_edges: set[str] | None = None) -> Heuristic:
    """No estimate at all: A* with this heuristic is Dijkstra's algorithm."""
    return lambda node_id: 0.0


def distance_heuristic(network: RouteNetwork, goal: str, weights: CostWeights,
                       blocked_nodes: set[str] | None = None, blocked_edges: set[str] | None = None) -> Heuristic:
    """Straight-line distance times the lowest score per kilometre on any open leg.

    Why it never overestimates: every leg scores at least (that lowest rate) x
    (its own straight-line length), and the straight-line lengths along any
    route add up to at least the straight-line distance to the goal.
    """
    scale = _heuristic_scale(network, weights, set(blocked_nodes or ()), set(blocked_edges or ()))
    target = network.nodes[goal]
    return lambda node_id: scale * haversine_km(network.nodes[node_id], target)


def time_lower_bound_heuristic(network: RouteNetwork, goal: str, weights: CostWeights,
                               blocked_nodes: set[str] | None = None,
                               blocked_edges: set[str] | None = None) -> Heuristic:
    """Straight-line distance at the top speed any open leg manages, times the time weight.

    Why it never overestimates: every leg takes at least (its straight-line
    length / the top speed) hours, the lengths along a route add up to at least
    the distance to the goal, and cost, risk and transfers only add to the score.
    It ignores cost and risk, so it helps most when the time weight is large.
    """
    top_speed = 0.0
    for edge in network.active_edges(set(blocked_nodes or ()), set(blocked_edges or ())):
        length = haversine_km(network.nodes[edge.source], network.nodes[edge.target])
        if edge.time_hours <= 0:
            if length > 0:   # an instant leg gives no time bound at all
                return zero_heuristic(network, goal, weights)
            continue
        top_speed = max(top_speed, length / edge.time_hours)
    if top_speed <= 0 or weights.time == 0:
        return zero_heuristic(network, goal, weights)
    target = network.nodes[goal]
    return lambda node_id: weights.time * haversine_km(network.nodes[node_id], target) / top_speed


def max_heuristic(*heuristics: Heuristic) -> Heuristic:
    """The largest of several estimates. If each never overestimates, neither does their maximum."""
    return lambda node_id: max(h(node_id) for h in heuristics)


def true_remaining_scores(network: RouteNetwork, goal: str, weights: CostWeights,
                          blocked_nodes: set[str] | None = None,
                          blocked_edges: set[str] | None = None) -> dict[str, float]:
    """The optimal remaining score from every hub that can still reach the goal (Dijkstra from each hub).

    Starting a search at a hub charges no transfer before its first leg, which
    is the cheapest way to leave it, so this is the bound a heuristic must respect.
    """
    closed_hubs = set(blocked_nodes or ())
    scores = {goal: 0.0}
    for node_id in network.nodes:
        if node_id == goal or node_id in closed_hubs:
            continue
        result = dijkstra(network, node_id, goal, weights, closed_hubs, set(blocked_edges or ()))
        if result.success:
            scores[node_id] = result.objective_score
    return scores


def check_admissible(network: RouteNetwork, goal: str, weights: CostWeights, heuristic: Heuristic,
                     blocked_nodes: set[str] | None = None, blocked_edges: set[str] | None = None,
                     tolerance: float = 1e-9) -> list[str]:
    """Hubs where the heuristic is above the true remaining score. An empty list means admissible."""
    remaining = true_remaining_scores(network, goal, weights, blocked_nodes, blocked_edges)
    return [node_id for node_id, score in remaining.items() if heuristic(node_id) > score + tolerance]


def check_consistent(network: RouteNetwork, goal: str, weights: CostWeights, heuristic: Heuristic,
                     blocked_nodes: set[str] | None = None, blocked_edges: set[str] | None = None,
                     tolerance: float = 1e-9) -> list[str]:
    """Places where h(u) > score of leg u->v + h(v), plus the goal if h(goal) isn't 0.

    An empty list means consistent. Transfers only add to a step's score, so
    checking the legs on their own is enough.
    """
    problems = [goal] if heuristic(goal) > tolerance else []
    for edge in network.active_edges(set(blocked_nodes or ()), set(blocked_edges or ())):
        directions = [(edge.source, edge.target)]
        if not network.directed:
            directions.append((edge.target, edge.source))
        step = weights.edge_cost(edge)
        if any(heuristic(u) > step + heuristic(v) + tolerance for u, v in directions):
            problems.append(edge.edge_id)
    return problems


def a_star_with(network: RouteNetwork, start: str, goal: str, weights: CostWeights, heuristic: Heuristic,
                name: str = "A* (custom heuristic)", blocked_nodes: set[str] | None = None,
                blocked_edges: set[str] | None = None) -> RouteResult:
    """A* using any heuristic, with the same search engine, transfers and closures as algorithms.a_star."""
    started = time.perf_counter()
    disabled_nodes, disabled_edges, error = _validate_request(
        network, start, goal, weights, blocked_nodes, blocked_edges
    )
    if error:
        return _result(network, name, False, None, [], None, 0, started, weights, error)
    start_state, is_goal, transitions, node_of = _node_states(
        network, start, goal, weights, disabled_nodes, disabled_edges
    )
    path, legs, score, expanded = _best_first_search(
        start_state=start_state,
        is_goal=is_goal,
        transitions=transitions,
        state_node_id=node_of,
        heuristic=lambda state: heuristic(node_of(state)),
        algorithm_name=name,
    )
    success = path is not None
    message = "Route found." if success else "No feasible route exists under the selected disruptions."
    return _result(network, name, success, path, legs, score, expanded, started, weights, message)


def compare_heuristics(network: RouteNetwork, start: str, goal: str, weights: CostWeights,
                       blocked_nodes: set[str] | None = None,
                       blocked_edges: set[str] | None = None) -> list[dict]:
    """Run A* with each heuristic and report score, states expanded and both checks."""
    built = {
        "Zero (Dijkstra)": zero_heuristic(network, goal, weights, blocked_nodes, blocked_edges),
        "Distance (used by A*)": distance_heuristic(network, goal, weights, blocked_nodes, blocked_edges),
        "Time lower bound": time_lower_bound_heuristic(network, goal, weights, blocked_nodes, blocked_edges),
    }
    built["Max of distance and time"] = max_heuristic(built["Distance (used by A*)"], built["Time lower bound"])
    rows = []
    for name, heuristic in built.items():
        result = a_star_with(network, start, goal, weights, heuristic, name, blocked_nodes, blocked_edges)
        rows.append({
            "heuristic": name,
            "success": result.success,
            "objective_score": result.objective_score,
            "nodes_expanded": result.nodes_expanded,
            "estimate_at_start": heuristic(start),
            "admissible": not check_admissible(network, goal, weights, heuristic, blocked_nodes, blocked_edges),
            "consistent": not check_consistent(network, goal, weights, heuristic, blocked_nodes, blocked_edges),
        })
    return rows

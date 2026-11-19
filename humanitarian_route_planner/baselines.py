"""Baseline searches to compare with Dijkstra and A*.

- breadth_first_search: the route with the fewest legs, ignoring time, cost and risk.
- greedy_best_first: always expands the hub closest to the goal in a straight line;
  quick, but it ignores the score already paid, so its route can be worse than optimal.
- weighted_a_star: A* with f = g + epsilon * h; its route scores at most epsilon times
  the optimal score.

Each takes the same arguments as dijkstra() (weighted A* adds epsilon) and returns a
RouteResult, so routes, totals, transfers and states expanded compare directly.
"""

from __future__ import annotations

import heapq
import itertools
import time
from collections import deque

from .algorithms import _best_first_search, _heuristic_scale, _node_states, _result, _validate_request
from .models import CostWeights, Edge, RouteResult
from .network import RouteNetwork, haversine_km

NO_ROUTE = "No feasible route exists under the selected disruptions."


def _hubs_along(states: list, node_of) -> list[str]:
    """Hub IDs along a list of search states, without repeats from mode-only changes."""
    path: list[str] = []
    for state in states:
        node_id = node_of(state)
        if not path or path[-1] != node_id:
            path.append(node_id)
    return path


def breadth_first_search(
    network: RouteNetwork,
    start: str,
    goal: str,
    weights: CostWeights,
    blocked_nodes: set[str] | None = None,
    blocked_edges: set[str] | None = None,
) -> RouteResult:
    """Find the route with the fewest legs.

    BFS explores hubs in rings: every hub one leg away, then two legs away, and
    so on, so the first time it reaches the goal it has used the fewest legs.
    Time, cost and risk play no part in the choice; the result still reports
    them (transfers included) so the route can be compared with the others.
    """
    name = "BFS (fewest legs)"
    started = time.perf_counter()
    disabled_nodes, disabled_edges, error = _validate_request(
        network, start, goal, weights, blocked_nodes, blocked_edges
    )
    if error:
        return _result(network, name, False, None, [], None, 0, started, weights, error)

    queue = deque([start])
    parent: dict[str, tuple[str, Edge]] = {}
    seen = {start}
    expanded = 0
    while queue:
        node_id = queue.popleft()
        expanded += 1
        if node_id == goal:
            break
        for neighbor, edge in network.neighbors(node_id, disabled_nodes, disabled_edges):
            if neighbor not in seen:
                seen.add(neighbor)
                parent[neighbor] = (node_id, edge)
                queue.append(neighbor)

    if goal not in seen:
        return _result(network, name, False, None, [], None, expanded, started, weights, NO_ROUTE)
    hubs, legs = [goal], []
    while hubs[-1] != start:
        previous, edge = parent[hubs[-1]]
        legs.append(edge)
        hubs.append(previous)
    hubs.reverse()
    legs.reverse()
    return _result(network, name, True, hubs, legs, None, expanded, started, weights,
                   "Route with the fewest legs; time, cost and risk were not considered.")


def greedy_best_first(
    network: RouteNetwork,
    start: str,
    goal: str,
    weights: CostWeights,
    blocked_nodes: set[str] | None = None,
    blocked_edges: set[str] | None = None,
) -> RouteResult:
    """Always expand the state whose hub is closest to the goal in a straight line.

    It orders the frontier by h alone (distance to the goal) and never looks at
    the score already paid, so it can commit to a route that looks direct but
    costs more. Transfers still count in the reported totals.
    """
    name = "Greedy best-first"
    started = time.perf_counter()
    disabled_nodes, disabled_edges, error = _validate_request(
        network, start, goal, weights, blocked_nodes, blocked_edges
    )
    if error:
        return _result(network, name, False, None, [], None, 0, started, weights, error)

    start_state, is_goal, transitions, node_of = _node_states(
        network, start, goal, weights, disabled_nodes, disabled_edges
    )
    target = network.nodes[goal]

    def distance_left(state) -> float:
        return haversine_km(network.nodes[node_of(state)], target)

    counter = itertools.count()
    frontier = [(distance_left(start_state), next(counter), start_state)]
    parent: dict = {}
    seen = {start_state}
    expanded = 0
    goal_state = None
    while frontier:
        _, _, state = heapq.heappop(frontier)
        expanded += 1
        if is_goal(state):
            goal_state = state
            break
        for transition in transitions(state):
            if transition.target not in seen:
                seen.add(transition.target)
                parent[transition.target] = (state, transition)
                heapq.heappush(frontier, (distance_left(transition.target), next(counter), transition.target))

    if goal_state is None:
        return _result(network, name, False, None, [], None, expanded, started, weights, NO_ROUTE)
    states, legs = [goal_state], []
    while states[-1] != start_state:
        previous, transition = parent[states[-1]]
        legs.append(transition.edge)
        states.append(previous)
    states.reverse()
    legs.reverse()
    return _result(network, name, True, _hubs_along(states, node_of), legs, None, expanded, started, weights,
                   "Route found by greedy best-first search; it is not guaranteed to be optimal.")


def weighted_a_star(
    network: RouteNetwork,
    start: str,
    goal: str,
    weights: CostWeights,
    epsilon: float = 1.5,
    blocked_nodes: set[str] | None = None,
    blocked_edges: set[str] | None = None,
) -> RouteResult:
    """A* with f = g + epsilon * h, for epsilon >= 1.

    A larger epsilon trusts the heuristic more, so the search heads for the goal
    sooner and usually expands fewer states, but the route can cost more. The
    heuristic is the one A* uses, which is consistent, so the route scores at
    most epsilon times the optimal score (epsilon = 1 is plain A*).
    """
    if epsilon < 1:
        raise ValueError("epsilon must be at least 1.")
    name = f"Weighted A* (ε={epsilon:g})"
    started = time.perf_counter()
    disabled_nodes, disabled_edges, error = _validate_request(
        network, start, goal, weights, blocked_nodes, blocked_edges
    )
    if error:
        return _result(network, name, False, None, [], None, 0, started, weights, error)

    scale = _heuristic_scale(network, weights, disabled_nodes, disabled_edges)
    start_state, is_goal, transitions, node_of = _node_states(
        network, start, goal, weights, disabled_nodes, disabled_edges
    )
    target = network.nodes[goal]

    def inflated(state) -> float:
        return epsilon * scale * haversine_km(network.nodes[node_of(state)], target)

    path, legs, score, expanded = _best_first_search(
        start_state=start_state,
        is_goal=is_goal,
        transitions=transitions,
        state_node_id=node_of,
        heuristic=inflated,
        algorithm_name=name,
    )
    success = path is not None
    message = f"Route within {epsilon:g} times the optimal score." if success else NO_ROUTE
    return _result(network, name, success, path, legs, score, expanded, started, weights, message)


def compare_baselines(
    network: RouteNetwork,
    start: str,
    goal: str,
    weights: CostWeights,
    blocked_nodes: set[str] | None = None,
    blocked_edges: set[str] | None = None,
    epsilon: float = 1.5,
) -> list[RouteResult]:
    """Run the three baselines with identical settings."""
    return [
        breadth_first_search(network, start, goal, weights, blocked_nodes, blocked_edges),
        greedy_best_first(network, start, goal, weights, blocked_nodes, blocked_edges),
        weighted_a_star(network, start, goal, weights, epsilon, blocked_nodes, blocked_edges),
    ]

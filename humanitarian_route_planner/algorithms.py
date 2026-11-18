"""Dijkstra, A*, and two-level hierarchical search."""

from __future__ import annotations

import heapq
import itertools
import time
from dataclasses import dataclass
from typing import Callable, Hashable, Iterable

from .models import CostWeights, Edge, RouteResult
from .network import RouteNetwork, haversine_km, mode_key


@dataclass(frozen=True)
class Transition:
    target: Hashable
    cost: float
    edge: Edge | None = None


def _heuristic_scale(
    network: RouteNetwork,
    weights: CostWeights,
    blocked_nodes: set[str],
    blocked_edges: set[str],
) -> float:
    """Find an admissible generalized-score lower bound per kilometre.

    The heuristic uses straight-line distance multiplied by the smallest
    active edge-score / estimated-edge-distance ratio. Because each teaching
    edge's estimated distance is at least the straight-line distance between
    its endpoints, the estimate cannot exceed a route's generalized score.
    """
    ratios: list[float] = []
    for edge in network.active_edges(blocked_nodes, blocked_edges):
        distance = network.edge_distance_km(edge)
        ratios.append(weights.edge_cost(edge) / distance)
    return min(ratios) if ratios else 0.0


def _node_states(
    network: RouteNetwork,
    start: str,
    goal: str,
    weights: CostWeights,
    disabled_nodes: set[str],
    disabled_edges: set[str],
):
    """Search states for Dijkstra and A*: the hub alone, or (hub, mode arrived on).

    The pair is needed when the network charges transfers: whether the next leg
    costs a transfer depends on how the cargo reached the hub. Returns the start
    state, the goal test, the transitions and a function from a state to its hub.
    """
    if network.transfer is None:
        def transitions(node_id: str) -> Iterable[Transition]:
            for neighbor, edge in network.neighbors(node_id, disabled_nodes, disabled_edges):
                yield Transition(neighbor, weights.edge_cost(edge), edge)

        return start, (lambda state: state == goal), transitions, (lambda state: str(state))

    def mode_transitions(state: tuple[str, str | None]) -> Iterable[Transition]:
        node_id, arrived = state
        for neighbor, edge in network.neighbors(node_id, disabled_nodes, disabled_edges):
            cost = weights.edge_cost(edge) + network.transfer_cost(arrived, edge.mode, weights)
            yield Transition((neighbor, mode_key(edge.mode)), cost, edge)

    return (start, None), (lambda state: state[0] == goal), mode_transitions, (lambda state: str(state[0]))


def _best_first_search(
    *,
    start_state: Hashable,
    is_goal: Callable[[Hashable], bool],
    transitions: Callable[[Hashable], Iterable[Transition]],
    state_node_id: Callable[[Hashable], str],
    heuristic: Callable[[Hashable], float],
    algorithm_name: str,
) -> tuple[list[str] | None, list[Edge], float | None, int]:
    """Shared best-first engine; heuristic=0 gives Dijkstra's algorithm."""
    counter = itertools.count()
    frontier: list[tuple[float, int, float, Hashable]] = []
    heapq.heappush(frontier, (heuristic(start_state), next(counter), 0.0, start_state))
    best_g: dict[Hashable, float] = {start_state: 0.0}
    parent: dict[Hashable, tuple[Hashable, Transition]] = {}
    closed: set[Hashable] = set()
    expanded = 0
    goal_state: Hashable | None = None

    while frontier:
        _, _, current_g, current = heapq.heappop(frontier)
        if current_g > best_g.get(current, float("inf")) + 1e-12:
            continue
        if current in closed:
            continue
        closed.add(current)
        expanded += 1

        if is_goal(current):
            goal_state = current
            break

        for transition in transitions(current):
            next_state = transition.target
            candidate = current_g + transition.cost
            if candidate + 1e-12 < best_g.get(next_state, float("inf")):
                best_g[next_state] = candidate
                parent[next_state] = (current, transition)
                priority = candidate + heuristic(next_state)
                heapq.heappush(frontier, (priority, next(counter), candidate, next_state))

    if goal_state is None:
        return None, [], None, expanded

    states: list[Hashable] = [goal_state]
    path_edges: list[Edge] = []
    cursor = goal_state
    while cursor != start_state:
        previous, transition = parent[cursor]
        if transition.edge is not None:
            path_edges.append(transition.edge)
        states.append(previous)
        cursor = previous
    states.reverse()
    path_edges.reverse()
    node_path: list[str] = []
    for state in states:
        node_id = state_node_id(state)
        if not node_path or node_path[-1] != node_id:
            node_path.append(node_id)
    return node_path, path_edges, best_g[goal_state], expanded


def _result(
    network: RouteNetwork,
    algorithm: str,
    success: bool,
    node_path: list[str] | None,
    path_edges: list[Edge],
    score: float | None,
    expanded: int,
    started: float,
    weights: CostWeights,
    message: str,
    abstract_regions: list[str] | None = None,
) -> RouteResult:
    runtime_ms = (time.perf_counter() - started) * 1000.0
    if not success or node_path is None:
        return RouteResult(
            algorithm=algorithm,
            success=False,
            nodes_expanded=expanded,
            runtime_ms=runtime_ms,
            message=message,
            abstract_regions=abstract_regions or [],
        )
    edge_ids = [edge.edge_id for edge in path_edges]
    totals = network.route_totals(edge_ids, weights)
    return RouteResult(
        algorithm=algorithm,
        success=True,
        node_path=node_path,
        edge_path=edge_ids,
        objective_score=float(totals["objective_score"] or 0.0),
        total_time_hours=float(totals["total_time_hours"] or 0.0),
        total_cost_usd=float(totals["total_cost_usd"] or 0.0),
        total_risk_points=float(totals["total_risk_points"] or 0.0),
        minimum_capacity_tonnes=totals["minimum_capacity_tonnes"],
        nodes_expanded=expanded,
        runtime_ms=runtime_ms,
        abstract_regions=abstract_regions or [],
        message=message,
        transfers=int(totals["transfers"] or 0),
        total_time_p90_hours=totals["total_time_p90_hours"],
        reliability_pct=totals["reliability_pct"],
    )


def _validate_request(
    network: RouteNetwork,
    start: str,
    goal: str,
    weights: CostWeights,
    blocked_nodes: set[str] | None,
    blocked_edges: set[str] | None,
) -> tuple[set[str], set[str], str | None]:
    weights.validate()
    disabled_nodes = set(blocked_nodes or set())
    disabled_edges = set(blocked_edges or set())
    unknown_nodes = disabled_nodes - set(network.nodes)
    unknown_edges = disabled_edges - set(network.edges)
    if unknown_nodes:
        return disabled_nodes, disabled_edges, f"Unknown blocked node IDs: {sorted(unknown_nodes)}"
    if unknown_edges:
        return disabled_nodes, disabled_edges, f"Unknown blocked edge IDs: {sorted(unknown_edges)}"
    if start not in network.nodes or goal not in network.nodes:
        return disabled_nodes, disabled_edges, "Start or destination is not present in the network."
    if start in disabled_nodes:
        return disabled_nodes, disabled_edges, "The selected origin is marked unavailable."
    if goal in disabled_nodes:
        return disabled_nodes, disabled_edges, "The selected destination is marked unavailable."
    return disabled_nodes, disabled_edges, None


def dijkstra(
    network: RouteNetwork,
    start: str,
    goal: str,
    weights: CostWeights,
    blocked_nodes: set[str] | None = None,
    blocked_edges: set[str] | None = None,
) -> RouteResult:
    """Find the minimum generalized-cost path using Dijkstra's algorithm."""
    started = time.perf_counter()
    disabled_nodes, disabled_edges, error = _validate_request(
        network, start, goal, weights, blocked_nodes, blocked_edges
    )
    if error:
        return _result(network, "Dijkstra", False, None, [], None, 0, started, weights, error)

    start_state, is_goal, transitions, node_of = _node_states(
        network, start, goal, weights, disabled_nodes, disabled_edges
    )
    path, edges, score, expanded = _best_first_search(
        start_state=start_state,
        is_goal=is_goal,
        transitions=transitions,
        state_node_id=node_of,
        heuristic=lambda _state: 0.0,
        algorithm_name="Dijkstra",
    )
    success = path is not None
    message = "Optimal route found." if success else "No feasible route exists under the selected disruptions."
    return _result(network, "Dijkstra", success, path, edges, score, expanded, started, weights, message)


def a_star(
    network: RouteNetwork,
    start: str,
    goal: str,
    weights: CostWeights,
    blocked_nodes: set[str] | None = None,
    blocked_edges: set[str] | None = None,
) -> RouteResult:
    """Find a minimum generalized-cost path using A* with an admissible heuristic."""
    started = time.perf_counter()
    disabled_nodes, disabled_edges, error = _validate_request(
        network, start, goal, weights, blocked_nodes, blocked_edges
    )
    if error:
        return _result(network, "A*", False, None, [], None, 0, started, weights, error)

    scale = _heuristic_scale(network, weights, disabled_nodes, disabled_edges)
    start_state, is_goal, transitions, node_of = _node_states(
        network, start, goal, weights, disabled_nodes, disabled_edges
    )

    def heuristic(state) -> float:
        # Transfers only add cost, so the distance bound stays admissible.
        return scale * haversine_km(network.nodes[node_of(state)], network.nodes[goal])

    path, edges, score, expanded = _best_first_search(
        start_state=start_state,
        is_goal=is_goal,
        transitions=transitions,
        state_node_id=node_of,
        heuristic=heuristic,
        algorithm_name="A*",
    )
    success = path is not None
    message = "Optimal route found with an admissible distance heuristic." if success else (
        "No feasible route exists under the selected disruptions."
    )
    return _result(network, "A*", success, path, edges, score, expanded, started, weights, message)


def _region_path(
    network: RouteNetwork,
    start_region: str,
    goal_region: str,
    weights: CostWeights,
    active_edges: list[Edge],
) -> tuple[list[str] | None, int]:
    """Search an abstract graph whose nodes represent logistics regions."""
    abstract_edges: dict[tuple[str, str], float] = {}
    for edge in active_edges:
        region_a = network.nodes[edge.source].region
        region_b = network.nodes[edge.target].region
        if region_a == region_b:
            continue
        pair = (region_a, region_b)
        cost = weights.edge_cost(edge)
        abstract_edges[pair] = min(cost, abstract_edges.get(pair, float("inf")))
        if not network.directed:
            reverse_pair = (region_b, region_a)
            abstract_edges[reverse_pair] = min(cost, abstract_edges.get(reverse_pair, float("inf")))

    abstract_adj: dict[str, dict[str, float]] = {}
    for (region_a, region_b), cost in abstract_edges.items():
        abstract_adj.setdefault(region_a, {})[region_b] = cost
    if start_region not in abstract_adj and start_region != goal_region:
        return None, 0

    queue: list[tuple[float, int, str]] = []
    count = itertools.count()
    heapq.heappush(queue, (0.0, next(count), start_region))
    distances = {start_region: 0.0}
    parents: dict[str, str] = {}
    expanded = 0
    while queue:
        distance, _, current = heapq.heappop(queue)
        if distance > distances.get(current, float("inf")) + 1e-12:
            continue
        expanded += 1
        if current == goal_region:
            break
        for neighbor, edge_cost in abstract_adj.get(current, {}).items():
            candidate = distance + edge_cost
            if candidate + 1e-12 < distances.get(neighbor, float("inf")):
                distances[neighbor] = candidate
                parents[neighbor] = current
                heapq.heappush(queue, (candidate, next(count), neighbor))
    if goal_region not in distances:
        return None, expanded
    path = [goal_region]
    while path[-1] != start_region:
        path.append(parents[path[-1]])
    path.reverse()
    return path, expanded


def hierarchical_search(
    network: RouteNetwork,
    start: str,
    goal: str,
    weights: CostWeights,
    blocked_nodes: set[str] | None = None,
    blocked_edges: set[str] | None = None,
) -> RouteResult:
    """Perform region-level planning followed by detailed route search.

    Tier 1 uses a graph of broad regions (UAE, regional hubs, staging areas,
    etc.) to choose a region sequence. Tier 2 searches the original network,
    constrained to move within a region or to the next region in that sequence.
    This demonstrates multi-layered search; it is not guaranteed to match the
    globally optimal flat path because the abstraction can discard alternatives.
    """
    started = time.perf_counter()
    disabled_nodes, disabled_edges, error = _validate_request(
        network, start, goal, weights, blocked_nodes, blocked_edges
    )
    if error:
        return _result(network, "Hierarchical", False, None, [], None, 0, started, weights, error)

    start_region = network.nodes[start].region
    goal_region = network.nodes[goal].region
    abstract_regions, abstract_expanded = _region_path(
        network,
        start_region,
        goal_region,
        weights,
        network.active_edges(disabled_nodes, disabled_edges),
    )
    if abstract_regions is None:
        return _result(
            network, "Hierarchical", False, None, [], None, abstract_expanded,
            started, weights, "No abstract region route exists under the selected disruptions."
        )

    region_index = {region: i for i, region in enumerate(abstract_regions)}
    scale = _heuristic_scale(network, weights, disabled_nodes, disabled_edges)
    use_modes = network.transfer is not None   # then states also carry the mode arrived on
    start_state = (start, 0, None) if use_modes else (start, 0)
    goal_index = len(abstract_regions) - 1

    def transitions(state: tuple) -> Iterable[Transition]:
        node_id, index = state[0], state[1]
        arrived = state[2] if use_modes else None
        current_region = abstract_regions[index]
        for neighbor, edge in network.neighbors(node_id, disabled_nodes, disabled_edges):
            neighbor_region = network.nodes[neighbor].region
            if neighbor_region == current_region:
                next_index = index
            elif index + 1 < len(abstract_regions) and neighbor_region == abstract_regions[index + 1]:
                next_index = index + 1
            else:
                continue
            cost = weights.edge_cost(edge) + network.transfer_cost(arrived, edge.mode, weights)
            target = (neighbor, next_index, mode_key(edge.mode)) if use_modes else (neighbor, next_index)
            yield Transition(target, cost, edge)

    def heuristic(state: tuple) -> float:
        return scale * haversine_km(network.nodes[state[0]], network.nodes[goal])

    path, edges, score, detailed_expanded = _best_first_search(
        start_state=start_state,
        is_goal=lambda state: state[0] == goal and state[1] == goal_index,
        transitions=transitions,
        state_node_id=lambda state: str(state[0]),
        heuristic=heuristic,
        algorithm_name="Hierarchical",
    )
    success = path is not None
    message = (
        "Hierarchical route found; optimality is relative to the selected region sequence."
        if success else
        "The abstract region sequence could not be realized in the detailed network."
    )
    return _result(
        network, "Hierarchical", success, path, edges, score,
        abstract_expanded + detailed_expanded, started, weights, message, abstract_regions
    )


def compare_algorithms(
    network: RouteNetwork,
    start: str,
    goal: str,
    weights: CostWeights,
    blocked_nodes: set[str] | None = None,
    blocked_edges: set[str] | None = None,
) -> list[RouteResult]:
    """Run all three algorithms with identical scenario settings."""
    return [
        dijkstra(network, start, goal, weights, blocked_nodes, blocked_edges),
        a_star(network, start, goal, weights, blocked_nodes, blocked_edges),
        hierarchical_search(network, start, goal, weights, blocked_nodes, blocked_edges),
    ]

"""Seeded random networks, for experiments the 10-hub sample is too small for.

Owner: Shreya.
"""

from __future__ import annotations

from humanitarian_route_planner.network import RouteNetwork


def generate_network(n_nodes: int, seed: int, extra_links_per_node: int = 2) -> RouteNetwork:
    """Return a connected network of n_nodes hubs with coordinates and air, sea and road links.

    The same seed must always give the same network: use random.Random(seed),
    never the global random module. One approach: scatter hubs at random
    coordinates in a box, link each hub to its nearest neighbours by road, add a
    few long air links, set time, cost and risk with simple per-mode rules, then
    make sure every hub is reachable. Build ``Node`` and ``Edge`` objects
    (models.py) and pass them to ``RouteNetwork(nodes, edges, metadata)``.
    """
    raise NotImplementedError("Shreya: generate_network is not written yet")

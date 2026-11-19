"""Seeded random networks for scaling experiments.

generate_network(n_hubs, seed) builds a connected multimodal network in the same
format as the Dubai Humanitarian data, so every algorithm runs on it unchanged:

- hubs scattered over a box from Sudan to the Gulf, about 15% airports and 10% sea ports;
- road links from every hub to its nearest neighbours, plus links that keep the network connected;
- air links between nearby airports and sea links between nearby ports;
- time, cost per tonne, risk, capacity, slow-case time and reliability from simple
  per-mode rules, roughly on the scale of the real data;
- links run both ways, and the data's transfer rule (3.5 h, $18/t, risk 1) applies
  where cargo changes mode.

The same seed always gives the same network. The values are made up, for
measuring the algorithms only.
"""

from __future__ import annotations

import random

import numpy as np

from .models import Edge, Node
from .network import RouteNetwork, haversine_km

LAT_RANGE = (5.0, 30.0)           # roughly Sudan to the Gulf
LON_RANGE = (25.0, 60.0)
ORIGIN_NEAR = (25.2, 55.3)        # the origin is the hub nearest Dubai
DESTINATION_NEAR = (13.2, 30.2)   # the destination is the hub nearest El Obeid
EARTH_RADIUS_KM = 6371.0088

# Per mode: route length / straight line, speed (km/h), fixed hours, USD per tonne-km,
# fixed USD per tonne, risk range (1-5) and capacity range (tonnes per week).
MODE_RULES = {
    "road": {"factor": 1.18, "speed": 45.0, "fixed_h": 2.0, "per_km": 0.40, "fixed_usd": 20.0,
             "risk": (1, 5), "capacity": (200, 800)},
    "air": {"factor": 1.05, "speed": 750.0, "fixed_h": 8.0, "per_km": 0.90, "fixed_usd": 300.0,
            "risk": (1, 3), "capacity": (20, 150)},
    "sea": {"factor": 1.25, "speed": 28.0, "fixed_h": 48.0, "per_km": 0.07, "fixed_usd": 50.0,
            "risk": (1, 4), "capacity": (1000, 5000)},
}
TRANSFER = {"time_hours": 3.5, "cost_usd": 18.0, "risk_score": 1.0,
            "basis": "Same as the Dubai Humanitarian data (median transfer leg)"}


def _distances_km(lats: np.ndarray, lons: np.ndarray, i: int, others: np.ndarray) -> np.ndarray:
    """Great-circle distances from hub i to each hub in `others` (inputs in radians)."""
    dlat = lats[others] - lats[i]
    dlon = lons[others] - lons[i]
    h = np.sin(dlat / 2) ** 2 + np.cos(lats[i]) * np.cos(lats[others]) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.minimum(1.0, np.sqrt(h)))


def _nearest(lats: np.ndarray, lons: np.ndarray, i: int, candidates: np.ndarray, k: int) -> list[int]:
    """Up to k nearest candidates to hub i, nearest first (hub i itself excluded)."""
    candidates = candidates[candidates != i]
    if candidates.size == 0:
        return []
    distances = _distances_km(lats, lons, i, candidates)
    k = min(k, candidates.size)
    picked = np.argpartition(distances, k - 1)[:k]
    return [int(candidates[j]) for j in picked[np.argsort(distances[picked])]]


def generate_network(
    n_hubs: int,
    seed: int,
    road_neighbours: int = 3,
    airport_share: float = 0.15,
    port_share: float = 0.10,
    transfer: bool = True,
) -> RouteNetwork:
    """Build a connected random network with n_hubs hubs; the same seed gives the same network."""
    if n_hubs < 2:
        raise ValueError("A network needs at least two hubs.")
    rng = random.Random(seed)

    nodes: list[Node] = []
    for index in range(n_hubs):
        lat, lon = rng.uniform(*LAT_RANGE), rng.uniform(*LON_RANGE)
        roll = rng.random()
        node_type = "airport" if roll < airport_share else "port" if roll < airport_share + port_share else "hub"
        row = min(3, int((lat - LAT_RANGE[0]) / (LAT_RANGE[1] - LAT_RANGE[0]) * 4))
        col = min(3, int((lon - LON_RANGE[0]) / (LON_RANGE[1] - LON_RANGE[0]) * 4))
        nodes.append(Node(
            node_id=f"H{index:05d}", name=f"Hub {index}", latitude=round(lat, 4), longitude=round(lon, 4),
            region=f"R{row}{col}",   # a 4 x 4 grid of regions, for hierarchical search
            node_type=node_type,
        ))
    lats = np.radians([node.latitude for node in nodes])
    lons = np.radians([node.longitude for node in nodes])
    everyone = np.arange(n_hubs)

    edges: list[Edge] = []
    linked: set[tuple[int, int, str]] = set()

    def link(a: int, b: int, mode: str) -> None:
        key = (min(a, b), max(a, b), mode)
        if a == b or key in linked:
            return
        linked.add(key)
        rule = MODE_RULES[mode]
        length = haversine_km(nodes[a], nodes[b]) * rule["factor"]
        hours = round(length / rule["speed"] + rule["fixed_h"], 2)
        edges.append(Edge(
            edge_id=f"E{len(edges):06d}", source=nodes[a].node_id, target=nodes[b].node_id, mode=mode,
            time_hours=hours,
            cost_usd=round(length * rule["per_km"] + rule["fixed_usd"], 2),
            risk_score=float(rng.randint(*rule["risk"])),
            capacity_tonnes=float(rng.randint(*rule["capacity"])),
            time_hours_p90=max(hours, round(hours * rng.uniform(1.1, 1.6), 2)),
            reliability_pct=round(rng.uniform(55.0, 98.0), 1),
            distance_km=round(length, 1),
            corridor="Synthetic",
        ))

    for index in range(1, n_hubs):   # each hub joins its nearest earlier hub: the network stays connected
        link(index, _nearest(lats, lons, index, everyone[:index], 1)[0], "road")
    for index in range(n_hubs):
        for other in _nearest(lats, lons, index, everyone, road_neighbours):
            link(index, other, "road")
    for mode, share_type, neighbours in (("air", "airport", 3), ("sea", "port", 2)):
        members = np.array([i for i, node in enumerate(nodes) if node.node_type == share_type])
        for index in members:
            for other in _nearest(lats, lons, int(index), members, neighbours):
                link(int(index), other, mode)

    def nearest_to(point: tuple[float, float]) -> int:
        probe = Node("probe", "probe", point[0], point[1], "", "hub")
        return min(range(n_hubs), key=lambda i: haversine_km(nodes[i], probe))

    origin = nearest_to(ORIGIN_NEAR)
    destination = nearest_to(DESTINATION_NEAR)
    if destination == origin:
        destination = max(range(n_hubs), key=lambda i: haversine_km(nodes[i], nodes[origin]))
    for index, role in ((origin, "origin"), (destination, "destination")):
        nodes[index] = Node(**{**nodes[index].__dict__, "node_type": role})

    metadata = {
        "title": f"Synthetic network ({n_hubs} hubs, seed {seed})",
        "directed": False,
        "default_origin": nodes[origin].node_id,
        "default_destination": nodes[destination].node_id,
        "cost_unit": "USD per tonne",
        "capacity_unit": "tonnes per week",
        "risk_scale": "1 (low) to 5 (high), ordinal",
        "data_status": "Synthetic network for scaling experiments.",
        "seed": seed,
    }
    if transfer:
        metadata["transfer"] = dict(TRANSFER)
    return RouteNetwork(nodes, edges, metadata)

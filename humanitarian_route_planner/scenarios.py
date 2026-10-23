"""Illustrative preconfigured disruption scenarios."""

from __future__ import annotations

SCENARIOS: dict[str, dict[str, set[str] | str]] = {
    "Baseline (no closures)": {
        "blocked_nodes": set(),
        "blocked_edges": set(),
        "description": "All illustrative hubs and links are available.",
    },
    "Airport disruption": {
        "blocked_nodes": {"DWC_AIRPORT"},
        "blocked_edges": set(),
        "description": "Al Maktoum Airport is unavailable; the algorithms must consider other options.",
    },
    "Port disruption": {
        "blocked_nodes": {"JEBEL_ALI_PORT"},
        "blocked_edges": set(),
        "description": "Jebel Ali Port is unavailable; sea connections through that node cannot be used.",
    },
    "Destination corridor disruption": {
        "blocked_nodes": set(),
        "blocked_edges": {"E14_ELARISH_DESTINATION"},
        "description": "The illustrative El Arish-to-destination corridor is unavailable.",
    },
    "Compound disruption": {
        "blocked_nodes": {"DWC_AIRPORT", "JEBEL_ALI_PORT"},
        "blocked_edges": {"E14_ELARISH_DESTINATION"},
        "description": "Airport, port, and one destination corridor are unavailable at the same time.",
    },
}

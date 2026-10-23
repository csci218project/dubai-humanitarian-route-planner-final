"""Graph visualization helpers for the Streamlit front end."""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import networkx as nx

from .network import RouteNetwork


MODE_COLORS = {
    "air": "#2563eb",
    "sea": "#0f766e",
    "road": "#64748b",
    "land convoy": "#b45309",
    "sea + road": "#7c3aed",
    "multimodal": "#7c3aed",
}


def draw_network(
    network: RouteNetwork,
    selected_path: list[str] | None = None,
    blocked_nodes: set[str] | None = None,
    blocked_edges: set[str] | None = None,
):
    """Draw a schematic network with a highlighted route and closures."""
    selected_path = selected_path or []
    blocked_nodes = blocked_nodes or set()
    blocked_edges = blocked_edges or set()
    graph = nx.Graph()
    for node_id, node in network.nodes.items():
        graph.add_node(node_id, label=node.name, pos=(node.longitude, node.latitude))
    for edge in network.edges.values():
        graph.add_edge(edge.source, edge.target, edge_id=edge.edge_id, mode=edge.mode)

    # Use a deterministic topology layout, rather than plotting labels at raw
    # longitude/latitude, so nearby logistics nodes remain readable. Geography
    # is deliberately not implied by the drawn line lengths or angles.
    positions = nx.spring_layout(graph, seed=218, k=1.25, iterations=120)
    fig, ax = plt.subplots(figsize=(12, 7.5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#f8fafc")

    normal_edges = []
    highlighted_edges = []
    closed_edges = []
    path_pairs = {frozenset((a, b)) for a, b in zip(selected_path, selected_path[1:])}
    for edge in network.edges.values():
        pair = (edge.source, edge.target)
        if edge.edge_id in blocked_edges or edge.source in blocked_nodes or edge.target in blocked_nodes:
            closed_edges.append(pair)
        elif frozenset(pair) in path_pairs:
            highlighted_edges.append(pair)
        else:
            normal_edges.append(pair)

    # Colour ordinary edges by transport mode so users can visually distinguish
    # modes. The highlighted route and closures take priority over mode colours.
    normal_edge_ids = {
        edge.edge_id for edge in network.edges.values()
        if (edge.source, edge.target) in normal_edges or (edge.target, edge.source) in normal_edges
    }
    for mode, color in MODE_COLORS.items():
        mode_edges = [
            (edge.source, edge.target) for edge in network.edges.values()
            if edge.edge_id in normal_edge_ids and edge.mode.lower() == mode
        ]
        if mode_edges:
            nx.draw_networkx_edges(graph, positions, edgelist=mode_edges, edge_color=color, width=1.8, alpha=0.88, ax=ax)
    nx.draw_networkx_edges(graph, positions, edgelist=closed_edges, edge_color="#dc2626", width=2.0, style="dashed", alpha=0.8, ax=ax)
    nx.draw_networkx_edges(graph, positions, edgelist=highlighted_edges, edge_color="#16a34a", width=3.5, ax=ax)

    node_colors = []
    node_sizes = []
    for node_id, node in network.nodes.items():
        if node_id in blocked_nodes:
            node_colors.append("#ef4444")
        elif node_id == (selected_path[0] if selected_path else None):
            node_colors.append("#16a34a")
        elif node_id == (selected_path[-1] if selected_path else None):
            node_colors.append("#7c3aed")
        else:
            node_colors.append("#dbeafe")
        node_sizes.append(680 if node.node_type in {"origin", "destination"} else 450)

    nx.draw_networkx_nodes(graph, positions, node_color=node_colors, node_size=node_sizes, edgecolors="#334155", linewidths=1.0, ax=ax)
    label_map = {node_id: network.nodes[node_id].name.replace(" Logistics Hub", " Hub").replace(" Regional Hub", " Hub") for node_id in graph.nodes}
    nx.draw_networkx_labels(graph, positions, labels=label_map, font_size=7.5, font_weight="medium", ax=ax)

    legend_items = [
        Line2D([0], [0], color="#16a34a", linewidth=3.5, label="Selected route"),
        Line2D([0], [0], color="#dc2626", linewidth=2.0, linestyle="--", label="Unavailable link"),
    ]
    for mode, color in MODE_COLORS.items():
        if any(edge.mode.lower() == mode for edge in network.edges.values()):
            legend_items.append(Line2D([0], [0], color=color, linewidth=1.8, label=mode.title()))
    ax.legend(handles=legend_items, loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=8, frameon=True)
    ax.set_title("Illustrative humanitarian logistics network", fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Schematic layout only — node spacing is not geographic distance")
    ax.set_axis_off()
    ax.margins(0.18)
    ax.text(
        0.01, -0.04,
        "Green line = selected route · Red dashed line/node = unavailable · Edge colours show synthetic transport modes",
        transform=ax.transAxes, fontsize=8.5, color="#475569",
    )
    fig.tight_layout(rect=[0, 0.02, 0.83, 1])
    return fig

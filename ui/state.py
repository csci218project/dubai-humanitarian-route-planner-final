"""Session state for the Streamlit front end.

Streamlit reruns ``app.py`` from top to bottom after every interaction. Every
value the user can change therefore lives in ``st.session_state`` under a
fixed key, and the widgets are created with those keys. That lets one action
update several widgets at once: a priority preset moves three sliders, a
scenario fills both closure lists, and the chart inspector can close a hub.

Callbacks run *before* the rerun, which is the only moment Streamlit allows a
widget's value to be changed from code.
"""

from __future__ import annotations

import streamlit as st

from humanitarian_route_planner.network import RouteNetwork
from humanitarian_route_planner.scenarios import SCENARIOS

# (time, cost, risk) weights for each preset.
PRESETS: dict[str, tuple[float, float, float]] = {
    "Fastest": (5.0, 0.0, 0.0),
    "Cheapest": (0.0, 5.0, 0.0),
    "Safest": (0.0, 0.0, 5.0),
    "Balanced": (1.0, 0.75, 2.0),
}
ALGORITHMS = ["A*", "Dijkstra", "Hierarchical"]
CHART_KEY = "route_chart"


def default_endpoints(network: RouteNetwork) -> tuple[str, str]:
    """The network's default origin and destination, or its first and last hubs."""
    node_ids = list(network.nodes)
    origin = network.metadata.get("default_origin")
    destination = network.metadata.get("default_destination")
    return (origin if origin in network.nodes else node_ids[0],
            destination if destination in network.nodes else node_ids[-1])


def init_state(network: RouteNetwork) -> None:
    """Create every session key once, with the app's starting values."""
    origin, destination = default_endpoints(network)
    defaults = {
        "origin": origin,
        "destination": destination,
        "preset": "Balanced",
        "w_time": PRESETS["Balanced"][0],
        "w_cost": PRESETS["Balanced"][1],
        "w_risk": PRESETS["Balanced"][2],
        "scenario": next(iter(SCENARIOS)),
        "closed_nodes": [],
        "closed_edges": [],
        "highlight": "A*",
        "inspected": None,        # ("node" | "edge", id) shown in the inspector
        "last_selection": None,   # last chart click already handled
        "pending_toast": None,    # message to show once on the next run
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


# ---- Priorities -----------------------------------------------------------

def apply_preset() -> None:
    """Preset clicked: move the three sliders to that preset's weights."""
    preset = st.session_state.get("preset")
    if preset in PRESETS:
        st.session_state.w_time, st.session_state.w_cost, st.session_state.w_risk = PRESETS[preset]
    else:  # the active preset was clicked again; keep showing whatever matches
        sync_preset_from_weights()


def sync_preset_from_weights() -> None:
    """Slider moved: highlight the matching preset, or none for custom weights."""
    current = (st.session_state.w_time, st.session_state.w_cost, st.session_state.w_risk)
    st.session_state.preset = next((name for name, weights in PRESETS.items() if weights == current), None)


# ---- Disruptions ----------------------------------------------------------

def reset_for_network(network: RouteNetwork) -> None:
    """Another network was picked: start again from its defaults, with nothing closed."""
    st.session_state.origin, st.session_state.destination = default_endpoints(network)
    st.session_state.scenario = next(iter(SCENARIOS))
    st.session_state.closed_nodes = []
    st.session_state.closed_edges = []
    st.session_state.inspected = None


def keep_valid_state(network: RouteNetwork) -> None:
    """Drop anything the current network doesn't have. Runs before the widgets are drawn."""
    origin, destination = default_endpoints(network)
    if st.session_state.origin not in network.nodes:
        st.session_state.origin = origin
    if st.session_state.destination not in network.nodes:
        st.session_state.destination = destination
    nodes = [n for n in st.session_state.closed_nodes if n in network.nodes]
    if nodes != list(st.session_state.closed_nodes):
        st.session_state.closed_nodes = nodes
    edges = [e for e in st.session_state.closed_edges if e in network.edges]
    if edges != list(st.session_state.closed_edges):
        st.session_state.closed_edges = edges
    inspected = st.session_state.inspected
    if inspected and inspected[1] not in (network.nodes if inspected[0] == "node" else network.edges):
        st.session_state.inspected = None


def apply_scenario() -> None:
    """Scenario picked: load its closures into the two editable closure lists."""
    scenario = SCENARIOS[st.session_state.scenario]
    st.session_state.closed_nodes = sorted(scenario["blocked_nodes"])
    st.session_state.closed_edges = sorted(scenario["blocked_edges"])


def scenario_is_edited() -> bool:
    scenario = SCENARIOS[st.session_state.scenario]
    return (
        set(st.session_state.closed_nodes) != set(scenario["blocked_nodes"])
        or set(st.session_state.closed_edges) != set(scenario["blocked_edges"])
    )


def toggle_node(node_id: str, name: str) -> None:
    closed = list(st.session_state.closed_nodes)
    if node_id in closed:
        closed.remove(node_id)
        st.session_state.pending_toast = (f"Reopened {name}", ":material/check_circle:")
    else:
        closed.append(node_id)
        st.session_state.pending_toast = (f"Closed {name}", ":material/block:")
    st.session_state.closed_nodes = closed


def toggle_edge(edge_id: str, label: str) -> None:
    closed = list(st.session_state.closed_edges)
    if edge_id in closed:
        closed.remove(edge_id)
        st.session_state.pending_toast = (f"Reopened {label}", ":material/check_circle:")
    else:
        closed.append(edge_id)
        st.session_state.pending_toast = (f"Closed {label}", ":material/block:")
    st.session_state.closed_edges = closed


def reopen_node(node_id: str) -> None:
    st.session_state.closed_nodes = [n for n in st.session_state.closed_nodes if n != node_id]


def reopen_all() -> None:
    st.session_state.closed_nodes = []
    st.session_state.closed_edges = []
    st.session_state.pending_toast = ("Every hub and link is open again", ":material/check_circle:")


def set_endpoint(which: str, node_id: str, name: str) -> None:
    """Inspector shortcut: make the inspected hub the origin or destination."""
    other = "destination" if which == "origin" else "origin"
    if st.session_state[other] == node_id:  # swap rather than make them equal
        st.session_state[other] = st.session_state[which]
    st.session_state[which] = node_id
    st.session_state.pending_toast = (f"{name} is now the {which}", ":material/flag:")


# ---- Chart clicks ---------------------------------------------------------

def consume_chart_selection(network: RouteNetwork | None = None) -> None:
    """Turn the latest chart click into the inspected hub or link.

    Run this at the top of the script, before the chart is drawn, so the
    figure can already show the gilt ring around the clicked item. Plotly's
    selection persists between reruns, so a click is only handled once.
    """
    state = st.session_state.get(CHART_KEY)
    try:
        points = state["selection"]["points"] if state else []
    except (KeyError, TypeError):
        points = []
    picked = None
    for point in points:
        data = point.get("customdata")
        if isinstance(data, (list, tuple)) and len(data) >= 2 and data[0] in ("node", "edge"):
            kind, item = str(data[0]), str(data[1])
            if network is not None and item not in (network.nodes if kind == "node" else network.edges):
                continue   # a click left over from the other network
            picked = (kind, item)
            break
    if picked is None:
        st.session_state.last_selection = None  # cleared, so the next click counts
        return
    if picked != st.session_state.last_selection:
        st.session_state.inspected = picked
        st.session_state.last_selection = picked


def clear_inspector() -> None:
    st.session_state.inspected = None


def keep_a_highlight() -> None:
    if st.session_state.get("highlight") not in ALGORITHMS:
        st.session_state.highlight = "A*"


def show_pending_toast() -> None:
    message = st.session_state.get("pending_toast")
    if message:
        text, icon = message
        st.toast(text, icon=icon)
        st.session_state.pending_toast = None

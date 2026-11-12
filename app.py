"""Streamlit front end for the Dubai Humanitarian Route Planner.

Run with:  streamlit run app.py

The page reacts to every change at once; there is no "run" button. Streamlit
reruns this script after each interaction, the three algorithms re-solve the
small network in a few milliseconds, and the summary, chart and tables are
redrawn. Clicking a hub or link on the chart opens it in the inspector, where
it can be closed or reopened. When anything is closed, the route before the
closures is drawn faded on the chart and compared in a before/after table.

Front end only: routes are computed by ``humanitarian_route_planner``; the
``ui`` package handles layout, styling and interaction.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from humanitarian_route_planner.algorithms import compare_algorithms
from humanitarian_route_planner.models import CostWeights
from humanitarian_route_planner.network import RouteNetwork
from humanitarian_route_planner.scenarios import SCENARIOS
from ui import components as ui
from ui.chart import build_expansion_figure, build_route_figure, schematic_positions
from ui.palette import mode_name, node_type_name
from ui.sequence import hero_sequence, planner_anchor
from ui.state import (
    ALGORITHMS, CHART_KEY, PRESETS,
    apply_preset, apply_scenario, clear_inspector, consume_chart_selection, init_state,
    keep_a_highlight, keep_valid_state, reopen_all, reopen_node, reset_for_network,
    scenario_is_edited, set_endpoint, show_pending_toast, sync_preset_from_weights,
    toggle_edge, toggle_node,
)
from ui.theme import inject_theme

ROOT = Path(__file__).resolve().parent
NETWORK_CHOICES = [   # (label, file); files that don't exist are left out
    ("Sample network", ROOT / "data" / "sample_network.json"),
    ("Extended network", ROOT / "data" / "extended_network.json"),
]

st.set_page_config(
    page_title="Humanitarian Route Planner",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="auto",  # open on desktop, tucked away on phones
)


@st.cache_resource
def load_network(path: str) -> RouteNetwork:
    return RouteNetwork.from_json(Path(path))


@st.cache_resource
def chart_positions(path: str, _network: RouteNetwork) -> dict[str, tuple[float, float]]:
    # Cached per file; the leading underscore tells Streamlit not to hash the network object.
    return schematic_positions(_network)


NETWORK_FILES = {
    f"{label} ({len(load_network(str(path)).nodes)} hubs)": str(path)
    for label, path in NETWORK_CHOICES if path.exists()
}
if st.session_state.get("network_name") not in NETWORK_FILES:
    st.session_state.network_name = next(iter(NETWORK_FILES))
network_path = NETWORK_FILES[st.session_state.network_name]
network = load_network(network_path)
positions = chart_positions(network_path, network)
node_ids = list(network.nodes)
edge_ids = list(network.edges)


def on_network_change() -> None:
    reset_for_network(load_network(NETWORK_FILES[st.session_state.network_name]))


init_state(network)
consume_chart_selection(network)   # before drawing, so the chart can ring the clicked item
keep_valid_state(network)
inject_theme()
show_pending_toast()


def _sources_html(sources: object) -> str:
    """Credit the public datasets a network was built from (required by their licences)."""
    if not isinstance(sources, list) or not sources:
        return ""
    items = ", ".join(
        f'<a href="{escape(str(s.get("url", "")))}">{escape(str(s.get("name", "")))}</a> ({escape(str(s.get("licence", "")))})'
        for s in sources if isinstance(s, dict)
    )
    return f"<p><b>Sources.</b> {items}.</p>"


def node_name(node_id: str) -> str:
    return network.nodes[node_id].name


def edge_label(edge_id: str) -> str:
    edge = network.edges[edge_id]
    return f"{node_name(edge.source)} ↔ {node_name(edge.target)} ({mode_name(edge.mode).lower()})"


# ---- Sidebar: the request ------------------------------------------------------

with st.sidebar:
    ui.sidebar_heading("Route request")
    if len(NETWORK_FILES) > 1:
        st.selectbox(
            "Network", list(NETWORK_FILES), key="network_name", on_change=on_network_change,
            help="The sample is the original 10-hub network. The extended network adds real airports "
                 "and ports; every link value in both is illustrative.",
        )
    st.selectbox("Origin", node_ids, key="origin", format_func=node_name)
    st.selectbox("Destination", node_ids, key="destination", format_func=node_name)

    ui.sidebar_heading("Priorities")
    st.segmented_control(
        "Priority preset", list(PRESETS), key="preset",
        on_change=apply_preset, label_visibility="collapsed", width="stretch",
    )
    st.slider("Time", 0.0, 5.0, step=0.25, key="w_time", on_change=sync_preset_from_weights,
              help="Weight on travel hours.")
    st.slider("Cost", 0.0, 5.0, step=0.25, key="w_cost", on_change=sync_preset_from_weights,
              help="Weight on cost, counted per $1,000.")
    st.slider("Risk", 0.0, 5.0, step=0.25, key="w_risk", on_change=sync_preset_from_weights,
              help="Weight on each link's ordinal 0–10 risk points.")
    if st.session_state.preset is None:
        st.caption("Custom weights. Pick a preset to reset them.")

    ui.sidebar_heading("Disruptions")
    st.selectbox("Scenario", list(SCENARIOS), key="scenario", on_change=apply_scenario)
    scenario_note = str(SCENARIOS[st.session_state.scenario]["description"])
    if scenario_is_edited():
        scenario_note += " You've edited its closures below."
    st.caption(scenario_note)
    st.multiselect("Closed hubs", node_ids, key="closed_nodes", format_func=node_name,
                   placeholder="All hubs open")
    st.multiselect("Closed links", edge_ids, key="closed_edges", format_func=edge_label,
                   placeholder="All links open")
    st.button(
        "Reopen everything", on_click=reopen_all, width="stretch", icon=":material/lock_open:",
        disabled=not (st.session_state.closed_nodes or st.session_state.closed_edges),
    )


# ---- Solve (runs on every interaction) -----------------------------------------------

origin = st.session_state.origin
destination = st.session_state.destination
closed_nodes = set(st.session_state.closed_nodes)
closed_edges = set(st.session_state.closed_edges)
raw_weights = (st.session_state.w_time, st.session_state.w_cost, st.session_state.w_risk)
weights_ok = any(value > 0 for value in raw_weights)
weights = CostWeights(*raw_weights) if weights_ok else CostWeights(time=1.0, cost=0.0, risk=0.0)

problem = None
if origin == destination:
    problem = "same"
elif origin in closed_nodes:
    problem = "origin"
elif destination in closed_nodes:
    problem = "destination"

results, baseline, route = [], None, None
if problem is None:
    results = compare_algorithms(
        network, origin, destination, weights,
        blocked_nodes=closed_nodes, blocked_edges=closed_edges,
    )
    chosen = next((r for r in results if r.algorithm == st.session_state.highlight), None)
    route = chosen if chosen and chosen.success else next((r for r in results if r.success), None)
    # The same request with everything open, solved by the same algorithm: the "before".
    open_results = compare_algorithms(network, origin, destination, weights) if (closed_nodes or closed_edges) else results
    shown = route.algorithm if route else st.session_state.highlight
    baseline = next((r for r in open_results if r.algorithm == shown), None)

before_differs = bool(closed_nodes or closed_edges) and baseline is not None and baseline.success and (
    route is None or not route.success or route.edge_path != baseline.edge_path
)


# ---- Main page -------------------------------------------------------------------

if not hero_sequence():   # scroll-driven globe; plain masthead if the frames are missing
    ui.masthead()
planner_anchor()
ui.notice()

if not weights_ok:
    ui.alert("All three priorities are at zero, so the planner is using travel time alone. "
             "Raise any priority to change that.", tone="green")

if problem == "same":
    ui.alert("The origin and destination are the same hub. Pick a different destination in the sidebar.")
elif problem in ("origin", "destination"):
    blocked = origin if problem == "origin" else destination
    ui.alert(f"The {problem}, <b>{escape(node_name(blocked))}</b>, is closed. "
             f"Reopen it, or choose another {problem} in the sidebar.")
    st.button(f"Reopen {node_name(blocked)}", on_click=reopen_node, args=(blocked,), type="primary")
else:
    ui.dispatch(network, route, baseline, origin, destination, len(closed_nodes) + len(closed_edges))
    ui.journey(network, route)
    if (closed_nodes or closed_edges) and baseline is not None and baseline.success:
        ui.before_after(network, baseline, route)

chart_col, side_col = st.columns([3.1, 1], gap="large")

with chart_col:
    title_col, control_col = st.columns([1.25, 1], vertical_alignment="bottom")
    with title_col:
        chart_note = "Schematic: hubs are spaced out so labels fit, so distances aren't to scale."
        if len(network.nodes) > 16:
            chart_note += " Only key hubs are labelled; hover over any hub for its name."
        ui.section_heading("Route chart", chart_note)
    with control_col:
        st.segmented_control(
            "Show the route found by", ALGORITHMS, key="highlight", required=True,
            on_change=keep_a_highlight, width="stretch",
        )
    if route is not None and route.algorithm != st.session_state.highlight:
        st.caption(f"{st.session_state.highlight} found no route here, so the chart shows {route.algorithm}'s.")

    figure = build_route_figure(
        network, positions, route, closed_nodes, closed_edges,
        origin, destination, st.session_state.inspected,
        baseline_route=baseline if before_differs else None,
    )
    with st.container(key="chart_frame"):
        st.plotly_chart(
            figure, key=CHART_KEY, on_select="rerun", selection_mode=("points",), theme=None,
            config={"displayModeBar": False, "scrollZoom": False, "doubleClick": False},
        )

with side_col:
    inspected = st.session_state.inspected
    with st.container(key="inspector"):
        if inspected and inspected[0] == "node" and inspected[1] in network.nodes:
            node_id = inspected[1]
            is_closed = node_id in closed_nodes
            role = "origin" if node_id == origin else "destination" if node_id == destination else None
            st.html(ui.inspector_node(network, node_id, is_closed, role))
            if role:
                st.caption(f"The {role} can't be closed. Make another hub the {role} first.")
            else:
                st.button(
                    "Reopen this hub" if is_closed else "Close this hub",
                    key="inspector_toggle", on_click=toggle_node, args=(node_id, node_name(node_id)),
                    type="secondary" if is_closed else "primary", width="stretch",
                    icon=":material/lock_open:" if is_closed else ":material/block:",
                )
            if not is_closed:
                start_col, end_col = st.columns(2)
                start_col.button("Start here", key="inspector_origin", width="stretch",
                                 on_click=set_endpoint, args=("origin", node_id, node_name(node_id)),
                                 disabled=node_id == origin)
                end_col.button("Deliver here", key="inspector_destination", width="stretch",
                               on_click=set_endpoint, args=("destination", node_id, node_name(node_id)),
                               disabled=node_id == destination)
            st.button("Clear selection", key="inspector_clear", on_click=clear_inspector, type="tertiary")
        elif inspected and inspected[0] == "edge" and inspected[1] in network.edges:
            edge_id = inspected[1]
            edge = network.edges[edge_id]
            hub_closed = edge.source in closed_nodes or edge.target in closed_nodes
            is_closed = edge_id in closed_edges
            on_route = route is not None and edge_id in route.edge_path
            st.html(ui.inspector_edge(network, edge_id, is_closed or hub_closed, on_route))
            if hub_closed and not is_closed:
                st.caption("This link can't be used because one of its hubs is closed.")
            else:
                st.button(
                    "Reopen this link" if is_closed else "Close this link",
                    key="inspector_toggle", on_click=toggle_edge, args=(edge_id, edge_label(edge_id)),
                    type="secondary" if is_closed else "primary", width="stretch",
                    icon=":material/lock_open:" if is_closed else ":material/block:",
                )
            st.button("Clear selection", key="inspector_clear", on_click=clear_inspector, type="tertiary")
        else:
            st.html(ui.inspector_empty())
    ui.legend(show_before=before_differs)


# ---- Detail tabs ------------------------------------------------------------------

compare_tab, legs_tab, data_tab = st.tabs(["Compare algorithms", "Leg-by-leg plan", "Network data"])

with compare_tab:
    if results:
        ui.comparison_summary(results)
        ledger_col, bars_col = st.columns([1.5, 1], gap="large")
        with ledger_col:
            ui.comparison_ledger(results)
        with bars_col:
            st.plotly_chart(build_expansion_figure(results), key="expansion_chart", theme=None,
                            config={"displayModeBar": False})
        st.caption(
            f"Runtimes on a {len(network.nodes)}-hub network are tiny and change from run to run. "
            "Use scripts/run_benchmarks.py for repeatable numbers in the report."
        )
    else:
        ui.alert("Fix the request above to compare the algorithms.", tone="green")

with legs_tab:
    ui.legs_ledger(network, route if problem is None else None)

with data_tab:
    disclaimer = network.metadata.get("disclaimer", "Synthetic demonstration network.")
    risk_scale = network.metadata.get("risk_scale", "an ordinal 0–10 score, not a probability")
    st.html(
        '<div class="hrp-prose">'
        f"<p><b>Data notice.</b> {escape(disclaimer)}</p>"
        f"<p>{len(network.nodes)} hubs and {len(network.edges)} links. Risk runs from {escape(risk_scale)}.</p>"
        + _sources_html(network.metadata.get("sources"))
        + "</div>"
    )
    st.dataframe(
        pd.DataFrame([
            {
                "Hub": node.name, "Type": node_type_name(node.node_type), "Region": node.region,
                "Status": "Closed" if node_id in closed_nodes else "Open", "ID": node_id,
            }
            for node_id, node in network.nodes.items()
        ]),
        hide_index=True,
    )
    st.dataframe(
        pd.DataFrame([
            {
                "From": node_name(edge.source), "To": node_name(edge.target), "Mode": mode_name(edge.mode),
                "Hours": edge.time_hours, "Cost (USD)": edge.cost_usd, "Risk (0–10)": edge.risk_score,
                "Capacity (t)": edge.capacity_tonnes,
                "Status": "Closed" if (edge_id in closed_edges or edge.source in closed_nodes
                                       or edge.target in closed_nodes) else "Open",
                "Notes": edge.notes, "ID": edge_id,
            }
            for edge_id, edge in network.edges.items()
        ]),
        hide_index=True,
    )
    st.html(
        '<div class="hrp-prose">'
        "<p><b>How to read the numbers.</b> Time is a synthetic per-link estimate with no schedules, "
        "queues, customs or handling. Cost is a placeholder in US dollars, not a quote; the cost priority "
        "counts it per $1,000. Risk points add up the ordinal link scores and aren’t probabilities or "
        "security assessments. A route’s bottleneck capacity is its smallest leg capacity; cargo packing "
        "isn’t modelled.</p>"
        "<p>Closing hubs and links demonstrates re-routing only. Real closures and permissions need verified, "
        "time-stamped sources and an authorised logistics operator.</p></div>"
    )

ui.footer()

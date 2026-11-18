"""Streamlit front end for the Dubai Humanitarian Route Planner.

Run with:  streamlit run app.py

The page reacts to every change at once; there is no "run" button. Streamlit
reruns this script after each interaction, the three algorithms re-solve the
network in a few milliseconds, and the summary, chart and tables are redrawn.
Clicking a hub or leg on the chart opens it in the inspector, where it can be
closed or reopened. Under a disruption (one of the data's scenarios, or your
own closures) the route under normal conditions is drawn faded on the chart
and compared in a before/after table.

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
from ui import components as ui
from ui.chart import build_expansion_figure, build_route_figure, schematic_positions
from ui.palette import mode_name, node_type_name
from ui.sequence import hero_sequence, planner_anchor
from ui.state import (
    ALGORITHMS, CHART_KEY, PRESETS,
    apply_preset, apply_scenario, clear_inspector, consume_chart_selection, init_state,
    keep_a_highlight, keep_valid_state, reopen_all, reopen_node, reset_for_network,
    scenario_is_edited, scenario_specs, set_endpoint, show_pending_toast,
    sync_preset_from_weights, toggle_edge, toggle_node,
)
from ui.theme import inject_theme

ROOT = Path(__file__).resolve().parent
NETWORK_CHOICES = [   # (label, file); files that don't exist are left out
    ("Dubai to El Obeid network", ROOT / "data" / "hrp_network.json"),
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


@st.cache_resource
def scenario_network(path: str, scenario: str, _network: RouteNetwork, _spec: dict) -> RouteNetwork:
    # The network as it runs under a scenario (some legs slower or dearer); cached per file and scenario.
    return _network.with_adjustments(_spec.get("time_mult"), _spec.get("cost_mult"))


NETWORK_FILES = {
    f"{label} ({len(load_network(str(path)).nodes)} hubs)": str(path)
    for label, path in NETWORK_CHOICES if path.exists()
}
if st.session_state.get("network_name") not in NETWORK_FILES:
    st.session_state.network_name = next(iter(NETWORK_FILES))
network_path = NETWORK_FILES[st.session_state.network_name]
network = load_network(network_path)
specs = scenario_specs(network)
positions = chart_positions(network_path, network)
node_ids = list(network.nodes)
edge_ids = list(network.edges)
ui.configure_units(network.metadata)


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
    arrow = "→" if network.directed else "↔"
    return f"{edge_id}: {node_name(edge.source)} {arrow} {node_name(edge.target)} ({mode_name(edge.mode).lower()})"


def factor_text(factors: dict[str, float]) -> str:
    values = sorted(set(factors.values()))
    return f"{values[0]:g}×" if len(values) == 1 else f"up to {values[-1]:g}×"


def scenario_note(spec: dict) -> str:
    closes = len(spec.get("close_edges", [])) + len(spec.get("close_nodes", []))
    slower, dearer = spec.get("time_mult", {}), spec.get("cost_mult", {})
    if not (closes or slower or dearer):
        return spec.get("trigger") or "Everything open."
    parts = [f"{spec['type']}." if spec.get("type") else "", f"Trigger: {spec['trigger']}." if spec.get("trigger") else ""]
    if slower:
        parts.append(f"{len(slower)} leg{'s' if len(slower) != 1 else ''} take {factor_text(slower)} as long.")
    if dearer:
        parts.append(f"{len(dearer)} leg{'s' if len(dearer) != 1 else ''} cost {factor_text(dearer)} as much.")
    if spec.get("duration_days"):
        parts.append(f"Expected to last about {spec['duration_days']} days.")
    return " ".join(part for part in parts if part)


# ---- Sidebar: the request ------------------------------------------------------

with st.sidebar:
    ui.sidebar_heading("Route request")
    if len(NETWORK_FILES) > 1:
        st.selectbox("Network", list(NETWORK_FILES), key="network_name", on_change=on_network_change)
    st.selectbox("Origin", node_ids, key="origin", format_func=node_name)
    st.selectbox("Destination", node_ids, key="destination", format_func=node_name)

    ui.sidebar_heading("Priorities")
    st.segmented_control(
        "Priority preset", list(PRESETS), key="preset",
        on_change=apply_preset, label_visibility="collapsed", width="stretch",
    )
    st.slider("Time", 0.0, 5.0, step=0.25, key="w_time", on_change=sync_preset_from_weights,
              help="Weight on travel hours, transfers included.")
    st.slider("Cost", 0.0, 5.0, step=0.25, key="w_cost", on_change=sync_preset_from_weights,
              help=f"Weight on {ui.cost_label().lower()}, counted per $1,000.")
    st.slider("Risk", 0.0, 5.0, step=0.25, key="w_risk", on_change=sync_preset_from_weights,
              help=f"Weight on each leg's risk score ({ui.risk_scale()}).")
    if st.session_state.preset is None:
        st.caption("Custom weights. Pick a preset to reset them.")

    ui.sidebar_heading("Disruptions")
    st.selectbox("Scenario", list(specs), key="scenario", on_change=apply_scenario, args=(specs,))
    note = scenario_note(specs[st.session_state.scenario])
    if scenario_is_edited(specs):
        note += " You've edited its closures below."
    st.caption(note)
    st.multiselect("Closed hubs", node_ids, key="closed_nodes", format_func=node_name,
                   placeholder="All hubs open")
    st.multiselect("Closed legs" if network.directed else "Closed links", edge_ids, key="closed_edges",
                   format_func=edge_label, placeholder="All legs open")
    st.button(
        "Reopen everything", on_click=reopen_all, width="stretch", icon=":material/lock_open:",
        disabled=not (st.session_state.closed_nodes or st.session_state.closed_edges),
    )


# ---- Solve (runs on every interaction) -----------------------------------------------

spec = specs[st.session_state.scenario]
active = scenario_network(network_path, st.session_state.scenario, network, spec)
origin = st.session_state.origin
destination = st.session_state.destination
closed_nodes = set(st.session_state.closed_nodes)
closed_edges = set(st.session_state.closed_edges)
adjusted_legs = set(spec.get("time_mult", {})) | set(spec.get("cost_mult", {}))
disruptions = len(closed_nodes) + len(closed_edges) + len(adjusted_legs)
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
        active, origin, destination, weights,
        blocked_nodes=closed_nodes, blocked_edges=closed_edges,
    )
    chosen = next((r for r in results if r.algorithm == st.session_state.highlight), None)
    route = chosen if chosen and chosen.success else next((r for r in results if r.success), None)
    # The same request under normal conditions, solved by the same algorithm: the "before".
    open_results = compare_algorithms(network, origin, destination, weights) if disruptions else results
    shown = route.algorithm if route else st.session_state.highlight
    baseline = next((r for r in open_results if r.algorithm == shown), None)

before_differs = bool(disruptions) and baseline is not None and baseline.success and (
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
    ui.dispatch(active, route, baseline, origin, destination, disruptions)
    ui.journey(active, route)
    if disruptions and baseline is not None and baseline.success:
        scenario_changes = spec.get("close_edges") or spec.get("close_nodes") or adjusted_legs
        ui.before_after(active, baseline, route, spec.get("expected_reroute") if scenario_changes else None)

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
        active, positions, route, closed_nodes, closed_edges,
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
            st.html(ui.inspector_node(active, node_id, is_closed, role))
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
            changes = []
            if edge_id in spec.get("time_mult", {}):
                changes.append(f"takes {spec['time_mult'][edge_id]:g}× as long")
            if edge_id in spec.get("cost_mult", {}):
                changes.append(f"costs {spec['cost_mult'][edge_id]:g}× as much")
            st.html(ui.inspector_edge(active, edge_id, is_closed or hub_closed, on_route,
                                      " and ".join(changes) or None))
            if hub_closed and not is_closed:
                st.caption("This leg can't be used because one of its hubs is closed.")
            else:
                st.button(
                    "Reopen this leg" if is_closed else "Close this leg",
                    key="inspector_toggle", on_click=toggle_edge, args=(edge_id, edge_label(edge_id)),
                    type="secondary" if is_closed else "primary", width="stretch",
                    icon=":material/lock_open:" if is_closed else ":material/block:",
                )
            st.button("Clear selection", key="inspector_clear", on_click=clear_inspector, type="tertiary")
        else:
            st.html(ui.inspector_empty())
    ui.legend(
        modes=[edge.mode for edge in network.edges.values()],
        show_before=before_differs,
        node_types={node.node_type for node in network.nodes.values()},
    )


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
    ui.legs_ledger(active, route if problem is None else None)

with data_tab:
    meta = network.metadata
    rule = network.transfer
    st.html(
        '<div class="hrp-prose">'
        f"<p><b>Data notice.</b> {escape(meta.get('disclaimer', 'Illustrative network.'))}</p>"
        f"<p>{len(network.nodes)} hubs, {len(network.edges)} {'one-way legs' if network.directed else 'links'} "
        f"and {len(specs)} scenario{'s' if len(specs) != 1 else ''}. Risk runs from "
        f"{escape(str(meta.get('risk_scale', '0 to 10')))}.</p>"
        + _sources_html(meta.get("sources"))
        + "</div>"
    )
    closed_by_hub = lambda e: e.edge_id in closed_edges or e.source in closed_nodes or e.target in closed_nodes  # noqa: E731
    st.dataframe(
        pd.DataFrame([
            {
                "ID": node_id, "Hub": node.name, "Type": node_type_name(node.node_type), "Region": node.region,
                "Status": "Closed" if node_id in closed_nodes else "Open",
            }
            for node_id, node in network.nodes.items()
        ]),
        hide_index=True,
    )
    st.dataframe(
        pd.DataFrame([
            {
                "ID": edge_id, "From": node_name(edge.source), "To": node_name(edge.target),
                "Mode": mode_name(edge.mode), "Hours": edge.time_hours, "Slow case (h)": edge.time_hours_p90,
                f"Cost (USD{'/t' if ui.cost_label() == 'Cost per tonne' else ''})": edge.cost_usd,
                f"Risk ({ui.risk_scale()})": edge.risk_score, "Reliability (%)": edge.reliability_pct,
                f"Capacity ({ui.capacity(1).split(' ', 1)[1]})": edge.capacity_tonnes,
                "Distance (km)": edge.distance_km, "Corridor": edge.corridor,
                "Status": "Closed" if closed_by_hub(edge) else "Open", "Notes": edge.notes,
            }
            for edge_id, edge in network.edges.items()
        ]),
        hide_index=True,
    )
    scenario_rows = [
        {
            "Scenario": label, "Type": s.get("type", ""), "Trigger": s.get("trigger", ""),
            "Closed legs": ", ".join(s.get("close_edges", [])),
            "Slower legs": ", ".join(f"{k} ×{v:g}" for k, v in s.get("time_mult", {}).items()),
            "Dearer legs": ", ".join(f"{k} ×{v:g}" for k, v in s.get("cost_mult", {}).items()),
            "Days": s.get("duration_days"), "Expected reroute": s.get("expected_reroute", ""),
        }
        for label, s in specs.items()
    ]
    if meta.get("scenarios"):
        st.dataframe(pd.DataFrame(scenario_rows), hide_index=True)
    transfer_text = (
        f"When cargo switches between air, sea and road at a hub that has no transfer leg of its own, the route "
        f"pays a transfer of {rule.time_hours:g} h and ${rule.cost_usd:g}{'/t' if ui.cost_label() == 'Cost per tonne' else ''} "
        f"({escape(str(meta.get('transfer', {}).get('basis', 'set in the data file')).lower())}). Transfer legs "
        "already include that work, so they never add another. "
    ) if rule else ""
    st.html(
        '<div class="hrp-prose">'
        "<p><b>How to read the numbers.</b> "
        + ("Each leg runs one way, from its source to its target. " if network.directed else "")
        + "Time is the typical transit time; the slow case (p90) is the time 90% of trips beat, and a route's "
        "slow case adds up every leg's p90. "
        + ("Cost is in US dollars per tonne of cargo. " if ui.cost_label() == "Cost per tonne" else "Cost is in US dollars. ")
        + "Risk is the data's ordinal score per leg, added along the route; reliability is the chance that every "
        "leg runs as planned, treating legs as independent. "
        + transfer_text
        + "A route's bottleneck capacity is its smallest leg capacity.</p>"
        "<p>Closing hubs and legs, and the scenarios, demonstrate re-routing only. Real closures and permissions "
        "need verified, time-stamped sources and an authorised logistics operator.</p></div>"
    )

ui.footer()

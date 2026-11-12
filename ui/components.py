"""Small HTML building blocks for the Streamlit front end.

Each function returns an HTML string (or renders one with ``st.html``). The
styling lives in ``ui/theme.css``; class names here all start with ``hrp-``.
User-facing text from the data file is always passed through ``escape``.
"""

from __future__ import annotations

from html import escape

import streamlit as st

from humanitarian_route_planner.models import RouteResult
from humanitarian_route_planner.network import RouteNetwork

from .palette import mode_css, mode_key, mode_name, node_type_name

# Material Design icon paths (Apache 2.0), drawn with currentColor.
_ICON_PATHS = {
    "air": "M21 16v-2l-8-5V3.5A1.5 1.5 0 0 0 11.5 2 1.5 1.5 0 0 0 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z",
    "sea": (
        "M17 15l1.55 1.55c-.96 1.69-3.33 3.04-5.55 3.37V11h3V9h-3V7.82C14.16 7.4 15 6.3 15 5c0-1.65-1.35-3-3-3S9 3.35 9 5"
        "c0 1.3.84 2.4 2 2.82V9H8v2h3v8.92c-2.22-.33-4.59-1.68-5.55-3.37L7 15l-4-3v3c0 3.88 4.92 7 9 7s9-3.12 9-7v-3l-4 3z"
        "M12 4c.55 0 1 .45 1 1s-.45 1-1 1-1-.45-1-1 .45-1 1-1z"
    ),
    "road": (
        "M20 8h-3V4H3c-1.1 0-2 .9-2 2v11h2c0 1.66 1.34 3 3 3s3-1.34 3-3h6c0 1.66 1.34 3 3 3s3-1.34 3-3h2v-5l-3-4z"
        "M6 18.5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zm13.5-9l1.96 2.5H17V9.5h2.5z"
        "m-1.5 9c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"
    ),
}


def icon(mode: str, size: int = 18) -> str:
    key = mode_key(mode)
    keys = {"air": ["air"], "sea": ["sea"], "road": ["road"], "land convoy": ["road"],
            "sea + road": ["sea", "road"], "multimodal": ["sea", "road"]}.get(key, ["road"])
    return "".join(
        f'<svg class="hrp-icon" width="{size}" height="{size}" viewBox="0 0 24 24" aria-hidden="true">'
        f'<path fill="currentColor" d="{_ICON_PATHS[k]}"/></svg>'
        for k in keys
    )


_FLEURON = (
    '<svg class="hrp-fleuron" viewBox="0 0 240 16" aria-hidden="true" preserveAspectRatio="xMidYMid meet">'
    '<path d="M0 8H92M148 8H240" stroke="currentColor" stroke-width="1"/>'
    '<path d="M120 1.5 126.5 8 120 14.5 113.5 8Z" fill="currentColor"/>'
    '<circle cx="104" cy="8" r="2.2" fill="currentColor"/><circle cx="136" cy="8" r="2.2" fill="currentColor"/>'
    '<circle cx="96" cy="8" r="1.2" fill="currentColor"/><circle cx="144" cy="8" r="1.2" fill="currentColor"/>'
    "</svg>"
)


# ---- Formatting -------------------------------------------------------------

def hours(value: float | None) -> str:
    return "–" if value is None else f"{value:,.1f} h"


def money(value: float | None) -> str:
    return "–" if value is None else f"${value:,.0f}"


def points(value: float | None) -> str:
    return "–" if value is None else f"{value:,.1f}"


def signed_int(value: int) -> str:
    return f"+{value}" if value > 0 else f"−{abs(value)}" if value < 0 else "±0"


def signed(value: float, unit: str = "", money_format: bool = False) -> str:
    sign = "+" if value > 0 else "−" if value < 0 else "±"
    magnitude = abs(value)
    body = f"${magnitude:,.0f}" if money_format else f"{magnitude:,.1f}{unit}"
    return f"{sign}{body}"


# ---- Page furniture -----------------------------------------------------------

def masthead() -> None:
    st.html(
        '<header class="hrp-masthead">'
        '<p class="hrp-kicker">A Dubai Humanitarian use case for CSCI218, Project B</p>'
        '<h1 class="hrp-title">Humanitarian Route Planner</h1>'
        '<p class="hrp-standfirst">Find the best way to move relief cargo from Dubai, then close airports, '
        "ports and corridors to see how Dijkstra, A* and hierarchical search adapt.</p>"
        f'<div class="hrp-rule">{_FLEURON}</div>'
        "</header>"
    )


def notice() -> None:
    st.html(
        '<p class="hrp-notice"><strong>Synthetic teaching network.</strong> Times, costs, risk scores and '
        "corridors are invented for algorithm demonstrations. Don’t use this tool to plan real aid movements.</p>"
    )


def sidebar_heading(text: str) -> None:
    st.html(f'<div class="hrp-side-head"><span>{escape(text)}</span>{_FLEURON}</div>')


def section_heading(text: str, note: str | None = None) -> None:
    note_html = f'<p class="hrp-section-note">{escape(note)}</p>' if note else ""
    st.html(f'<div class="hrp-section"><h2>{escape(text)}</h2>{note_html}</div>')


def alert(message_html: str, tone: str = "claret") -> None:
    st.html(f'<div class="hrp-alert hrp-alert-{tone}" role="status">{message_html}</div>')


def footer() -> None:
    st.html(
        '<footer class="hrp-footer">CSCI218 Foundations of Artificial Intelligence, '
        "University of Wollongong in Dubai, Autumn 2026. Teaching prototype on synthetic data.</footer>"
    )


# ---- Dispatch summary ---------------------------------------------------------

def dispatch(
    network: RouteNetwork,
    route: RouteResult | None,
    baseline: RouteResult | None,
    origin: str,
    destination: str,
    closed_count: int,
) -> None:
    """The headline: what was found, its numbers, and what the closures cost."""
    origin_name = escape(network.nodes[origin].name)
    destination_name = escape(network.nodes[destination].name)

    if route is None or not route.success:
        if baseline is not None and baseline.success:
            impact = ("Reopen a hub or link to restore a path; closed items are drawn in claret on the chart.")
        else:
            impact = "The destination can’t be reached even with every hub and link open."
        st.html(
            '<section class="hrp-dispatch is-failed" aria-live="polite">'
            f'<p class="hrp-lead">No route reaches <b>{destination_name}</b> from <b>{origin_name}</b> '
            "with the current closures.</p>"
            f'<p class="hrp-impact">{impact}</p></section>'
        )
        return

    legs = route.hops
    lead = (
        f'<b>{escape(route.algorithm)}</b> sends the shipment from <b>{origin_name}</b> to '
        f'<b>{destination_name}</b> in <b>{legs} leg{"s" if legs != 1 else ""}</b>.'
    )
    capacity = f"{route.minimum_capacity_tonnes:g} t" if route.minimum_capacity_tonnes is not None else "–"
    figures = [
        ("Travel time", hours(route.total_time_hours)),
        ("Illustrative cost", money(route.total_cost_usd)),
        ("Risk points", points(route.total_risk_points)),
        ("Route score", f"{route.objective_score:,.2f}"),
        ("Bottleneck capacity", capacity),
    ]
    figures_html = "".join(f'<div><dt>{label}</dt><dd>{value}</dd></div>' for label, value in figures)

    if closed_count == 0:
        impact = "Everything is open. Close a hub or link, in the sidebar or by clicking the chart, to see the route adapt."
    elif baseline is None or not baseline.success:
        impact = "No open-network route exists to compare against."
    elif route.edge_path == baseline.edge_path:
        impact = (
            f"The {closed_count} closure{'s' if closed_count != 1 else ''} "
            "don’t touch this route; it matches the open-network route."
        )
    else:
        deltas = [
            (route.total_time_hours - baseline.total_time_hours, "time", lambda d: signed(d, " h")),
            (route.total_cost_usd - baseline.total_cost_usd, "cost", lambda d: signed(d, money_format=True)),
            (route.total_risk_points - baseline.total_risk_points, "risk", lambda d: signed(d, " risk points")),
        ]
        changed = [f"<b>{fmt(d)}</b>" for d, _, fmt in deltas if abs(d) > 1e-9]
        same = [name for d, name, _ in deltas if abs(d) <= 1e-9]
        if changed:
            listed = changed[0] if len(changed) == 1 else ", ".join(changed[:-1]) + " and " + changed[-1]
            impact = f"Compared with the open network, the closures change the route: {listed}"
            impact += f"; {' and '.join(same)} {'is' if len(same) == 1 else 'are'} unchanged." if same else "."
        else:
            impact = "The closures change the route, but time, cost and risk come out the same."
    st.html(
        '<section class="hrp-dispatch" aria-live="polite">'
        f'<p class="hrp-lead">{lead}</p>'
        f'<dl class="hrp-figures">{figures_html}</dl>'
        f'<p class="hrp-impact">{impact}</p></section>'
    )


# ---- Journey strip ------------------------------------------------------------

def journey(network: RouteNetwork, route: RouteResult | None) -> None:
    """The route as a numbered sequence of stops joined by transport legs."""
    if route is None or not route.success:
        return
    parts = []
    elapsed = 0.0
    last = len(route.node_path) - 1
    for index, node_id in enumerate(route.node_path):
        node = network.nodes[node_id]
        role = " is-origin" if index == 0 else " is-destination" if index == last else ""
        parts.append(
            f'<li class="hrp-stop{role}"><span class="hrp-roundel">{index + 1}</span>'
            f'<span class="hrp-stop-name">{escape(node.name)}</span>'
            f'<span class="hrp-stop-time">{"Departs" if index == 0 else hours(elapsed)}</span></li>'
        )
        if index < len(route.edge_path):
            edge = network.edges[route.edge_path[index]]
            elapsed += edge.time_hours
            parts.append(
                f'<li class="hrp-leg" aria-label="{escape(mode_name(edge.mode))}, {edge.time_hours:g} hours">'
                f'<span class="hrp-dash hrp-leg-line {mode_css(edge.mode)}"></span>'
                f'<span class="hrp-leg-mode">{icon(edge.mode)}{escape(mode_name(edge.mode))}</span>'
                f'<span class="hrp-leg-time">{edge.time_hours:g} h</span></li>'
            )
    st.html(
        f'<ol class="hrp-journey" aria-label="Stops on the route found by {escape(route.algorithm)}">'
        + "".join(parts) + "</ol>"
    )


# ---- Inspector ----------------------------------------------------------------

def inspector_empty() -> str:
    return (
        '<h3 class="hrp-panel-title">Hub or link details</h3>'
        '<p class="hrp-panel-text">Click a hub, or the small diamond halfway along a link, to see its details '
        "here. You can close or reopen it from this panel.</p>"
    )


def inspector_node(network: RouteNetwork, node_id: str, closed: bool, role: str | None) -> str:
    node = network.nodes[node_id]
    links = len(network.neighbors(node_id))
    status = "Closed" if closed else (role.title() if role else "Open")
    tone = "closed" if closed else "open"
    description = f'<p class="hrp-panel-text">{escape(node.description)}</p>' if node.description else ""
    return (
        f'<h3 class="hrp-panel-title">{escape(node.name)}</h3>'
        f'<p class="hrp-panel-meta">{escape(node_type_name(node.node_type))} in {escape(node.region)}, '
        f'{links} link{"s" if links != 1 else ""}</p>'
        f'<p class="hrp-status hrp-status-{tone}">{status}</p>{description}'
    )


def inspector_edge(network: RouteNetwork, edge_id: str, closed: bool, on_route: bool) -> str:
    edge = network.edges[edge_id]
    status = "Closed" if closed else ("On the route" if on_route else "Open")
    tone = "closed" if closed else "open"
    rows = [
        ("Mode", f"{icon(edge.mode, 16)} {escape(mode_name(edge.mode))}"),
        ("Time", f"{edge.time_hours:g} h"),
        ("Cost", money(edge.cost_usd)),
        ("Risk", f"{edge.risk_score:g} of 10"),
        ("Capacity", f"{edge.capacity_tonnes:g} t"),
    ]
    table = "".join(f"<tr><th scope='row'>{label}</th><td>{value}</td></tr>" for label, value in rows)
    notes = f'<p class="hrp-panel-text"><i>{escape(edge.notes)}</i></p>' if edge.notes else ""
    return (
        f'<h3 class="hrp-panel-title">{escape(network.nodes[edge.source].name)} to '
        f'{escape(network.nodes[edge.target].name)}</h3>'
        f'<p class="hrp-status hrp-status-{tone}">{status}</p>'
        f'<table class="hrp-facts">{table}</table>{notes}'
    )


def legend(show_before: bool = False) -> None:
    rows = [('<span class="hrp-key-route"></span>', "Route that was found")]
    if show_before:
        rows.append(('<span class="hrp-dash m-before"></span>', "Route before the closures"))
    rows += [
        ('<span class="hrp-dash m-closed"></span>', "Closed hub or link"),
        ('<span class="hrp-dash m-air"></span>', "Air"),
        ('<span class="hrp-dash m-sea"></span>', "Sea"),
        ('<span class="hrp-dash m-road"></span>', "Road"),
        ('<span class="hrp-dash m-convoy"></span>', "Land convoy"),
        ('<span class="hrp-dash m-searoad"></span>', "Sea + road"),
    ]
    items = "".join(f"<li>{sample}<span>{label}</span></li>" for sample, label in rows)
    st.html(
        '<div class="hrp-key"><h3 class="hrp-panel-title">Key</h3>'
        f'<ul>{items}</ul>'
        '<p class="hrp-panel-text">Green circle: origin. Gilt star: destination. '
        "Triangle: airport. Diamond: port. Square: staging area.</p></div>"
    )


# ---- Before and after the closures ------------------------------------------------

def before_after(network: RouteNetwork, before: RouteResult, after: RouteResult | None) -> None:
    """Same request and weights, solved with everything open and with the current closures."""
    def stops(route: RouteResult) -> str:
        return " → ".join(escape(network.nodes[node_id].name) for node_id in route.node_path)

    def row(label: str, route: RouteResult | None) -> str:
        if route is None or not route.success:
            return (f"<tr><th scope='row'>{label}</th><td class='hrp-route-cell'><span class='hrp-bad'>No route</span>"
                    "</td><td>–</td><td>–</td><td>–</td><td>–</td><td>–</td></tr>")
        return (f"<tr><th scope='row'>{label}</th><td class='hrp-route-cell'>{stops(route)}</td>"
                f"<td>{route.hops}</td><td>{hours(route.total_time_hours)}</td><td>{money(route.total_cost_usd)}</td>"
                f"<td>{points(route.total_risk_points)}</td><td>{route.nodes_expanded}</td></tr>")

    if after is not None and after.success:
        change = (
            "<tr class='hrp-total'><th scope='row'>Change</th>"
            f"<td class='hrp-route-cell'>{'Same route' if after.edge_path == before.edge_path else 'Re-routed'}</td>"
            f"<td>{signed_int(after.hops - before.hops)}</td>"
            f"<td>{signed(after.total_time_hours - before.total_time_hours, ' h')}</td>"
            f"<td>{signed(after.total_cost_usd - before.total_cost_usd, money_format=True)}</td>"
            f"<td>{signed(after.total_risk_points - before.total_risk_points)}</td>"
            f"<td>{signed_int(after.nodes_expanded - before.nodes_expanded)}</td></tr>"
        )
    else:
        change = ("<tr class='hrp-total'><th scope='row'>Change</th><td class='hrp-route-cell'>"
                  "The closures cut the destination off.</td><td>–</td><td>–</td><td>–</td><td>–</td><td>–</td></tr>")
    algorithm = escape(before.algorithm)
    st.html(
        '<div class="hrp-section"><h2>Before and after the closures</h2>'
        f'<p class="hrp-section-note">Same request and weights, solved by {algorithm} with everything open '
        "and with the current closures.</p></div>"
        '<div class="hrp-ledger-wrap"><table class="hrp-ledger hrp-ledger-compare">'
        "<thead><tr><th scope='col'><span class='hrp-visually-hidden'>Network</span></th><th scope='col'>Route</th>"
        "<th scope='col'>Legs</th><th scope='col'>Time</th><th scope='col'>Cost</th><th scope='col'>Risk points</th>"
        "<th scope='col'>Nodes explored</th></tr></thead>"
        f"<tbody>{row('Before (all open)', before)}{row('After (with closures)', after)}</tbody>"
        f"<tfoot>{change}</tfoot></table></div>"
    )


# ---- Ledgers (tables) ------------------------------------------------------------

def comparison_ledger(results: list[RouteResult]) -> None:
    """Rows are measures, columns are algorithms, like a page of an account book."""
    reference = next((r for r in results if r.algorithm == "Dijkstra" and r.success), None)

    def cell(result: RouteResult, measure: str) -> str:
        if measure == "found":
            return "Yes" if result.success else "<span class='hrp-bad'>No</span>"
        if not result.success and measure not in ("expanded", "runtime"):
            return "–"
        if measure == "score":
            return f"{result.objective_score:,.2f}"
        if measure == "gap":
            if reference is None:
                return "–"
            gap = result.objective_score - reference.objective_score
            return "Optimal" if abs(gap) < 1e-9 else f"+{gap:,.2f}"
        if measure == "time":
            return hours(result.total_time_hours)
        if measure == "cost":
            return money(result.total_cost_usd)
        if measure == "risk":
            return points(result.total_risk_points)
        if measure == "legs":
            return str(result.hops)
        if measure == "expanded":
            return str(result.nodes_expanded)
        return f"{result.runtime_ms:.3f}"

    measures = [
        ("found", "Route found"), ("score", "Route score"), ("gap", "Gap to Dijkstra"),
        ("time", "Travel time"), ("cost", "Illustrative cost"), ("risk", "Risk points"),
        ("legs", "Legs"), ("expanded", "States expanded"), ("runtime", "Runtime (ms)"),
    ]
    head = "".join(f"<th scope='col'>{escape(r.algorithm)}</th>" for r in results)
    body = "".join(
        f"<tr><th scope='row'>{label}</th>" + "".join(f"<td>{cell(r, key)}</td>" for r in results) + "</tr>"
        for key, label in measures
    )
    st.html(
        '<div class="hrp-ledger-wrap"><table class="hrp-ledger">'
        f"<thead><tr><th scope='col'><span class='hrp-visually-hidden'>Measure</span></th>{head}</tr></thead>"
        f"<tbody>{body}</tbody></table></div>"
    )


def comparison_summary(results: list[RouteResult]) -> None:
    by_name = {r.algorithm: r for r in results}
    dijkstra, a_star, hier = by_name.get("Dijkstra"), by_name.get("A*"), by_name.get("Hierarchical")
    sentences = []
    if dijkstra and a_star and dijkstra.success and a_star.success:
        if abs(dijkstra.objective_score - a_star.objective_score) < 1e-9:
            if a_star.nodes_expanded < dijkstra.nodes_expanded:
                work = f"A* expanded {a_star.nodes_expanded} states to Dijkstra’s {dijkstra.nodes_expanded}."
            elif a_star.nodes_expanded == dijkstra.nodes_expanded:
                work = f"Both expanded {a_star.nodes_expanded} states; on a network this small the heuristic can’t prune much."
            else:
                work = f"A* expanded {a_star.nodes_expanded} states to Dijkstra’s {dijkstra.nodes_expanded}."
            sentences.append(f"Dijkstra and A* agree on the optimal score of {dijkstra.objective_score:,.2f}. {work}")
        else:
            sentences.append(
                "<span class='hrp-bad'>Dijkstra and A* disagree on the optimal score, "
                "so the A* heuristic isn’t admissible for this data.</span>"
            )
    elif dijkstra and not dijkstra.success:
        sentences.append("No algorithm can find a route with the current closures.")
    if hier is not None:
        regions = " → ".join(escape(r) for r in hier.abstract_regions)
        if hier.success and dijkstra and dijkstra.success:
            gap = hier.objective_score - dijkstra.objective_score
            outcome = "found the optimal route too" if abs(gap) < 1e-9 else f"found a route {gap:,.2f} points above optimal"
            sentences.append(f"Hierarchical search planned the regions first ({regions}) and {outcome}.")
        elif not hier.success and dijkstra and dijkstra.success:
            sentences.append(f"Hierarchical search couldn’t complete its region plan: {escape(hier.message.lower().rstrip('.'))}.")
    if sentences:
        st.html('<div class="hrp-prose">' + "".join(f"<p>{s}</p>" for s in sentences) + "</div>")


def legs_ledger(network: RouteNetwork, route: RouteResult | None) -> None:
    if route is None or not route.success:
        st.html('<p class="hrp-panel-text">No route to itemise with the current closures.</p>')
        return
    rows = []
    elapsed = 0.0
    for index, edge_id in enumerate(route.edge_path, start=1):
        edge = network.edges[edge_id]
        # Edges are undirected; show each leg in the direction of travel.
        start, end = route.node_path[index - 1], route.node_path[index]
        elapsed += edge.time_hours
        rows.append(
            f"<tr><td>{index}</td><td>{escape(network.nodes[start].name)}</td>"
            f"<td>{escape(network.nodes[end].name)}</td>"
            f"<td class='hrp-mode'>{icon(edge.mode, 16)} {escape(mode_name(edge.mode))}</td>"
            f"<td>{edge.time_hours:g}</td><td>{elapsed:,.1f}</td><td>{edge.cost_usd:,.0f}</td>"
            f"<td>{edge.risk_score:g}</td><td>{edge.capacity_tonnes:g}</td></tr>"
        )
    capacity = f"{route.minimum_capacity_tonnes:g}" if route.minimum_capacity_tonnes is not None else "–"
    totals = (
        "<tr class='hrp-total'><th scope='row' colspan='4'>Route total</th>"
        f"<td>{route.total_time_hours:,.1f}</td><td></td><td>{route.total_cost_usd:,.0f}</td>"
        f"<td>{route.total_risk_points:g}</td><td>{capacity} min.</td></tr>"
    )
    head = ("<tr><th scope='col'>Leg</th><th scope='col'>From</th><th scope='col'>To</th><th scope='col'>Mode</th>"
            "<th scope='col'>Hours</th><th scope='col'>Elapsed</th><th scope='col'>Cost (USD)</th>"
            "<th scope='col'>Risk</th><th scope='col'>Capacity (t)</th></tr>")
    regions = ""
    if route.abstract_regions:
        regions = ('<p class="hrp-panel-text">Region plan used by hierarchical search: '
                   + " → ".join(escape(r) for r in route.abstract_regions) + "</p>")
    st.html(
        '<div class="hrp-ledger-wrap"><table class="hrp-ledger hrp-ledger-legs">'
        f"<thead>{head}</thead><tbody>{''.join(rows)}</tbody><tfoot>{totals}</tfoot></table></div>{regions}"
    )

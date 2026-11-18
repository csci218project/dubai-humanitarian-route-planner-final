"""Interactive route chart for the Streamlit front end.

The chart is schematic on purpose. Hub positions start from their latitude and
longitude, then hubs that sit too close together (the three Dubai nodes are
only a few kilometres apart) are nudged apart so every label stays readable.
No basemap is drawn, so the picture never suggests that a real corridor exists.

Every hub and every link carries ``customdata = [kind, id, ...]``. When a user
clicks one, Streamlit returns that customdata in the chart's selection state,
which ``ui.state.consume_chart_selection`` turns into the inspected item.
"""

from __future__ import annotations

import base64
import math
from typing import Iterable

import plotly.graph_objects as go

from humanitarian_route_planner.models import RouteResult
from humanitarian_route_planner.network import RouteNetwork

from .palette import (
    CLARET, FONT, GILT, GREEN, INK, LINE, MODE_DASH, SEPIA, VELLUM,
    mode_key, mode_name, node_type_name,
)

Position = tuple[float, float]

# Approximate drawing size used only to estimate label boxes in data units.
_PLOT_W_PX, _PLOT_H_PX = 660.0, 500.0
_FONT_PX, _CHAR_PX, _LINE_PX = 13.0, 7.6, 16.5


# --------------------------------------------------------------------------
# Layout
# --------------------------------------------------------------------------

def schematic_positions(
    network: RouteNetwork,
    min_gap: float | None = None,
    y_stretch: float = 2.0,
    max_iterations: int = 800,
) -> dict[str, Position]:
    """Place hubs roughly where they are, then push overlapping hubs apart.

    1. Project longitude/latitude to a flat plane (longitude is shrunk by
       cos(mean latitude) so east-west and north-south distances are comparable).
    2. Stretch the vertical axis, because this network is much wider than it
       is tall and the labels need room.
    3. Normalise so the longest side is 1.0.
    4. Repeatedly push any pair closer than ``min_gap`` apart along the line
       joining them (half the overlap each, damped by 0.5 so it settles).

    Deterministic: the same network always gives the same picture.
    """
    ids = sorted(network.nodes)
    if not ids:
        return {}
    if min_gap is None:   # 0.25 for the 10-hub sample, tighter for bigger networks
        min_gap = min(0.25, 0.85 / math.sqrt(len(ids)))
    mean_lat = sum(network.nodes[i].latitude for i in ids) / len(ids)
    shrink = math.cos(math.radians(mean_lat))
    raw = {
        i: (network.nodes[i].longitude * shrink, network.nodes[i].latitude * y_stretch)
        for i in ids
    }
    xs = [p[0] for p in raw.values()]
    ys = [p[1] for p in raw.values()]
    span = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
    pos = {i: [(raw[i][0] - min(xs)) / span, (raw[i][1] - min(ys)) / span] for i in ids}

    for _ in range(max_iterations):
        worst_overlap = 0.0
        for a_index, a in enumerate(ids):
            for b_index, b in enumerate(ids[a_index + 1:], start=a_index + 1):
                dx = pos[b][0] - pos[a][0]
                dy = pos[b][1] - pos[a][1]
                distance = math.hypot(dx, dy)
                if distance >= min_gap:
                    continue
                if distance < 1e-9:  # identical coordinates: pick a fixed direction
                    angle = math.radians((a_index * 47 + b_index * 13) % 360)
                    dx, dy, distance = math.cos(angle), math.sin(angle), 1.0
                overlap = min_gap - distance
                worst_overlap = max(worst_overlap, overlap)
                push = overlap / 2 * 0.5
                ux, uy = dx / distance, dy / distance
                pos[a][0] -= ux * push
                pos[a][1] -= uy * push
                pos[b][0] += ux * push
                pos[b][1] += uy * push
        if worst_overlap < 1e-4:
            break
    return {i: (p[0], p[1]) for i, p in pos.items()}


def chart_label(name: str) -> str:
    """Short, wrapped label for the chart; the full name stays in the hover."""
    for long_form, short_form in (
        (" Logistics Hub", " Hub"),
        (" Regional Hub", " Hub"),
        (" Staging Hub", " Staging"),
    ):
        name = name.replace(long_form, short_form)
    words = name.split()
    if len(name) <= 14 or len(words) < 2:
        return name
    # Split into two lines with the shortest possible longest line.
    best = min(
        range(1, len(words)),
        key=lambda k: max(len(" ".join(words[:k])), len(" ".join(words[k:]))),
    )
    return " ".join(words[:best]) + "<br>" + " ".join(words[best:])


def _label_box(pos: Position, label: str, where: str, units: tuple[float, float]) -> tuple[float, float, float, float]:
    """Estimate a label's bounding box (x0, y0, x1, y1) in data units."""
    lines = label.split("<br>")
    width = max(len(line) for line in lines) * _CHAR_PX * units[0]
    height = len(lines) * _LINE_PX * units[1]
    gap_x, gap_y = 12 * units[0], 12 * units[1]
    x, y = pos
    if where == "top center":
        return (x - width / 2, y + gap_y, x + width / 2, y + gap_y + height)
    if where == "bottom center":
        return (x - width / 2, y - gap_y - height, x + width / 2, y - gap_y)
    if where == "middle right":
        return (x + gap_x, y - height / 2, x + gap_x + width, y + height / 2)
    return (x - gap_x - width, y - height / 2, x - gap_x, y + height / 2)  # middle left


def _overlap_area(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    width = min(a[2], b[2]) - max(a[0], b[0])
    height = min(a[3], b[3]) - max(a[1], b[1])
    return width * height if width > 0 and height > 0 else 0.0


def place_labels(
    positions: dict[str, Position],
    labels: dict[str, str],
    ranges: tuple[tuple[float, float], tuple[float, float]],
    segments: list[tuple[Position, Position]] | None = None,
) -> dict[str, str]:
    """Greedy label placement: try above, below, right, left; keep the least crowded.

    A candidate is penalised for overlapping labels already placed, for
    covering other hubs, for sitting on top of links, and for running off
    the drawing area.
    """
    segments = segments or []

    def links_crossed(box: tuple[float, float, float, float]) -> int:
        hits = 0
        for (ax, ay), (bx, by) in segments:
            for step in range(1, 12):  # sample the segment, skipping its end points
                t = step / 12
                x, y = ax + (bx - ax) * t, ay + (by - ay) * t
                if box[0] <= x <= box[2] and box[1] <= y <= box[3]:
                    hits += 1
                    break
        return hits

    (x0, x1), (y0, y1) = ranges
    units = ((x1 - x0) / _PLOT_W_PX, (y1 - y0) / _PLOT_H_PX)
    marker_half = (10 * units[0], 10 * units[1])
    markers = {
        node_id: (x - marker_half[0], y - marker_half[1], x + marker_half[0], y + marker_half[1])
        for node_id, (x, y) in positions.items()
    }
    placed: list[tuple[float, float, float, float]] = []
    result: dict[str, str] = {}
    candidates = ("top center", "bottom center", "middle right", "middle left")
    # Place the most crowded hubs first so they get first pick.
    def crowding(node_id: str) -> float:
        x, y = positions[node_id]
        return -sum(1.0 / (1e-6 + math.hypot(x - ox, y - oy)) for other, (ox, oy) in positions.items() if other != node_id)

    for node_id in sorted(labels, key=crowding):
        best_where, best_cost = candidates[0], float("inf")
        for rank, where in enumerate(candidates):
            box = _label_box(positions[node_id], labels[node_id], where, units)
            cost = rank * 1e-6  # tie-break: prefer the earlier candidate
            cost += sum(_overlap_area(box, other) for other in placed) * 4
            cost += sum(_overlap_area(box, m) for other, m in markers.items() if other != node_id) * 6
            cost += links_crossed(box) * 0.0015
            spill = max(0.0, x0 - box[0]) + max(0.0, box[2] - x1) + max(0.0, y0 - box[1]) + max(0.0, box[3] - y1)
            cost += spill * 2.0   # labels must stay inside the chart
            if cost < best_cost:
                best_where, best_cost = where, cost
        result[node_id] = best_where
        placed.append(_label_box(positions[node_id], labels[node_id], best_where, units))
    return result


def _ranges(positions: dict[str, Position]) -> tuple[tuple[float, float], tuple[float, float]]:
    xs = [p[0] for p in positions.values()] or [0.0, 1.0]
    ys = [p[1] for p in positions.values()] or [0.0, 1.0]
    pad_x = 0.13 * max(1e-6, max(xs) - min(xs))
    pad_y = 0.16 * max(1e-6, max(ys) - min(ys))
    return (min(xs) - pad_x, max(xs) + pad_x), (min(ys) - pad_y, max(ys) + pad_y)


# --------------------------------------------------------------------------
# Ornament: compass rose (drawn behind the network, top-right)
# --------------------------------------------------------------------------

def _compass_rose_uri() -> str:
    points = []
    for angle, length, dark in ((0, 44, True), (90, 34, False), (180, 34, False), (270, 34, False)):
        half_a = f"M0 {-length} L6 -6 L0 0 Z"
        half_b = f"M0 {-length} L-6 -6 L0 0 Z"
        fill_a = INK if dark else SEPIA
        points.append(
            f"<g transform='rotate({angle})'>"
            f"<path d='{half_a}' fill='{fill_a}'/>"
            f"<path d='{half_b}' fill='{VELLUM}' stroke='{fill_a}' stroke-width='0.8'/></g>"
        )
    for angle in (45, 135, 225, 315):
        points.append(
            f"<g transform='rotate({angle})'><path d='M0 -22 L3.5 -3.5 L0 0 L-3.5 -3.5 Z' "
            f"fill='{VELLUM}' stroke='{LINE}' stroke-width='0.7'/></g>"
        )
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='-60 -64 120 120'>"
        f"<circle r='30' fill='none' stroke='{GILT}' stroke-width='1.2'/>"
        f"<circle r='25' fill='none' stroke='{GILT}' stroke-width='0.7' stroke-dasharray='1.5 2.5'/>"
        + "".join(points)
        + f"<circle r='2.5' fill='{GILT}'/>"
        f"<text y='-49' text-anchor='middle' font-family='Georgia, serif' font-size='12' fill='{INK}'>N</text>"
        "</svg>"
    )
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


_COMPASS_URI = _compass_rose_uri()


# --------------------------------------------------------------------------
# Route chart
# --------------------------------------------------------------------------

def _segments(pairs: Iterable[tuple[Position, Position]]) -> tuple[list, list]:
    xs: list[float | None] = []
    ys: list[float | None] = []
    for (ax, ay), (bx, by) in pairs:
        xs += [ax, bx, None]
        ys += [ay, by, None]
    return xs, ys


def _no_dimming() -> dict:
    """Stop Plotly fading every other point once something is clicked."""
    return {"selected": {"marker": {"opacity": 1}}, "unselected": {"marker": {"opacity": 1}}}


def build_route_figure(
    network: RouteNetwork,
    positions: dict[str, Position],
    route: RouteResult | None,
    closed_nodes: set[str],
    closed_edges: set[str],
    origin: str,
    destination: str,
    inspected: tuple[str, str] | None = None,
    baseline_route: RouteResult | None = None,
    height: int | None = None,
) -> go.Figure:
    """Draw the network with the found route gilded and closures in claret.

    ``baseline_route`` is the route before the closures; when given, it is drawn
    as a faded long-dashed line under the current route (the before/after view).
    """
    fig = go.Figure()
    large = len(network.nodes) > 16   # bigger networks: lighter links, fewer labels
    cost_unit = "/t" if "tonne" in str(network.metadata.get("cost_unit", "")).lower() else ""
    capacity_unit = "t/week" if "week" in str(network.metadata.get("capacity_unit", "")).lower() else "t"
    risk_max = 5 if str(network.metadata.get("risk_scale", "")).startswith("1") else 10
    route_edges = set(route.edge_path) if route and route.success else set()
    route_nodes = set(route.node_path) if route and route.success else set()

    def edge_closed(edge_id: str) -> bool:
        edge = network.edges[edge_id]
        return edge_id in closed_edges or edge.source in closed_nodes or edge.target in closed_nodes

    # 1. Unused open links, one trace per transport mode (pattern = mode).
    by_mode: dict[str, list[tuple[Position, Position]]] = {}
    for edge_id, edge in network.edges.items():
        if edge_id in route_edges or edge_closed(edge_id):
            continue
        by_mode.setdefault(mode_key(edge.mode), []).append((positions[edge.source], positions[edge.target]))
    for mode, pairs in by_mode.items():
        xs, ys = _segments(pairs)
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", hoverinfo="skip", showlegend=False,
            line={"color": LINE, "width": 1.2 if large else 1.7, "dash": MODE_DASH.get(mode, "solid")},
            opacity=0.6 if large else 1.0,
        ))

    # 2. Closed links.
    closed_pairs = [
        (positions[e.source], positions[e.target])
        for e_id, e in network.edges.items() if edge_closed(e_id)
    ]
    if closed_pairs:
        xs, ys = _segments(closed_pairs)
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", hoverinfo="skip", showlegend=False,
            line={"color": CLARET, "width": 2.0, "dash": "dot"}, opacity=0.85,
        ))

    # 3a. The route before the closures, faded and long-dashed, under the current route.
    if baseline_route is not None and baseline_route.success:
        before_pairs = [(positions[a], positions[b]) for a, b in zip(baseline_route.node_path, baseline_route.node_path[1:])]
        xs, ys = _segments(before_pairs)
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", name="before", hoverinfo="skip", showlegend=False,
            line={"color": INK, "width": 3.4, "dash": "longdash"}, opacity=0.45,
        ))

    # 3b. The route: a gilt casing under a bottle-green line, plus direction arrows.
    if route_edges:
        ordered = list(zip(route.node_path, route.node_path[1:]))
        pairs = [(positions[a], positions[b]) for a, b in ordered]
        xs, ys = _segments(pairs)
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", hoverinfo="skip", showlegend=False,
            line={"color": GILT, "width": 11}, opacity=0.55,
        ))
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", hoverinfo="skip", showlegend=False,
            line={"color": GREEN, "width": 4.2},
        ))
        for (ax, ay), (bx, by) in pairs:
            fig.add_annotation(
                x=ax + (bx - ax) * 0.64, y=ay + (by - ay) * 0.64,
                ax=ax + (bx - ax) * 0.52, ay=ay + (by - ay) * 0.52,
                xref="x", yref="y", axref="x", ayref="y", text="",
                showarrow=True, arrowhead=2, arrowsize=1.15, arrowwidth=2.2, arrowcolor=GREEN,
            )

    # 4. Link handles: a small diamond at the middle of every link. Clicking it
    #    selects the link; hovering shows its synthetic attributes.
    handle_x, handle_y, handle_data = [], [], []
    handle_symbol, handle_color, handle_line, handle_size = [], [], [], []
    for edge_id, edge in network.edges.items():
        (ax, ay), (bx, by) = positions[edge.source], positions[edge.target]
        handle_x.append((ax + bx) / 2)
        handle_y.append((ay + by) / 2)
        closed = edge_closed(edge_id)
        on_route = edge_id in route_edges
        status = "Closed" if closed else ("On the route" if on_route else "Open")
        handle_data.append([
            "edge", edge_id,
            network.nodes[edge.source].name, network.nodes[edge.target].name,
            mode_name(edge.mode), f"{edge.time_hours:.1f}", f"{edge.cost_usd:,.0f}{cost_unit}",
            f"{edge.risk_score:g}", f"{edge.capacity_tonnes:g} {capacity_unit}", status, edge_id,
        ])
        if closed:
            handle_symbol.append("x"); handle_color.append(CLARET); handle_line.append(CLARET); handle_size.append(12)
        elif on_route:
            handle_symbol.append("diamond"); handle_color.append(GREEN); handle_line.append(GILT); handle_size.append(12)
        else:
            handle_symbol.append("diamond"); handle_color.append(VELLUM); handle_line.append(SEPIA); handle_size.append(7 if large else 10)
    fig.add_trace(go.Scatter(
        x=handle_x, y=handle_y, mode="markers", showlegend=False, customdata=handle_data,
        marker={"symbol": handle_symbol, "size": handle_size, "color": handle_color,
                "line": {"color": handle_line, "width": 1.4}},
        hovertemplate=(
            "<b>%{customdata[10]}: %{customdata[2]}</b> to <b>%{customdata[3]}</b><br>"
            "%{customdata[4]}: %{customdata[5]} h, $%{customdata[6]}<br>"
            "Risk %{customdata[7]} of " + str(risk_max) + ", capacity %{customdata[8]}<br>"
            "<i>%{customdata[9]}. Click to inspect.</i><extra></extra>"
        ),
        **_no_dimming(),
    ))

    # 5. Hubs. Open and closed hubs are separate traces so each keeps its own
    #    label colour after a click.
    xr, yr = _ranges(positions)
    labels = {node_id: chart_label(node.name) for node_id, node in network.nodes.items()}
    if large:   # label only the hubs that matter right now; hovering shows any hub's name
        keep = {origin, destination} | route_nodes | set(closed_nodes)
        if baseline_route is not None and baseline_route.success:
            keep |= set(baseline_route.node_path)
        if inspected and inspected[0] == "node":
            keep.add(inspected[1])
        labels = {node_id: text for node_id, text in labels.items() if node_id in keep}
    all_segments = [(positions[e.source], positions[e.target]) for e in network.edges.values()]
    label_positions = place_labels(positions, labels, (xr, yr), all_segments)

    symbol_by_type = {"airport": "triangle-up", "port": "diamond", "staging": "square", "border": "hexagon"}
    for closed_group in (False, True):
        ids = [n for n in network.nodes if (n in closed_nodes) == closed_group]
        if not ids:
            continue
        symbols, sizes, fills, outlines, widths, data = [], [], [], [], [], []
        for node_id in ids:
            node = network.nodes[node_id]
            if closed_group:
                symbols.append("circle"); sizes.append(17); fills.append(CLARET); outlines.append("#4A111A"); widths.append(1.5)
                status = "Closed"
            elif node_id == origin:
                symbols.append("circle"); sizes.append(22); fills.append(GREEN); outlines.append(GILT); widths.append(3)
                status = "Origin"
            elif node_id == destination:
                symbols.append("star"); sizes.append(28); fills.append(GILT); outlines.append(INK); widths.append(1.2)
                status = "Destination"
            else:
                symbols.append(symbol_by_type.get(node.node_type, "circle"))
                sizes.append(16 if node.node_type == "airport" else 15)
                fills.append(VELLUM)
                on_route = node_id in route_nodes
                outlines.append(GREEN if on_route else SEPIA)
                widths.append(3 if on_route else 1.5)
                status = "On the route" if on_route else "Open"
            data.append(["node", node_id, node.name, node_type_name(node.node_type), node.region, status])
        fig.add_trace(go.Scatter(
            x=[positions[n][0] for n in ids], y=[positions[n][1] for n in ids],
            mode="markers", showlegend=False, customdata=data,
            marker={"symbol": symbols, "size": sizes, "color": fills, "line": {"color": outlines, "width": widths}},
            hovertemplate=(
                "<b>%{customdata[2]}</b><br>%{customdata[3]}, %{customdata[4]}<br>"
                "<i>%{customdata[5]}. Click to inspect.</i><extra></extra>"
            ),
            **_no_dimming(),
        ))
        if closed_group:  # a pale cross on each closed hub; same customdata so clicks still work
            fig.add_trace(go.Scatter(
                x=[positions[n][0] for n in ids], y=[positions[n][1] for n in ids],
                mode="markers", showlegend=False, customdata=data, hoverinfo="skip",
                marker={"symbol": "x", "size": 8, "color": VELLUM, "line": {"width": 0}},
                **_no_dimming(),
            ))

    # Labels as annotations on a vellum ground, so links never strike through them.
    anchors = {
        "top center": {"xanchor": "center", "yanchor": "bottom", "yshift": 11},
        "bottom center": {"xanchor": "center", "yanchor": "top", "yshift": -11},
        "middle right": {"xanchor": "left", "yanchor": "middle", "xshift": 12},
        "middle left": {"xanchor": "right", "yanchor": "middle", "xshift": -12},
    }
    for node_id in labels:
        x, y = positions[node_id]
        fig.add_annotation(
            x=x, y=y, text=labels[node_id], showarrow=False, align="center",
            font={"family": FONT, "size": _FONT_PX, "color": CLARET if node_id in closed_nodes else INK},
            bgcolor="rgba(246, 238, 218, 0.88)", borderpad=1,
            **anchors[label_positions[node_id]],
        )

    # 6. A gilt ring around whatever the inspector is showing.
    if inspected:
        kind, item_id = inspected
        ring = None
        if kind == "node" and item_id in positions:
            ring, ring_size = positions[item_id], 38
        elif kind == "edge" and item_id in network.edges:
            edge = network.edges[item_id]
            (ax, ay), (bx, by) = positions[edge.source], positions[edge.target]
            ring, ring_size = ((ax + bx) / 2, (ay + by) / 2), 26
        if ring:
            fig.add_trace(go.Scatter(
                x=[ring[0]], y=[ring[1]], mode="markers", hoverinfo="skip", showlegend=False,
                marker={"symbol": "circle-open", "size": ring_size, "color": GILT, "line": {"width": 2.5}},
                **_no_dimming(),
            ))

    fig.update_layout(
        template="none",
        height=height or (600 if large else 520),
        margin={"l": 6, "r": 6, "t": 6, "b": 6},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        dragmode=False,
        hovermode="closest",
        font={"family": FONT, "color": INK, "size": 13},
        hoverlabel={"bgcolor": VELLUM, "bordercolor": GILT, "font": {"family": FONT, "color": INK, "size": 13}},
        xaxis={"visible": False, "fixedrange": True, "range": list(xr)},
        yaxis={"visible": False, "fixedrange": True, "range": list(yr)},
        images=[{
            "source": _COMPASS_URI, "xref": "paper", "yref": "paper",
            "x": 0.985, "y": 0.985, "sizex": 0.13, "sizey": 0.2,
            "xanchor": "right", "yanchor": "top", "layer": "below", "opacity": 0.9,
        }],
    )
    return fig


# --------------------------------------------------------------------------
# Algorithm comparison bars
# --------------------------------------------------------------------------

def build_expansion_figure(results: list[RouteResult]) -> go.Figure:
    """Horizontal bars of states expanded per algorithm (smaller is less work)."""
    colours = {"Dijkstra": SEPIA, "A*": GREEN, "Hierarchical": GILT}
    names = [r.algorithm for r in results][::-1]
    values = [r.nodes_expanded for r in results][::-1]
    fig = go.Figure(go.Bar(
        x=values, y=names, orientation="h",
        marker={"color": [colours.get(n, LINE) for n in names], "line": {"color": INK, "width": 0.8}},
        text=[f"{v} states" for v in values], textposition="outside", cliponaxis=False,
        textfont={"family": FONT, "color": INK, "size": 13},
        hovertemplate="%{y}: %{x} states expanded<extra></extra>",
    ))
    top = max(values or [1])
    fig.update_layout(
        template="none", height=200, margin={"l": 104, "r": 76, "t": 4, "b": 40},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", dragmode=False,
        font={"family": FONT, "color": INK, "size": 13}, bargap=0.38,
        xaxis={"range": [0, top * 1.22 + 1], "fixedrange": True, "gridcolor": "rgba(140,122,98,0.25)",
               "zeroline": False, "tickfont": {"color": SEPIA}, "title": {"text": "States expanded", "font": {"color": SEPIA, "size": 12}}},
        yaxis={"fixedrange": True, "tickfont": {"size": 14, "color": INK}, "automargin": True, "ticksuffix": "  "},
        hoverlabel={"bgcolor": VELLUM, "bordercolor": GILT, "font": {"family": FONT, "color": INK}},
    )
    return fig

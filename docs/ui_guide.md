# Front-end guide

How the Streamlit interface works, for the report and the viva. The front end
only calls the public functions in `humanitarian_route_planner`; it never
changes how routes are computed.

## Files

| File | Job |
|---|---|
| `app.py` | Page layout: sidebar controls, summary, chart, inspector, tabs. Solves the request on every run. |
| `ui/state.py` | Session-state defaults and callbacks: presets, scenarios, close/reopen, chart clicks. |
| `ui/chart.py` | Plotly route chart: schematic layout, label placement, clickable hubs and links. |
| `ui/components.py` | HTML blocks: masthead, summary, journey strip, inspector, key, ledgers. |
| `ui/theme.css`, `ui/theme.py` | Victorian theme: parchment, green sidebar, gilt frames. |
| `ui/sequence.py`, `static/sequence/` | Scroll-driven opening: globe frames drawn on a canvas as you scroll. |
| `ui/palette.py` | Colours, fonts and transport-mode line patterns shared by all of the above. |
| `.streamlit/config.toml` | Streamlit theme colours and the bundled fonts in `static/fonts/`. |

## Why there is no "run" button

Streamlit reruns `app.py` from top to bottom after every interaction. Dijkstra,
A* and hierarchical search solve this 23-hub network in about a
millisecond, so the app simply re-solves on every rerun. Whatever is on screen
always matches the current settings.

## How one click updates several widgets

Every setting lives in `st.session_state` under a fixed key (`origin`,
`w_time`, `closed_nodes`, ...), and each widget is created with that key.
Callbacks run *before* the rerun, which is the one moment Streamlit allows code
to change a widget's value. So:

- a preset button sets all three weight sliders (`apply_preset`);
- moving a slider highlights the matching preset, or none (`sync_preset_from_weights`);
- picking a scenario fills both closure lists (`apply_scenario`);
- the inspector's buttons add or remove a hub or link from those lists (`toggle_node`, `toggle_edge`).

## How a chart click becomes the inspector

Every hub and link handle carries `customdata = ["node" | "edge", id, ...]`.
The chart is drawn with `on_select="rerun"`, so a click reruns the script and
Streamlit stores the clicked point, customdata included, in
`st.session_state["route_chart"]`. At the top of the next run,
`consume_chart_selection()` reads it and sets `inspected`. It runs before the
chart is drawn, so the gilt ring appears around the clicked item in the same
run. Plotly keeps the selection between reruns, so the last handled click is
remembered and not processed twice.

## The schematic layout

`schematic_positions()` starts from each hub's longitude and latitude
(longitude shrunk by cos(mean latitude)), stretches the vertical axis, then
repeatedly pushes apart any two hubs closer than a minimum gap. It is
deterministic and keeps west on the left and east on the right, but distances
on screen are not to scale. No basemap is drawn, so the chart never suggests a
real corridor exists.

`place_labels()` tries each label above, below, right and left of its hub and
keeps the position with the least overlap with other labels, other hubs and
links. Labels sit on a vellum background so lines never cross the text.

## The "what the closures cost" line

After solving with the current closures, the app runs A* once more with
everything open (the baseline) and reports the difference in time, cost and
risk. If the route is unchanged, it says so.

## The opening sequence

The globe is a 10-second video made with Gemini, split into 120 frames by
`scripts/make_sequence.py`. The opening section is 2.5 screens tall and holds
a "sticky" stage that stays pinned while the section scrolls past. A small
script (in `ui/sequence.py`) works out how far you have scrolled into the
section and draws the matching frame on a canvas:

    progress = distance scrolled into the section / (section height - screen height)
    frame    = round(progress * 119)

The same progress value fades the title out and the three cards in and out.
Frames are cached in the browser, so Streamlit reruns don't download them
again. With "reduce motion" switched on in the operating system, the opening
shows a single still frame. If the frames are missing, the app falls back to
the plain title.

## Scenarios and the before/after view

The scenario list comes from the network file. Picking one fills the closure
lists with the legs it closes (you can still edit them), and the app runs the
network with that scenario's slower or dearer legs
(`RouteNetwork.with_adjustments`). Under any disruption the app solves the same
request twice with the same algorithm: under normal conditions (before) and
disrupted (after). The before route is drawn as a faded long-dashed line under
the current route, and a table compares legs, transfers, time, cost, risk and
nodes explored, next to the reroute the data expects for that scenario.

## Transfers on screen

When a route changes mode at a hub without its own transfer leg, the journey
strip marks the stop with "+ transfer", the leg-by-leg plan lists the transfer
as its own row, and the totals include it. The chart labels only the hubs that
matter (origin, destination, routes, closed and inspected hubs); hover over any
hub to see its name.

## Design choices

- **Colour has one job each.** Green means the route or open, claret means closed, gilt is ornament only, sepia is inactive.
- **Modes are told apart by line pattern**, not colour (air dotted, sea dashed, road solid), so the chart works for colour-blind viewers. The key and journey strip use the same dash lengths as the chart.
- **Fonts are bundled** (Abril Fatface for the title, Libre Caslon Text for everything else, both under the SIL Open Font Licence), so the demo works without internet.

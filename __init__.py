"""Dubai Humanitarian Route Planner: CSCI218 Project B, UOWD, Autumn 2026.

An educational prototype that compares Dijkstra, A* and hierarchical search on
a relief network from Dubai to El Obeid in Sudan, and shows how closures,
slow-downs and cost shocks change the route. The network data was provided by
Dubai Humanitarian.

Where things live:
    humanitarian_route_planner/     core models, network, algorithms
    app.py, ui/, static/            Streamlit front end and opening sequence
    data/                           the network (spreadsheet and the app's JSON)
    scripts/                        data import, benchmarks, opening frames
    tests/                          unit and app tests

See README.md for setup, usage and the data.
"""

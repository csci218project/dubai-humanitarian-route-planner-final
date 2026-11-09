"""Dubai Humanitarian Route Planner: CSCI218 Project B, UOWD, Autumn 2026.

An educational prototype that compares Dijkstra, A* and hierarchical search on
a small synthetic multimodal logistics network, and shows how closing an
airport, port, hub or corridor changes the route. All data is synthetic.

Where things live:
    humanitarian_route_planner/    core models, network, algorithms, scenarios
    app.py, ui/, static/           Streamlit front end and opening sequence (Arwin)
    build_network.py               CSV-to-JSON network builder (Shahir)
    search.py                      BFS, Greedy best-first, Weighted A* (Koushik)
    heuristics.py                  heuristic checks and risk model (Mohammed)
    synthetic.py, experiments.py   synthetic networks and experiments (Shreya)

See README.md for setup, usage and who owns what.
"""

"""Build a network JSON file from two spreadsheets (CSV): hubs and links.

Owner: Shahir.

Usage (from the repository root):
    python -m team.shahir_network.build_network team/shahir_network/hubs_template.csv team/shahir_network/links_template.csv data/extended_network.json

The columns are the same fields as data/sample_network.json, so the app can
load the result directly.
"""

from __future__ import annotations

import sys
from pathlib import Path

from humanitarian_route_planner.models import Edge, Node
from humanitarian_route_planner.network import RouteNetwork

HUB_COLUMNS = ["node_id", "name", "latitude", "longitude", "region", "node_type", "description"]
LINK_COLUMNS = ["edge_id", "source", "target", "mode", "time_hours", "cost_usd",
                "risk_score", "capacity_tonnes", "notes"]


def read_hubs(path: Path) -> list[Node]:
    """One Node per row, with latitude and longitude as floats (use csv.DictReader)."""
    raise NotImplementedError("Shahir: read_hubs is not written yet")


def read_links(path: Path) -> list[Edge]:
    """One Edge per row, with the number columns converted to float."""
    raise NotImplementedError("Shahir: read_links is not written yet")


def build_network(hubs_csv: Path, links_csv: Path, metadata: dict | None = None) -> RouteNetwork:
    """Read both files and return a RouteNetwork (its constructor checks the data)."""
    raise NotImplementedError("Shahir: build_network is not written yet")


def write_network_json(network: RouteNetwork, path: Path, metadata: dict) -> None:
    """Write {"metadata": ..., "nodes": [...], "edges": [...]} like data/sample_network.json.

    Keep a metadata disclaimer saying the values are illustrative.
    """
    raise NotImplementedError("Shahir: write_network_json is not written yet")


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 3:
        raise SystemExit("Usage: python -m team.shahir_network.build_network HUBS.csv LINKS.csv OUTPUT.json")
    raise NotImplementedError("Shahir: main is not written yet")


if __name__ == "__main__":
    main()

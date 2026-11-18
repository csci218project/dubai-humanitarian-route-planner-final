"""Convert data/hrp_network_data.xlsx into data/hrp_network.json, the file the app loads.

Usage (from the repository root):
    pip install -r requirements-dev.txt
    python scripts/import_hrp_data.py

The spreadsheet has three sheets:
- locations: the hubs (origin, airports, ports, border crossings, destination)
- network_legs: one-way legs with typical and slow-case (p90) transit time,
  cost per tonne, weekly capacity, a 1-5 risk score and a reliability %
- disruption_scenarios: closures (CLOSE), slow-downs (TIME_MULT), cost shocks
  (COST_MULT) and combinations of other scenarios (COMBINE)

Rerun this script whenever the spreadsheet changes; the app only reads the JSON.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "hrp_network_data.xlsx"
OUTPUT = ROOT / "data" / "hrp_network.json"

MODES = {"Air": "air", "Sea": "sea", "Road": "road", "Road (transfer)": "transfer"}
NODE_TYPES = {"Airport": "airport", "Seaport": "port", "Hub": "hub", "Border crossing": "border",
              "Warehouse": "origin", "Destination": "destination"}


def text(value: object) -> str:
    return "" if pd.isna(value) else str(value).strip()


def build(source: Path = SOURCE) -> dict:
    sheets = pd.read_excel(source, sheet_name=None)
    locations, legs, scenarios = sheets["locations"], sheets["network_legs"], sheets["disruption_scenarios"]

    nodes = []
    for row in locations.itertuples(index=False):
        node_type = NODE_TYPES[row.node_type]
        if text(row.role) == "Origin":
            node_type = "origin"
        nodes.append({
            "node_id": row.node_id, "name": row.name,
            "latitude": float(row.lat), "longitude": float(row.lon),
            "region": row.country,   # countries are the regions for hierarchical search
            "node_type": node_type,
            "description": f"{text(row.role)}. Modes served: {text(row.modes_served).replace(';', ', ')}.",
        })

    edges = []
    for row in legs.itertuples(index=False):
        notes = text(row.notes)
        frequency = text(row.restriction_frequency)
        edges.append({
            "edge_id": row.leg_id, "source": row.from_node, "target": row.to_node,
            "mode": MODES[row.mode],
            "time_hours": float(row.transit_hours_typical),
            "cost_usd": float(row.cost_usd_per_tonne),
            "risk_score": float(row.risk_score_1to5),
            "capacity_tonnes": float(row.capacity_tonnes_per_week),
            "notes": f"{notes}. Restrictions: {frequency.lower()}." if frequency else notes,
            "time_hours_p90": float(row.transit_hours_p90),
            "reliability_pct": float(row.reliability_pct),
            "distance_km": float(row.distance_km),
            "corridor": text(row.corridor_group),
        })

    # A mode change at a hub with no transfer leg of its own costs a typical transfer:
    # the median of the data's own transfer legs.
    transfer_legs = [e for e in edges if e["mode"] == "transfer"]
    transfer = {
        "time_hours": statistics.median(e["time_hours"] for e in transfer_legs),
        "cost_usd": statistics.median(e["cost_usd"] for e in transfer_legs),
        "risk_score": statistics.median(e["risk_score"] for e in transfer_legs),
        "basis": f"Median of the {len(transfer_legs)} transfer legs in the data",
    }

    specs: dict[str, dict] = {}
    for row in scenarios.itertuples(index=False):
        spec = specs.setdefault(row.scenario_id, {
            "id": row.scenario_id, "name": text(row.scenario_name),
            "label": f"{row.scenario_id}: {text(row.scenario_name)}",
            "type": text(row.disruption_type), "trigger": text(row.example_trigger),
            "duration_days": int(row.expected_duration_days), "expected_reroute": text(row.typical_reroute),
            "close_edges": [], "time_mult": {}, "cost_mult": {}, "combine": [],
        })
        action = text(row.action)
        if action == "CLOSE":
            spec["close_edges"].append(text(row.leg_id))
        elif action in ("TIME_MULT", "COST_MULT"):
            spec["time_mult" if action == "TIME_MULT" else "cost_mult"][text(row.leg_id)] = float(row.value)
        elif action == "COMBINE":
            spec["combine"] = [part.strip() for part in text(row.value).split(";") if part.strip()]
    for spec in specs.values():   # resolve combinations into one set of changes
        for part in spec.pop("combine"):
            other = specs[part]
            spec["close_edges"] += other["close_edges"]
            for key in ("time_mult", "cost_mult"):
                for leg, factor in other[key].items():
                    spec[key][leg] = spec[key].get(leg, 1.0) * factor
        spec["close_edges"] = sorted(set(spec["close_edges"]))

    roles = {row.node_id: text(row.role) for row in locations.itertuples(index=False)}
    metadata = {
        "title": f"Dubai to El Obeid relief network ({len(nodes)} hubs, {len(edges)} legs)",
        "version": "hrp-1",
        "directed": True,
        "default_origin": next(n for n, role in roles.items() if role == "Origin"),
        "default_destination": next(n for n, role in roles.items() if role == "Destination"),
        "alternative_destinations": [n for n, role in roles.items() if role == "Alternative destination"],
        "cost_unit": "USD per tonne",
        "capacity_unit": "tonnes per week",
        "risk_scale": "1 (low) to 5 (high), ordinal",
        "transfer": transfer,
        "data_status": "Illustrative network compiled by the project team.",
        "disclaimer": (
            "Illustrative network compiled by the project team from public information. Locations are real; "
            "transit times, costs, risk scores and reliability are planning estimates for algorithm "
            "demonstrations, not official Dubai Humanitarian data, schedules or security assessments. "
            "Do not use it to plan real aid movements."
        ),
        "source_file": source.name,
        "scenarios": list(specs.values()),
    }
    return {"metadata": metadata, "nodes": nodes, "edges": edges}


def main() -> None:
    payload = build()
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    meta = payload["metadata"]
    print(f"Wrote {OUTPUT.relative_to(ROOT)}: {len(payload['nodes'])} hubs, {len(payload['edges'])} legs, "
          f"{len(meta['scenarios'])} scenarios; transfer = {meta['transfer']['time_hours']} h, "
          f"${meta['transfer']['cost_usd']}/t")


if __name__ == "__main__":
    main()

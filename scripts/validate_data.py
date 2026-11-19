"""Check Dubai Humanitarian's spreadsheet before it is imported into the app.

Usage (from the repository root; reading .xlsx needs openpyxl, in requirements-dev.txt):
    python scripts/validate_data.py
    python scripts/validate_data.py --file data/hrp_network_data.xlsx

Prints PASS or FAIL for each check and exits with code 1 if any check fails, so
bad data is caught before scripts/import_hrp_data.py writes the app's JSON file.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FILE = ROOT / "data" / "hrp_network_data.xlsx"

# Columns each sheet must have, and the ones that may never be empty.
COLUMNS = {
    "locations": ["node_id", "name", "node_type", "country", "lat", "lon", "role", "legs_out", "legs_in"],
    "network_legs": ["leg_id", "from_node", "from_name", "to_node", "to_name", "mode", "distance_km",
                     "transit_hours_typical", "transit_hours_p90", "cost_usd_per_tonne",
                     "capacity_tonnes_per_week", "risk_score_1to5", "reliability_pct"],
    "disruption_scenarios": ["scenario_id", "scenario_name", "leg_id", "action", "value", "typical_reroute"],
}
NEVER_EMPTY = {
    "locations": ["node_id", "name", "node_type", "country", "lat", "lon", "role"],
    "network_legs": COLUMNS["network_legs"],
    "disruption_scenarios": ["scenario_id", "scenario_name"],
}
MODES = {"Air", "Sea", "Road", "Road (transfer)"}
ACTIONS = {"CLOSE", "TIME_MULT", "COST_MULT", "COMBINE"}

Check = tuple[str, list[str]]   # (what was checked, problems found; empty means it passed)


def run_checks(sheets: dict[str, pd.DataFrame]) -> list[Check]:
    """Run every check on the three sheets and return what each one found."""
    missing = [f"{sheet}: {column}" for sheet, columns in COLUMNS.items() for column in columns
               if sheet not in sheets or column not in sheets[sheet].columns]
    checks: list[Check] = [("Sheets and columns are present", missing)]
    if missing:
        return checks   # the other checks need these columns

    locations, legs, scenarios = sheets["locations"], sheets["network_legs"], sheets["disruption_scenarios"]
    empty = [f"{sheet} row {index + 2}: {column}"   # +2: spreadsheet rows start at 1, after the header
             for sheet, columns in NEVER_EMPTY.items()
             for column in columns
             for index, value in sheets[sheet][column].items() if pd.isna(value)]
    checks.append(("No required value is empty", empty))

    checks.append(("Location IDs are unique",
                   [node for node, count in Counter(locations.node_id).items() if count > 1]))
    checks.append(("Leg IDs are unique", [leg for leg, count in Counter(legs.leg_id).items() if count > 1]))

    known = set(locations.node_id)
    checks.append(("Every leg starts and ends at a known location",
                   [f"{leg.leg_id}: {end}" for leg in legs.itertuples()
                    for end in (leg.from_node, leg.to_node) if end not in known]))
    checks.append(("No leg starts and ends at the same location",
                   [leg.leg_id for leg in legs.itertuples() if leg.from_node == leg.to_node]))

    names = dict(zip(locations.node_id, locations.name))
    checks.append(("Leg names match the locations sheet",
                   [leg.leg_id for leg in legs.itertuples()
                    if names.get(leg.from_node, leg.from_name) != leg.from_name
                    or names.get(leg.to_node, leg.to_name) != leg.to_name]))

    checks.append(("Modes are Air, Sea, Road or Road (transfer)",
                   [f"{leg.leg_id}: {leg.mode}" for leg in legs.itertuples() if leg.mode not in MODES]))

    out_of_range = []
    for leg in legs.itertuples():
        rules = [
            (leg.transit_hours_typical > 0, "typical time must be above 0"),
            (leg.transit_hours_p90 >= leg.transit_hours_typical, "p90 time is below the typical time"),
            (leg.cost_usd_per_tonne >= 0, "cost is negative"),
            (leg.capacity_tonnes_per_week > 0, "capacity must be above 0"),
            (1 <= leg.risk_score_1to5 <= 5, "risk must be 1 to 5"),
            (0 < leg.reliability_pct <= 100, "reliability must be above 0 and at most 100"),
            (leg.distance_km > 0, "distance must be above 0"),
        ]
        out_of_range += [f"{leg.leg_id}: {problem}" for ok, problem in rules if not ok]
    checks.append(("Times, costs, capacities, risk and reliability are in range", out_of_range))

    checks.append(("Coordinates are valid",
                   [place.node_id for place in locations.itertuples()
                    if not (-90 <= place.lat <= 90 and -180 <= place.lon <= 180)]))

    leaving, arriving = Counter(legs.from_node), Counter(legs.to_node)
    checks.append(("legs_out and legs_in match the legs sheet",
                   [place.node_id for place in locations.itertuples()
                    if place.legs_out != leaving[place.node_id] or place.legs_in != arriving[place.node_id]]))

    origins = locations[locations.role == "Origin"].node_id.tolist()
    destinations = locations[locations.role == "Destination"].node_id.tolist()
    roles_ok = len(origins) == 1 and len(destinations) == 1
    checks.append(("Exactly one origin and one destination",
                   [] if roles_ok else [f"origins: {origins}, destinations: {destinations}"]))

    unreachable: list[str] = []
    if len(origins) == 1:   # legs are one-way, so follow them from the origin
        next_stops: dict[str, list[str]] = {}
        for leg in legs.itertuples():
            next_stops.setdefault(leg.from_node, []).append(leg.to_node)
        seen, stack = {origins[0]}, [origins[0]]
        while stack:
            for stop in next_stops.get(stack.pop(), []):
                if stop not in seen:
                    seen.add(stop)
                    stack.append(stop)
        unreachable = sorted(known - seen)
    checks.append(("Every location can be reached from the origin", unreachable))

    leg_ids, scenario_ids = set(legs.leg_id), set(scenarios.scenario_id)
    bad_actions, unknown_legs, bad_values, bad_combines = [], [], [], []
    for row in scenarios.itertuples():
        label = f"{row.scenario_id} row {row.Index + 2}"
        if pd.isna(row.action):   # a baseline row changes nothing
            continue
        if row.action not in ACTIONS:
            bad_actions.append(f"{label}: {row.action}")
        elif row.action == "COMBINE":
            parts = [part.strip() for part in str(row.value).split(";") if part.strip()]
            bad_combines += [f"{label}: {part}" for part in parts if part not in scenario_ids]
        else:
            if row.leg_id not in leg_ids:
                unknown_legs.append(f"{label}: {row.leg_id}")
            if row.action != "CLOSE" and not (pd.notna(row.value) and float(row.value) > 0):
                bad_values.append(f"{label}: {row.value}")
    checks.append(("Scenario actions are CLOSE, TIME_MULT, COST_MULT or COMBINE", bad_actions))
    checks.append(("Scenarios only name known legs", unknown_legs))
    checks.append(("Slow-down and cost multipliers are positive numbers", bad_values))
    checks.append(("Combined scenarios only name known scenarios", bad_combines))
    return checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", default=str(DEFAULT_FILE), help="The spreadsheet to check.")
    args = parser.parse_args(argv)
    sheets = pd.read_excel(args.file, sheet_name=None)
    counts = {name: len(sheet) for name, sheet in sheets.items()}
    print(f"Checking {Path(args.file).name}: " + ", ".join(f"{rows} rows in {name}" for name, rows in counts.items()))
    checks = run_checks(sheets)
    for name, problems in checks:
        shown = "; ".join(problems[:5]) + (f" (and {len(problems) - 5} more)" if len(problems) > 5 else "")
        print(f"{'PASS' if not problems else 'FAIL'}  {name}" + (f": {shown}" if problems else ""))
    failed = sum(1 for _, problems in checks if problems)
    print(f"\n{len(checks) - failed} of {len(checks)} checks passed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

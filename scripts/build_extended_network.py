"""Build data/extended_network.json: the sample network plus real airports and ports.

Usage (from the repository root):
    pip install -r requirements-dev.txt
    python scripts/build_extended_network.py

What is real and what is assumed:
- Real: hub locations (OurAirports for airports, UN/LOCODE for ports), which
  airport pairs have a scheduled air route (OpenFlights route data), and sea
  distances along shipping lanes (the searoute package).
- Assumed: every link's time, cost, risk and capacity. Time and cost come from
  straight lines fitted to the sample network's own links, so new links are
  on the same scale as the original ones. Risk follows a fixed rule by mode and
  distance from the destination. All of it is illustrative.

The ten sample hubs and fifteen sample links are kept unchanged, and new hubs
reach the destination only through the sample's own corridor links.
"""

from __future__ import annotations

import csv
import io
import json
import math
import urllib.request
from pathlib import Path

import numpy as np
import searoute

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "sample_network.json"
OUTPUT = ROOT / "data" / "extended_network.json"

SOURCES = {
    "airports": "https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/airports.csv",
    "routes": "https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat",
    "locodes": "https://raw.githubusercontent.com/datasets/un-locode/main/data/code-list.csv",
}

# New airports (IATA codes). Airports next to a sample hub are served by that hub instead.
NEW_AIRPORTS = ["DXB", "SHJ", "MCT", "SLL", "DOH", "BAH", "KWI", "DMM", "MED", "TUU",
                "AMM", "HBE", "SSH", "HRG", "LCA"]
AIRPORT_AT_SAMPLE_HUB = {"DWC": "DWC_AIRPORT", "AUH": "ABU_DHABI_HUB", "RUH": "RIYADH_HUB",
                         "JED": "JEDDAH_HUB", "AQJ": "AQABA_HUB", "CAI": "CAIRO_HUB", "AAC": "EL_ARISH_HUB"}

# New ports: node id -> (UN/LOCODE country, location code, display name).
NEW_PORTS = {
    "KHALIFA_PORT": ("AE", "KHL", "Khalifa Port (Abu Dhabi)"),
    "FUJAIRAH_PORT": ("AE", "FJR", "Port of Fujairah"),
    "MUSCAT_PORT": ("OM", "STQ", "Port Sultan Qaboos (Muscat)"),
    "DUQM_PORT": ("OM", "DQM", "Port of Duqm"),
    "HAMAD_PORT": ("QA", "HMD", "Hamad Port (Qatar)"),
    "KBS_PORT": ("BH", "KBS", "Khalifa Bin Salman Port (Bahrain)"),
    "SHUWAIKH_PORT": ("KW", "SWK", "Shuwaikh Port (Kuwait)"),
    "DAMMAM_PORT": ("SA", "DMM", "King Abdulaziz Port (Dammam)"),
    "KING_ABDULLAH_PORT": ("SA", "KAC", "King Abdullah Port"),
    "YANBU_PORT": ("SA", "YNB", "Yanbu Commercial Port"),
    "PORT_SAID_PORT": ("EG", "PSE", "Port Said East Port"),
    "ALEXANDRIA_PORT": ("EG", "ALY", "Port of Alexandria"),
    "DAMIETTA_PORT": ("EG", "DAM", "Damietta Port"),
    "SOKHNA_PORT": ("EG", "SOK", "Sokhna Port"),
    "LIMASSOL_PORT": ("CY", "LMS", "Limassol Port"),
}
SAMPLE_PORTS = ["JEBEL_ALI_PORT", "JEDDAH_HUB", "AQABA_HUB"]   # sample hubs with sea access
SAMPLE_COUNTRY = {"DUBAI_HUB": "AE", "DWC_AIRPORT": "AE", "JEBEL_ALI_PORT": "AE", "ABU_DHABI_HUB": "AE",
                  "RIYADH_HUB": "SA", "JEDDAH_HUB": "SA", "CAIRO_HUB": "EG", "AQABA_HUB": "JO",
                  "EL_ARISH_HUB": "EG", "RELIEF_DESTINATION": "XX"}
# Countries joined by road (each country is also joined to itself).
LAND_NEIGHBOURS = {"AE": {"OM", "SA"}, "OM": {"AE", "SA"}, "SA": {"AE", "OM", "QA", "KW", "JO", "BH"},
                   "QA": {"SA"}, "KW": {"SA"}, "BH": {"SA"}, "JO": {"SA"}, "EG": set(), "CY": set()}

ROAD_CIRCUITY = 1.3        # road distance ~ 1.3 x straight-line distance
ROAD_MAX_KM = 900          # longest new road link (straight line)
MIN_AIR_KM = 250           # shorter trips go by road
NEIGHBOURS_PER_HUB = 3     # road and sea partners per hub
AIR_PARTNERS = 5           # nearest scheduled-route partners kept per airport
BASE_RISK = {"road": 1.5, "air": 2.0, "sea": 2.5}


def download(url: str) -> str:
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read().decode("utf-8", errors="ignore")


def km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance between (lat, lon) points."""
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def sea_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    return float(searoute.searoute([a[1], a[0]], [b[1], b[0]]).properties["length"])


def locode_position(text: str) -> tuple[float, float]:
    """'2450N 05440E' -> (24.833, 54.667)."""
    lat_part, lon_part = text.split()
    lat = int(lat_part[:2]) + int(lat_part[2:4]) / 60
    lon = int(lon_part[:3]) + int(lon_part[3:5]) / 60
    return (-lat if lat_part[-1] == "S" else lat, -lon if lon_part[-1] == "W" else lon)


def region_for(country: str, lat: float, lon: float) -> str:
    if country == "AE":
        return "UAE"
    if country in {"OM", "SA", "QA", "BH", "KW"}:
        return "Arabian Peninsula"
    if country == "JO":
        return "Levant"
    if country == "CY":
        return "Eastern Mediterranean"
    return "Sinai staging" if lat >= 27.7 and lon >= 32.6 else "North Africa"


def fit_line(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Least-squares y = a + b*x, with a kept non-negative."""
    b, a = np.polyfit(xs, ys, 1)
    if a < 0:
        a, b = 0.0, float(np.dot(xs, ys) / np.dot(xs, xs))
    return float(a), float(b)


def main() -> None:
    sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
    nodes = {n["node_id"]: dict(n) for n in sample["nodes"]}
    position = {i: (n["latitude"], n["longitude"]) for i, n in nodes.items()}
    country = dict(SAMPLE_COUNTRY)
    destination = sample["metadata"]["default_destination"]

    print("Downloading OurAirports, OpenFlights and UN/LOCODE data ...")
    airports = {r["iata_code"]: r for r in csv.DictReader(io.StringIO(download(SOURCES["airports"]))) if r["iata_code"]}
    locodes = {r["Country"] + r["Location"]: r for r in csv.DictReader(io.StringIO(download(SOURCES["locodes"])))}
    routes = download(SOURCES["routes"]).splitlines()

    # ---- hubs ---------------------------------------------------------------
    airport_node = dict(AIRPORT_AT_SAMPLE_HUB)
    for iata in NEW_AIRPORTS:
        row = airports[iata]
        node_id = f"{iata}_AIRPORT"
        lat, lon = round(float(row["latitude_deg"]), 3), round(float(row["longitude_deg"]), 3)
        nodes[node_id] = {
            "node_id": node_id, "name": f"{row['name']} ({iata})", "latitude": lat, "longitude": lon,
            "region": region_for(row["iso_country"], lat, lon), "node_type": "airport",
            "description": "Real airport location (OurAirports); link values are illustrative.",
        }
        position[node_id], country[node_id], airport_node[iata] = (lat, lon), row["iso_country"], node_id
    for node_id, (cc, loc, name) in NEW_PORTS.items():
        lat, lon = locode_position(locodes[cc + loc]["Coordinates"])
        lat, lon = round(lat, 3), round(lon, 3)
        nodes[node_id] = {
            "node_id": node_id, "name": name, "latitude": lat, "longitude": lon,
            "region": region_for(cc, lat, lon), "node_type": "port",
            "description": f"Real port location (UN/LOCODE {cc} {loc}); link values are illustrative.",
        }
        position[node_id], country[node_id] = (lat, lon), cc

    # ---- calibrate time and cost on the sample's own links -------------------
    sample_edges = sample["edges"]
    def length(edge: dict) -> float:
        a, b = position[edge["source"]], position[edge["target"]]
        if edge["mode"] == "sea":
            return sea_km(a, b)
        return km(a, b) * (ROAD_CIRCUITY if edge["mode"] == "road" else 1.0)
    models, capacity = {}, {}
    for mode in ("road", "air", "sea"):
        rows = [e for e in sample_edges if e["mode"] == mode]
        xs = [length(e) for e in rows]
        models[mode] = (fit_line(xs, [e["time_hours"] for e in rows]), fit_line(xs, [e["cost_usd"] for e in rows]))
        capacity[mode] = float(np.median([e["capacity_tonnes"] for e in rows]))
        (ta, tb), (ca, cb) = models[mode]
        print(f"{mode:>4}: time = {ta:.2f} h + {tb * 1000:.2f} h/1000 km; cost = ${ca:,.0f} + ${cb:.2f}/km "
              f"({len(rows)} sample links)")

    edges = [dict(e) for e in sample_edges]
    connected = {frozenset((e["source"], e["target"])) for e in edges}
    counter = {"n": 0}

    def add(a: str, b: str, mode: str, distance: float, note: str) -> None:
        (ta, tb), (ca, cb) = models[mode]
        near = min(km(position[a], position[destination]), km(position[b], position[destination]))
        risk = BASE_RISK[mode] + (2.0 if near < 250 else 1.0 if near < 600 else 0.0)
        counter["n"] += 1
        short = lambda node_id: node_id.replace("_AIRPORT", "").replace("_PORT", "").replace("_HUB", "")
        edges.append({
            "edge_id": f"X{counter['n']:03d}_{short(a)}_{short(b)}_{mode.upper()}",
            "source": a, "target": b, "mode": mode,
            "time_hours": round(ta + tb * distance, 1), "cost_usd": int(round((ca + cb * distance) / 10) * 10),
            "risk_score": round(min(10.0, risk) * 2) / 2, "capacity_tonnes": capacity[mode],
            "notes": note,
        })
        connected.add(frozenset((a, b)))

    hubs = [i for i in nodes if i != destination]

    # ---- road: nearest land-connected hubs -----------------------------------
    for a in hubs:
        reachable = [b for b in hubs if b != a and (country[b] == country[a] or country[b] in LAND_NEIGHBOURS.get(country[a], set()))]
        reachable = sorted((km(position[a], position[b]), b) for b in reachable)
        added = 0
        for straight, b in reachable:
            if straight > ROAD_MAX_KM or added >= NEIGHBOURS_PER_HUB:
                break
            if frozenset((a, b)) not in connected:
                add(a, b, "road", straight * ROAD_CIRCUITY,
                    "Illustrative road link; distance = 1.3 x straight line, time and cost fitted to the sample's road links.")
            added += 1

    # ---- air: airport pairs with a scheduled route in OpenFlights -------------
    partners: dict[str, set[str]] = {}
    for line in routes:
        parts = line.split(",")
        if len(parts) > 4 and parts[2] in airport_node and parts[4] in airport_node:
            a, b = airport_node[parts[2]], airport_node[parts[4]]
            if a != b:
                partners.setdefault(a, set()).add(b)
                partners.setdefault(b, set()).add(a)
    for a in sorted(partners):
        nearest = sorted((km(position[a], position[b]), b) for b in partners[a])
        kept = [(d, b) for d, b in nearest if d >= MIN_AIR_KM][:AIR_PARTNERS]
        for straight, b in kept:
            if frozenset((a, b)) not in connected:
                add(a, b, "air", straight,
                    "Illustrative air link between airports with a scheduled route in OpenFlights data; "
                    "time and cost fitted to the sample's air links.")

    # ---- sea: nearest ports along shipping lanes ------------------------------
    ports = SAMPLE_PORTS + list(NEW_PORTS)
    sea = {}
    for i, a in enumerate(ports):
        for b in ports[i + 1:]:
            sea[frozenset((a, b))] = sea_km(position[a], position[b])
    for a in ports:
        nearest = sorted((sea[frozenset((a, b))], b) for b in ports if b != a)
        added = 0
        for distance, b in nearest:
            if added >= NEIGHBOURS_PER_HUB:
                break
            if frozenset((a, b)) not in connected:
                add(a, b, "sea", distance,
                    "Illustrative sea link; distance along shipping lanes (searoute), time and cost fitted to the sample's sea links.")
                added += 1

    # ---- every hub must be reachable from the origin ---------------------------
    origin = sample["metadata"]["default_origin"]
    neighbours: dict[str, set[str]] = {}
    for e in edges:
        neighbours.setdefault(e["source"], set()).add(e["target"])
        neighbours.setdefault(e["target"], set()).add(e["source"])
    seen, stack = {origin}, [origin]
    while stack:
        for nxt in neighbours.get(stack.pop(), ()):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    missing = set(nodes) - seen
    if missing:
        raise SystemExit(f"Unreachable hubs: {sorted(missing)}")

    metadata = dict(sample["metadata"])
    metadata.update({
        "title": f"Extended illustrative network ({len(nodes)} hubs)",
        "version": "extended-1",
        "data_status": "Real hub locations and air-route pairs; all link values are synthetic.",
        "disclaimer": (
            "Hub locations come from OurAirports and UN/LOCODE, and air links follow scheduled-route pairs in "
            "OpenFlights data. Every time, cost, risk and capacity value is an illustrative assumption fitted to the "
            "sample network. No live schedules, permissions, security assessments or official Dubai Humanitarian "
            "data are included. Do not use this network to plan real aid movements."
        ),
        "sources": [
            {"name": "OurAirports", "url": "https://ourairports.com/data/", "licence": "Public domain"},
            {"name": "OpenFlights route data", "url": "https://openflights.org/data", "licence": "ODbL 1.0"},
            {"name": "UN/LOCODE", "url": "https://unece.org/trade/cefact/unlocode-code-list-country-and-territory", "licence": "UNECE, free use with attribution"},
            {"name": "searoute (sea distances)", "url": "https://pypi.org/project/searoute/", "licence": "Apache 2.0"},
        ],
    })
    OUTPUT.write_text(json.dumps({"metadata": metadata, "nodes": list(nodes.values()), "edges": edges}, indent=2,
                                 ensure_ascii=False) + "\n", encoding="utf-8")
    by_mode: dict[str, int] = {}
    for e in edges:
        by_mode[e["mode"]] = by_mode.get(e["mode"], 0) + 1
    print(f"Wrote {OUTPUT.relative_to(ROOT)}: {len(nodes)} hubs, {len(edges)} links {by_mode}")


if __name__ == "__main__":
    main()

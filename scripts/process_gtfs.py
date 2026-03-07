#!/usr/bin/env python3
"""
Process MTA GTFS data into the JSON format needed by the subway app.

Usage:
    # First download the GTFS data:
    curl -sL -o gtfs.zip "http://web.mta.info/developers/data/nyct/subway/google_transit.zip"
    mkdir -p gtfs_raw && unzip -o gtfs.zip -d gtfs_raw

    # Then run this script:
    python3 scripts/process_gtfs.py
"""

import csv
import json
import os
import re
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GTFS_DIR = os.path.join(SCRIPT_DIR, "..", "gtfs_raw")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "..", "data", "subway_data.json")
WIKI_BOROUGHS_FILE = os.path.join(SCRIPT_DIR, "wiki_boroughs.json")

# Official MTA line colors
LINE_COLORS = {
    "1": "#EE352E", "2": "#EE352E", "3": "#EE352E",
    "4": "#00933C", "5": "#00933C", "6": "#00933C",
    "7": "#B933AD",
    "A": "#0039A6", "C": "#0039A6", "E": "#0039A6",
    "B": "#FF6319", "D": "#FF6319", "F": "#FF6319", "M": "#FF6319",
    "G": "#6CBE45",
    "J": "#996633", "Z": "#996633",
    "L": "#A7A9AC",
    "N": "#FCCC0A", "Q": "#FCCC0A", "R": "#FCCC0A", "W": "#FCCC0A",
    "S": "#808183",
}

# The 24 standard subway lines (exclude SI, express variants like 6X/7X/FX, and shuttles FS/GS/H)
# Shuttles: FS = Franklin Ave, GS = 42 St, H = Rockaway Park
# We include S as a combined shuttle entry
STANDARD_LINES = {"1","2","3","4","5","6","7","A","B","C","D","E","F","G","J","L","M","N","Q","R","W","Z"}
SHUTTLE_ROUTES = {"GS", "FS", "H"}

# Borough mapping based on stop_id prefix ranges (from MTA documentation)
# This is approximate; we'll also use lat/lon as fallback
BOROUGH_BY_COORDS = {
    # (lat_min, lat_max, lon_min, lon_max, borough)
}


def read_csv(filename):
    filepath = os.path.join(GTFS_DIR, filename)
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def get_borough(lat, lon):
    """Determine borough from coordinates. Only called for subway stations
    (SI Railway is excluded), so we never return Staten Island."""
    lat, lon = float(lat), float(lon)

    # Bronx: generally north of ~40.8
    if lat > 40.82:
        return "Bronx"
    if lat > 40.8 and lon > -73.935:
        return "Bronx"

    # Queens: generally east, identified by longitude
    if lon > -73.86:
        return "Queens"
    # Northern Queens (Jackson Heights, Woodside, etc.) extends further west
    if lon > -73.91 and lat > 40.73 and lat < 40.77:
        return "Queens"
    if lon > -73.88 and lat < 40.77 and lat > 40.56:
        return "Queens"

    # Manhattan: the narrow island, bounded roughly by:
    # West: -74.02, East: -73.93 (varies), North: ~40.88, South: ~40.70
    if lat > 40.75 and lon > -74.02 and lon < -73.93:
        return "Manhattan"
    if lat > 40.705 and lat <= 40.75 and lon > -74.015 and lon < -73.965:
        return "Manhattan"

    # Everything else is Brooklyn
    return "Brooklyn"


def main():
    print("Reading GTFS files...")
    stops_raw = read_csv("stops.txt")
    trips_raw = read_csv("trips.txt")
    stop_times_raw = read_csv("stop_times.txt")
    routes_raw = read_csv("routes.txt")

    # Build parent station lookup: stop_id -> (stop_name, lat, lon)
    # Parent stations have location_type=1, child stops have parent_station set
    parent_stations = {}
    child_to_parent = {}
    for s in stops_raw:
        if s.get("location_type") == "1":
            parent_stations[s["stop_id"]] = {
                "name": s["stop_name"],
                "lat": s["stop_lat"],
                "lon": s["stop_lon"],
            }
        elif s.get("parent_station"):
            child_to_parent[s["stop_id"]] = s["parent_station"]

    print(f"Found {len(parent_stations)} parent stations")

    # Build trip -> route mapping
    trip_to_route = {}
    for t in trips_raw:
        route_id = t["route_id"]
        trip_to_route[t["trip_id"]] = {
            "route_id": route_id,
            "direction_id": t.get("direction_id", "0"),
            "shape_id": t.get("shape_id", ""),
        }

    # For each line, find the trip with the most stops to get the full stop sequence
    # Group stop_times by trip
    print("Processing stop times (this may take a moment)...")
    trip_stops = defaultdict(list)
    for st in stop_times_raw:
        trip_stops[st["trip_id"]].append({
            "stop_id": st["stop_id"],
            "stop_sequence": int(st["stop_sequence"]),
        })

    # Sort each trip's stops by sequence
    for tid in trip_stops:
        trip_stops[tid].sort(key=lambda x: x["stop_sequence"])

    # Group trips by (route_id, shape_id) to find distinct branch patterns
    # Then pick the longest trip per shape to get stop sequences for each branch
    route_shape_best = {}  # (route_id, shape_id) -> (trip_id, stop_count)
    for tid, info in trip_to_route.items():
        route_id = info["route_id"]
        shape_id = info["shape_id"]
        key = (route_id, shape_id)
        stop_count = len(trip_stops.get(tid, []))
        if key not in route_shape_best or stop_count > route_shape_best[key][1]:
            route_shape_best[key] = (tid, stop_count)

    # Build line data
    lines = {}
    station_lines = defaultdict(set)  # station_name -> set of lines

    def resolve_stop_name(stop_id):
        parent_id = child_to_parent.get(stop_id, stop_id)
        if parent_id in parent_stations:
            return parent_stations[parent_id]["name"]
        return None

    def get_trip_stop_names(trip_id):
        result = []
        for st in trip_stops[trip_id]:
            name = resolve_stop_name(st["stop_id"])
            if name and (not result or result[-1] != name):
                result.append(name)
        return result

    for route_id in sorted(STANDARD_LINES):
        # Collect all distinct shapes for this route
        shapes = {}
        for (rid, shape_id), (tid, count) in route_shape_best.items():
            if rid == route_id:
                shapes[shape_id] = tid

        if not shapes:
            print(f"  WARNING: No trips found for route {route_id}")
            continue

        # Get stop sequences for all shapes (branches)
        branch_stops = []
        for shape_id, tid in shapes.items():
            stops = get_trip_stop_names(tid)
            if stops:
                branch_stops.append(stops)

        # Merge branches: find the longest branch as the trunk, then insert
        # branch-only stops at the correct divergence point
        branch_stops.sort(key=len, reverse=True)
        trunk = list(branch_stops[0])
        trunk_set = set(trunk)

        for branch in branch_stops[1:]:
            # Find where branch diverges from trunk
            # Walk from the start to find last common stop
            branch_only = [s for s in branch if s not in trunk_set]
            if not branch_only:
                continue

            # Find the divergence point: the last trunk stop that appears
            # before the branch-only stops in the branch sequence
            diverge_idx = None
            for i, stop in enumerate(branch):
                if stop in trunk_set:
                    diverge_idx_in_trunk = trunk.index(stop)
                elif diverge_idx is not None:
                    break

            # Find insertion point: after the last common stop before divergence
            last_common_in_branch = None
            for stop in branch:
                if stop in trunk_set:
                    last_common_in_branch = stop
                else:
                    break

            if last_common_in_branch:
                insert_after = trunk.index(last_common_in_branch)
            else:
                insert_after = len(trunk) - 1

            # Collect the branch-only stops in order
            branch_tail = []
            found_diverge = False
            for stop in branch:
                if stop not in trunk_set:
                    found_diverge = True
                    branch_tail.append(stop)
                elif found_diverge:
                    break

            # Insert branch stops after the divergence point
            for j, stop in enumerate(branch_tail):
                trunk.insert(insert_after + 1 + j, stop)
                trunk_set.add(stop)

        # Register ALL stops (trunk + merged branches) for this line
        for name in trunk:
            station_lines[name].add(route_id)

        lines[route_id] = {
            "color": LINE_COLORS.get(route_id, "#808183"),
            "stops": trunk,
        }
        print(f"  Line {route_id}: {len(trunk)} stops")

    # Handle shuttles - combine into "S" line entries
    # GS = 42 St Shuttle, FS = Franklin Ave Shuttle, H = Rockaway Park Shuttle
    shuttle_names = {"GS": "42 St Shuttle", "FS": "Franklin Av Shuttle", "H": "Rockaway Park Shuttle"}
    all_shuttle_stops = []
    for shuttle_id in SHUTTLE_ROUTES:
        # Find the longest trip for this shuttle
        best_trip = None
        best_count = 0
        for (rid, shape_id), (tid, count) in route_shape_best.items():
            if rid == shuttle_id and count > best_count:
                best_trip = tid
                best_count = count
        if best_trip:
            stops_in_order = get_trip_stop_names(best_trip)
            for name in stops_in_order:
                station_lines[name].add("S")
            shuttle_entry = {
                "name": shuttle_names.get(shuttle_id, shuttle_id),
                "stops": stops_in_order,
            }
            all_shuttle_stops.append(shuttle_entry)
            print(f"  Shuttle {shuttle_id} ({shuttle_names.get(shuttle_id, '')}): {len(stops_in_order)} stops")

    lines["S"] = {
        "color": LINE_COLORS["S"],
        "shuttles": all_shuttle_stops,
    }

    # Load Wikipedia borough data if available
    wiki_boroughs = {}
    if os.path.exists(WIKI_BOROUGHS_FILE):
        with open(WIKI_BOROUGHS_FILE, "r", encoding="utf-8") as f:
            wiki_boroughs = json.load(f)
        print(f"Loaded {len(wiki_boroughs)} borough mappings from Wikipedia")

    def normalize_name(s):
        s = s.replace("\u2013", "-").replace("\u2014", "-").lower().strip()
        # Expand common abbreviations for better matching
        s = s.replace(" av/", " avenue/").replace(" av-", " avenue-")
        if s.endswith(" av"):
            s = s[:-3] + " avenue"
        s = s.replace(" st-", " street-").replace(" st/", " street/")
        if s.endswith(" st"):
            s = s[:-3] + " street"
        s = s.replace(" blvd", " boulevard").replace(" pkwy", " parkway")
        s = s.replace(" hts", " heights").replace(" sq", " square")
        s = s.replace(" ctr", " center").replace(" sts", " streets")
        s = re.sub(r"\s+", " ", s)
        return s

    # Build normalized Wikipedia lookup
    norm_wiki = {normalize_name(k): v for k, v in wiki_boroughs.items()}

    def lookup_borough_wiki(name):
        nn = normalize_name(name)
        if nn in norm_wiki:
            return norm_wiki[nn]
        # Try without parenthetical
        no_paren = re.sub(r"\s*\([^)]+\)", "", nn)
        if no_paren in norm_wiki:
            return norm_wiki[no_paren]
        # Try substring matching — prefer longest match
        best_match = None
        best_len = 0
        for wk, wv in norm_wiki.items():
            if nn in wk or wk in nn:
                overlap = min(len(nn), len(wk))
                if overlap > best_len:
                    best_len = overlap
                    best_match = wv
        if best_match:
            return best_match
        # Try matching first part before hyphen
        parts = nn.split("-")
        if len(parts) > 1:
            for wk, wv in norm_wiki.items():
                wparts = wk.split("-")
                if parts[0] == wparts[0] and len(parts[0]) > 3:
                    return wv
        return None

    # Build name -> (lat, lon) lookup from parent stations
    name_to_coords = {}
    for pid, info in parent_stations.items():
        if info["name"] not in name_to_coords:
            name_to_coords[info["name"]] = (info["lat"], info["lon"])

    # Build stations dict
    stations = {}
    wiki_hits = 0
    coord_hits = 0
    for name, line_set in station_lines.items():
        # Try Wikipedia first
        borough = lookup_borough_wiki(name)
        if borough:
            wiki_hits += 1
        else:
            # Fall back to coordinates
            coords = name_to_coords.get(name)
            if coords:
                borough = get_borough(coords[0], coords[1])
                coord_hits += 1
            else:
                borough = "Unknown"

        stations[name] = {
            "lines": sorted(line_set),
            "borough": borough,
        }

    print(f"Borough sources: {wiki_hits} from Wikipedia, {coord_hits} from coordinates")

    print(f"\nTotal: {len(lines)} lines, {len(stations)} stations")

    # Borough breakdown
    borough_counts = defaultdict(int)
    for s in stations.values():
        borough_counts[s["borough"]] += 1
    for b, c in sorted(borough_counts.items()):
        print(f"  {b}: {c} stations")

    # Transfer stations (3+ lines)
    transfer_stations = {k: v for k, v in stations.items() if len(v["lines"]) >= 3}
    print(f"  Transfer stations (3+ lines): {len(transfer_stations)}")

    output = {
        "lines": lines,
        "stations": stations,
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    file_size = os.path.getsize(OUTPUT_FILE)
    print(f"\nOutput written to {OUTPUT_FILE} ({file_size / 1024:.1f} KB)")

    # Also write a minified version
    min_output = OUTPUT_FILE.replace(".json", ".min.json")
    with open(min_output, "w", encoding="utf-8") as f:
        json.dump(output, f, separators=(",", ":"), ensure_ascii=False)

    min_size = os.path.getsize(min_output)
    print(f"Minified version: {min_output} ({min_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()

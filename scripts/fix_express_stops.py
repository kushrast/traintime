#!/usr/bin/env python3
"""Fix express/local stop issues and naming across all lines."""
import json

with open("data/subway_data.min.json") as f:
    data = json.load(f)

# ── Correct stop lists per MTA official maps ──
# Only lines that need fixing are listed here.

fixes = {
    "2": {
        "remove": [
            "86 St", "79 St", "66 St-Lincoln Center", "59 St-Columbus Circle", "50 St",
            "28 St", "23 St", "18 St", "Christopher St-Stonewall", "Houston St",
            "Canal St", "Franklin St",
            "Nostrand Av", "Kingston Av", "Crown Hts-Utica Av", "Sutter Av-Rutland Rd",
            "Saratoga Av", "Rockaway Av", "Junius St", "Pennsylvania Av",
            "Van Siclen Av", "New Lots Av"
        ]
    },
    "4": {
        "remove": [
            "116 St", "110 St", "103 St", "96 St", "77 St", "68 St-Hunter College",
            "51 St", "33 St", "28 St", "23 St-Baruch College", "Astor Pl",
            "Bleecker St", "Spring St", "Canal St",
            "Bergen St", "Grand Army Plaza", "Eastern Pkwy-Brooklyn Museum",
            "Nostrand Av", "Kingston Av", "Sutter Av-Rutland Rd", "Saratoga Av",
            "Rockaway Av", "Junius St", "Pennsylvania Av", "Van Siclen Av", "New Lots Av"
        ]
    },
    "5": {
        "remove": [
            "New Lots Av", "Van Siclen Av", "Pennsylvania Av", "Junius St",
            "Rockaway Av", "Saratoga Av", "Sutter Av-Rutland Rd",
            "Crown Hts-Utica Av", "Kingston Av", "Nostrand Av"
        ]
    },
    "A": {
        "remove": [
            "50 St", "23 St", "Spring St",
            "72 St", "81 St-Museum of Natural History", "86 St", "96 St",
            "103 St", "Cathedral Pkwy (110 St)", "116 St", "135 St",
            "155 St", "163 St-Amsterdam Av",
            "Lafayette Av", "Clinton-Washington Avs", "Franklin Av",
            "Kingston-Throop Avs", "Ralph Av", "Rockaway Av",
            "Liberty Av", "Shepherd Av", "Van Siclen Av"
        ]
    },
    "D": {
        "remove": [
            "DeKalb Av", "Union St", "4 Av-9 St", "Prospect Av", "25 St"
        ]
    },
    "E": {
        "remove": [
            "Sutphin Blvd", "Parsons Blvd", "169 St", "Jamaica-179 St",
            "67 Av", "63 Dr-Rego Park", "Woodhaven Blvd", "Grand Av-Newtown", "Elmhurst Av",
            "65 St", "Northern Blvd", "46 St", "Steinway St", "36 St"
        ]
    },
    "F": {
        "remove": [
            "67 Av", "63 Dr-Rego Park", "Woodhaven Blvd", "Grand Av-Newtown", "Elmhurst Av",
            "65 St", "Northern Blvd", "46 St", "Steinway St", "36 St",
            "21 St-Queensbridge", "Roosevelt Island", "Lexington Av/63 St", "57 St"
        ]
    },
    "N": {
        "remove": [
            "28 St", "23 St", "8 St-NYU", "Prince St",
            "Lexington Av/63 St", "72 St",
            "City Hall", "Cortlandt St", "Rector St", "Whitehall St-South Ferry",
            "Court St", "Jay St-MetroTech", "DeKalb Av",
            "Union St", "4 Av-9 St", "Prospect Av", "25 St",
            "45 St", "53 St",
            "96 St"
        ]
    },
    "R": {
        "remove": [
            "9 Av", "62 St", "Bay Pkwy",
            "Lexington Av/63 St", "72 St"
        ]
    },
    "W": {
        "remove": [
            "86 St", "Avenue U", "Kings Hwy", "Bay Pkwy", "20 Av", "18 Av",
            "New Utrecht Av", "Fort Hamilton Pkwy", "8 Av", "59 St", "53 St",
            "45 St", "36 St", "9 Av", "62 St", "25 St", "Prospect Av",
            "4 Av-9 St", "Union St", "Atlantic Av-Barclays Ctr", "DeKalb Av",
            "Jay St-MetroTech", "Court St"
        ]
    }
}

total_removed = 0
for line, fix in fixes.items():
    stops = data["lines"][line]["stops"]
    to_remove = set(fix["remove"])
    before = len(stops)
    new_stops = [s for s in stops if s not in to_remove]
    removed = before - len(new_stops)
    total_removed += removed
    data["lines"][line]["stops"] = new_stops
    print(f"{line}: {before} → {len(new_stops)} (removed {removed})")

    # Also remove line from station records
    for station in fix["remove"]:
        if station in data["stations"]:
            lines = data["stations"][station]["lines"]
            if line in lines:
                lines.remove(line)

print(f"\nTotal stops removed: {total_removed}")

# ── Naming fixes ──
# These are minor but let's keep them consistent with MTA

# Note: Not renaming stations that are shared across lines since the key
# would need to change everywhere. Just documenting for now.
print("\nNaming issues (not auto-fixed, need key changes):")
print("  6: 'E 143 St-St Mary's St' vs MTA 'E 143 St-Mary's St'")
print("  6: '23 St-Baruch College' vs MTA '23 St'")
print("  B: '42 St-Bryant Pk' vs MTA '42 St-Bryant Park'")
print("  Q: 'Beverley Rd' vs MTA 'Beverly Rd'")

with open("data/subway_data.min.json", "w") as f:
    json.dump(data, f, separators=(",", ":"))

print("\nDone. Data saved.")

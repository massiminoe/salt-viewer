#!/usr/bin/env python3
"""Parse Salt Guide fishing report text files into spots.json."""

import json
import re
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
OUTPUT = Path(__file__).parent / "spots.json"

REGIONS = {
    "PORT PHILLIP BAY", "WESTERN PORT", "WELSHPOOL", "OFFSHORE",
}

FISH_TYPES = {
    "CALAMARI": "Calamari",
    "WHITING": "Whiting",
    "GUMMY SHARK": "Gummy Shark",
    "GUMMY SHARKS": "Gummy Shark",
    "GUMMIES OFFSHORE": "Gummy Shark",
    "KINGFISH": "Kingfish",
    "CUTTLEFISH": "Cuttlefish",
}

COORD_RE = re.compile(
    r"[Ss](\d{2})\s+(\d{2})\s+(\d{3})\s+[Ee](\d{2,3})\s+(\d{2})\s+(\d{3})"
)

# Lines starting with these signal end of useful content
BOILERPLATE = [
    "There you go crew",
    "NB: Remember",
    "QUICK REMINDERS",
    "NEW MEMBER NOTES",
    "*/The above information",
]

MONTH_MAP = {
    "Jan": "Jan", "Feb": "Feb", "Mar": "Mar", "Apr": "Apr",
    "May": "May", "Jun": "Jun", "Jul": "Jul", "Aug": "Aug",
    "Sep": "Sep", "Oct": "Oct", "Nov": "Nov", "Dec": "Dec",
}


def parse_dms(deg, mins, dec):
    """Convert S38 21 504 style to decimal degrees. Format is deg° min.dec'."""
    return int(deg) + (int(mins) + int(dec) / 1000) / 60


def week_from_filename(filename):
    """Extract week label from filename like '5_Feb_26.txt'."""
    m = re.match(r"(\d+)_(\w+)_(\d+)", filename)
    if not m:
        return filename
    day, month, year = m.groups()
    return f"{int(day)} {month} 20{year}"


def is_boilerplate(line):
    return any(line.startswith(b) for b in BOILERPLATE)


def parse_file(filepath):
    spots = []
    week = week_from_filename(filepath.name)
    region = ""
    fish = ""
    spot_name = ""

    with open(filepath) as f:
        lines = f.readlines()

    for line in lines:
        line = line.rstrip()
        stripped = line.strip()

        if not stripped:
            continue

        if is_boilerplate(stripped):
            break

        # Check for region header
        if stripped in REGIONS:
            region = stripped.title()
            spot_name = ""
            continue

        # Check for fish type header
        upper = stripped.rstrip()
        if upper in FISH_TYPES:
            fish = FISH_TYPES[upper]
            spot_name = ""
            continue

        # Check for coordinate
        coord_match = COORD_RE.search(stripped)
        if coord_match:
            lat_d, lat_m, lat_dec, lng_d, lng_m, lng_dec = coord_match.groups()
            lat = -parse_dms(lat_d, lat_m, lat_dec)
            lng = parse_dms(lng_d, lng_m, lng_dec)

            # Text before the coordinate on the same line (e.g. "Ebb tide S38...")
            prefix = stripped[:coord_match.start()].strip()
            name = f"{spot_name} ({prefix})" if prefix and spot_name else prefix or spot_name

            spots.append({
                "lat": round(lat, 6),
                "lng": round(lng, 6),
                "spot": name,
                "fish": fish,
                "region": region,
                "week": week,
            })
            continue

        # Skip known non-spot lines (intro text, GAWAINE header, day headers)
        if stripped.startswith("GAWAINE") and len(stripped) < 30:
            continue
        if re.match(r"^(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY)\s", stripped):
            continue
        if stripped.startswith("G'day ") or stripped.startswith("G'day,"):
            continue

        # If line is long (>80 chars), it's probably a description paragraph
        if len(stripped) > 80:
            continue

        # Otherwise treat as spot name
        spot_name = stripped

    return spots


def main():
    all_spots = []
    files = sorted(DATA_DIR.glob("*.txt"))

    if not files:
        print(f"No .txt files found in {DATA_DIR}", file=sys.stderr)
        sys.exit(1)

    for f in files:
        spots = parse_file(f)
        print(f"{f.name}: {len(spots)} spots")
        all_spots.extend(spots)

    with open(OUTPUT, "w") as out:
        json.dump(all_spots, out, indent=2)

    print(f"\nTotal: {len(all_spots)} spots written to {OUTPUT}")


if __name__ == "__main__":
    main()

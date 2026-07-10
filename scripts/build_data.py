#!/usr/bin/env python3
"""Build ow-dashboard index.html from CSVs and map descriptions.

Reads:
  data/overwatch/{dps,tank,support}.csv
  memory/overwatch-maps.md
Writes:
  <repo>/index.html   (single-file static site with embedded JSON)
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

WORKSPACE = Path("/Users/clea/.openclaw/workspace")
DATA_DIR = WORKSPACE / "data" / "overwatch"
MAPS_MD = WORKSPACE / "memory" / "overwatch-maps.md"
REPO = WORKSPACE / "codebases" / "ow-dashboard"
OUT = REPO / "index.html"
TEMPLATE = REPO / "scripts" / "template.html"

CSV_TO_MD = {
    "Antarctica": "Antarctic Peninsula",
    "Busan": "Busan",
    "Ilios": "Ilios",
    "Lijiang": "Lijiang Tower",
    "Nepal": "Nepal",
    "Oasis": "Oasis",
    "Samoa": "Samoa",
    "Circuit Royal": "Circuit Royal",
    "Dorado": "Dorado",
    "Havana": "Havana",
    "Junkertown": "Junkertown",
    "Rialto": "Rialto",
    "Route 66": "Route 66",
    "Shambali": "Shambali Monastery",
    "Gibraltar": None,
    "Aatlis": None,
    "New Junk": "New Junk City",
    "Suravasa": "Suravasa",
    "Blizz World": "Blizzard World",
    "Eichenwalde": "Eichenwalde",
    "Hollywood": "Hollywood",
    "King's Row": "King's Row",
    "Midtown": "Midtown",
    "Neo Junction": None,
    "Numbani": "Numbani",
    "Paraiso": "Paraiso",
    "Colosseo": "Colosseo",
    "Esperanca": "Esperanca",
    "Queen St.": "New Queen Street",
    "Runasapi": "Runasapi",
}

DISPLAY_NAMES = {
    "Antarctica": "Antarctic Peninsula",
    "Lijiang": "Lijiang Tower",
    "Shambali": "Shambali Monastery",
    "Gibraltar": "Watchpoint: Gibraltar",
    "New Junk": "New Junk City",
    "Blizz World": "Blizzard World",
    "Neo Junction": "Neo Junction City",
    "Queen St.": "New Queen Street",
}

MODES = {
    "Control": ["Antarctica", "Busan", "Ilios", "Lijiang", "Nepal", "Oasis", "Samoa"],
    "Escort": ["Circuit Royal", "Dorado", "Havana", "Junkertown", "Rialto", "Route 66", "Shambali", "Gibraltar"],
    "Flashpoint": ["Aatlis", "New Junk", "Suravasa"],
    "Hybrid": ["Blizz World", "Eichenwalde", "Hollywood", "King's Row", "Midtown", "Neo Junction", "Numbani", "Paraiso"],
    "Push": ["Colosseo", "Esperanca", "Queen St.", "Runasapi"],
}

# Fallback descriptions for maps not in overwatch-maps.md yet.
FALLBACK_META = {
    "Gibraltar": (
        "Watchpoint: Gibraltar (Escort). Rocket-launch facility on the Mediterranean coast — three payload segments moving through cliff paths, indoor hangars, and the rocket assembly interior. First point is a classic long-sightline defender's paradise; second point breaks into tight corridors; the final push has heavy verticality. Sharpshooters and long-range poke thrive on defense; brawl and dive close distance on attack once the payload turns indoors."
    ),
    "Aatlis": (
        "Aatlis (Flashpoint). Sprawling multi-point map with rotating capture zones spread across large distances. Rewards mobility, macro rotations, and comps that can teamfight repeatedly without long downtime. Fast heroes and self-sustain shine — Wrecking Ball, D.Va, Winston, Tracer, Sombra — as does Symmetra's teleporter for rotations. Long stretches between zones punish slow lineups."
    ),
    "Neo Junction": (
        "Neo Junction City (Hybrid). Neon-lit near-future Junker City. First point contest is a wide urban plaza with elevated flanks; escort phase snakes through market corridors and skybridges. Verticality and short flank routes favor dive tanks and mobile DPS; the tight second segment opens the door to brawl and area-denial specialists."
    ),
}


def parse_percent(s: str) -> float | None:
    s = s.strip().replace("%", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def load_csv(path: Path, role: str) -> tuple[list[str], list[dict]]:
    with path.open() as fh:
        rows = list(csv.reader(fh))
    header = rows[0]
    # Columns: [blank, blank, map1, map2, ...]
    map_cols = header[2:]
    heroes: list[dict] = []
    for row in rows[1:]:
        if not row or not row[1].strip():
            continue
        overall = parse_percent(row[0])
        name = row[1].strip()
        by_map: dict[str, float] = {}
        for col, val in zip(map_cols, row[2:]):
            dev = parse_percent(val)
            if dev is None:
                continue
            by_map[col.strip()] = dev
        heroes.append({
            "name": name,
            "role": role,
            "overall": overall,
            "byMap": by_map,
        })
    return [c.strip() for c in map_cols], heroes


def extract_map_meta(md_text: str) -> dict[str, dict]:
    """Return {md_section_name: {description, tips, tank_picks, dps_picks, sup_picks}}."""
    sections: dict[str, dict] = {}
    # Split on `### `
    parts = re.split(r"^### ", md_text, flags=re.MULTILINE)
    for chunk in parts[1:]:
        # First line: "Name (Mode)"
        first_nl = chunk.find("\n")
        header = chunk[:first_nl].strip()
        body = chunk[first_nl + 1:]
        # Split at next `---` boundary
        end = body.find("\n---")
        if end != -1:
            body = body[:end]
        # Extract name (strip mode paren)
        name_match = re.match(r"^(.+?)\s*\(", header)
        name = name_match.group(1).strip() if name_match else header
        # Description
        desc_m = re.search(r"\*\*Map Description:\*\*\s*(.+?)(?=\n\n|\n\*\*)", body, re.DOTALL)
        description = desc_m.group(1).strip().replace("\n", " ") if desc_m else ""
        # Compositions
        comp_m = re.search(r"\*\*Compositions That Thrive:\*\*\s*\n(.+?)(?=\n\n\*\*|\Z)", body, re.DOTALL)
        comps = comp_m.group(1).strip() if comp_m else ""
        # Tips
        tips_m = re.search(r"\*\*Tips:\*\*\s*\n(.+?)(?=\n\n\*\*|\Z)", body, re.DOTALL)
        tips = tips_m.group(1).strip() if tips_m else ""
        sections[name] = {
            "description": description,
            "compositions": comps,
            "tips": tips,
        }
    return sections


def build_meta(csv_key: str, md_meta: dict[str, dict]) -> dict:
    md_name = CSV_TO_MD.get(csv_key)
    if md_name and md_name in md_meta:
        entry = md_meta[md_name]
        return {
            "description": entry["description"],
            "compositions": entry["compositions"],
            "tips": entry["tips"],
        }
    # Fallback
    return {
        "description": FALLBACK_META.get(csv_key, ""),
        "compositions": "",
        "tips": "",
    }


def main() -> int:
    map_cols_dps, dps = load_csv(DATA_DIR / "dps.csv", "DPS")
    map_cols_tank, tank = load_csv(DATA_DIR / "tank.csv", "Tank")
    map_cols_sup, sup = load_csv(DATA_DIR / "support.csv", "Support")

    if map_cols_dps != map_cols_tank or map_cols_dps != map_cols_sup:
        print("CSV map columns do not match across roles", file=sys.stderr)
        return 2

    map_keys = map_cols_dps

    md_meta = extract_map_meta(MAPS_MD.read_text())

    # Build maps array, grouped by mode
    maps = []
    for mode, keys in MODES.items():
        for key in keys:
            if key not in map_keys:
                print(f"WARN: {key} not in CSV columns", file=sys.stderr)
                continue
            meta = build_meta(key, md_meta)
            maps.append({
                "key": key,
                "name": DISPLAY_NAMES.get(key, key),
                "mode": mode,
                "meta": meta,
            })

    heroes = dps + tank + sup

    data = {
        "generatedAt": None,
        "maps": maps,
        "heroes": heroes,
    }

    template = TEMPLATE.read_text()
    data_json = json.dumps(data, ensure_ascii=False, indent=None, separators=(",", ":"))
    out = template.replace("/*__DATA__*/", data_json)
    OUT.write_text(out)
    print(f"Wrote {OUT} ({len(out):,} bytes, {len(maps)} maps, {len(heroes)} heroes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Update cycling race startlists from ProCyclingStats.

Fetches startlists for 19 men's races and produces:
- startlist_matrix.csv: rider presence matrix
- startlist_changes.csv: append-only change log
- startlist_snapshot.json: internal state for diffing
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Set, List, Tuple

from procyclingstats import RaceStartlist

def extract_race_path(pcs_url: str) -> str:
    """
    Extract the race path from a full ProCyclingStats URL.
    
    Example:
        https://www.procyclingstats.com/race/omloop-het-nieuwsblad/2026/startlist
        -> omloop-het-nieuwsblad/2026
    """
    # Remove protocol and domain
    parts = pcs_url.replace("https://www.procyclingstats.com/race/", "")
    # Remove /startlist suffix
    parts = parts.replace("/startlist", "")
    return parts

def load_race_config(config_path: str) -> List[Dict]:
    """Load race configuration from JSON file."""
    with open(config_path, "r") as f:
        data = json.load(f)
    return data["races"]

def fetch_startlist(race_path: str, sleep_seconds: float = 1.0) -> List[Dict]:
    """
    Fetch startlist for a race using procyclingstats library.
    
    Args:
        race_path: Path like "omloop-het-nieuwsblad/2026"
        sleep_seconds: Delay before fetching (politeness)
    
    Returns:
        List of rider dicts with 'name' and 'url' keys
    """
    time.sleep(sleep_seconds)
    try:
        startlist = RaceStartlist(race_path)
        riders = []
        for rider in startlist.riders:
            riders.append({
                "name": rider.name,
                "url": rider.url
            })
        return riders
    except Exception as e:
        print(f"  WARNING: Failed to fetch {race_path}: {e}", file=sys.stderr)
        return []

def build_snapshot(races: List[Dict], sleep_seconds: float = 1.0) -> Dict:
    """
    Build a snapshot of all startlists.
    
    Returns:
        {
            "timestamp_utc": "2026-02-09T14:30:00Z",
            "races": {
                "Omloop Nieuwsblad": [
                    {"name": "Rider Name", "url": "rider_url"},
                    ...
                ],
                ...
            }
        }
    """
    print("Fetching startlists...")
    snapshot = {
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "races": {}
    }
    
    for race in races:
        race_name = race["race_name"]
        pcs_url = race["pcs_url"]
        race_path = extract_race_path(pcs_url)
        
        print(f"  Fetching {race_name}...", end=" ", flush=True)
        riders = fetch_startlist(race_path, sleep_seconds=sleep_seconds)
        snapshot["races"][race_name] = riders
        print(f"({len(riders)} riders)")
    
    return snapshot

def snapshot_to_rider_map(snapshot: Dict) -> Dict[str, Dict]:
    """
    Convert snapshot to a rider map keyed by rider_url.
    
    Returns:
        {
            "rider_url": {
                "name": "Rider Name",
                "races": {"Omloop Nieuwsblad", "Kuurne-Brussel-Kuurne", ...}
            },
            ...
        }
    """
    rider_map = {}
    
    for race_name, riders in snapshot["races"].items():
        for rider in riders:
            url = rider["url"]
            name = rider["name"]
            
            if url not in rider_map:
                rider_map[url] = {
                    "name": name,
                    "races": set()
                }
            
            rider_map[url]["races"].add(race_name)
    
    return rider_map

def compute_changes(
    old_snapshot: Dict,
    new_snapshot: Dict,
    races: List[Dict]
) -> List[Dict]:
    """
    Compute changes between two snapshots.
    
    Returns:
        List of change dicts: {
            "timestamp_utc": "...",
            "race_name": "...",
            "change": "ADDED" or "REMOVED",
            "rider_name": "...",
            "rider_url": "..."
        }
    """
    changes = []
    
    # Build maps for easy lookup
    old_races = old_snapshot["races"] if old_snapshot else {}
    new_races = new_snapshot["races"]
    
    timestamp = new_snapshot["timestamp_utc"]
    
    for race in races:
        race_name = race["race_name"]
        
        old_riders = set()
        if race_name in old_races:
            old_riders = {r["url"] for r in old_races[race_name]}
        
        new_riders = set()
        if race_name in new_races:
            new_riders = {r["url"] for r in new_races[race_name]}
        
        # Build lookup for names
        new_riders_by_url = {}
        if race_name in new_races:
            new_riders_by_url = {r["url"]: r["name"] for r in new_races[race_name]}
        
        old_riders_by_url = {}
        if race_name in old_races:
            old_riders_by_url = {r["url"]: r["name"] for r in old_races[race_name]}
        
        # ADDED riders
        for rider_url in new_riders - old_riders:
            changes.append({
                "timestamp_utc": timestamp,
                "race_name": race_name,
                "change": "ADDED",
                "rider_name": new_riders_by_url[rider_url],
                "rider_url": rider_url
            })
        
        # REMOVED riders
        for rider_url in old_riders - new_riders:
            changes.append({
                "timestamp_utc": timestamp,
                "race_name": race_name,
                "change": "REMOVED",
                "rider_name": old_riders_by_url[rider_url],
                "rider_url": rider_url
            })
    
    return changes

def write_matrix_csv(
    output_path: str,
    rider_map: Dict,
    races: List[Dict]
):
    """Write startlist_matrix.csv with rider presence matrix."""
    race_names = [r["race_name"] for r in races]
    
    # Sort riders deterministically: by name, then by URL
    sorted_riders = sorted(
        rider_map.items(),
        key=lambda x: (x[1]["name"], x[0])
    )
    
    with open(output_path, "w", encoding="utf-8") as f:
        # Header
        header = ["rider_name", "rider_url"] + race_names + ["races_count"]
        f.write(",".join(header) + "\n")
        
        # Rows
        for rider_url, rider_info in sorted_riders:
            name = rider_info["name"]
            races_set = rider_info["races"]
            
            row = [name, rider_url]
            for race_name in race_names:
                row.append("X" if race_name in races_set else "")
            
            races_count = f"{len(races_set)}/{len(race_names)}"
            row.append(races_count)
            
            # Escape quotes in rider names
            safe_row = []
            for cell in row:
                if "," in cell or '"' in cell or "\n" in cell:
                    safe_row.append(f'"{cell.replace(chr(34), chr(34) + chr(34))}"')
                else:
                    safe_row.append(cell)
            
            f.write(",".join(safe_row) + "\n")


def write_changes_csv(output_path: str, changes: List[Dict]):
    """Append changes to startlist_changes.csv."""
    file_exists = os.path.exists(output_path)
    
    with open(output_path, "a", encoding="utf-8") as f:
        # Write header only if file doesn't exist
        if not file_exists:
            f.write("timestamp_utc,race_name,change,rider_name,rider_url\n")
        
        # Write change rows
        for change in changes:
            row = [
                change["timestamp_utc"],
                change["race_name"],
                change["change"],
                change["rider_name"],
                change["rider_url"]
            ]
            
            # Escape CSV fields
            safe_row = []
            for cell in row:
                if "," in cell or '"' in cell or "\n" in cell:
                    safe_row.append(f'"{cell.replace(chr(34), chr(34) + chr(34))}"')
                else:
                    safe_row.append(cell)
            
            f.write(",".join(safe_row) + "\n")


def write_snapshot_json(output_path: str, snapshot: Dict):
    """Write snapshot for next diff."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)

def load_old_snapshot(snapshot_path: str) -> Dict:
    """Load previous snapshot, or return None if missing."""
    if os.path.exists(snapshot_path):
        try:
            with open(snapshot_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"WARNING: Failed to load snapshot: {e}", file=sys.stderr)
    return None

def main():
    # Setup paths
    config_path = Path("data/races_2026.json")
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    matrix_path = output_dir / "startlist_matrix.csv"
    changes_path = output_dir / "startlist_changes.csv"
    snapshot_path = output_dir / "startlist_snapshot.json"
    
    # Load config
    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)
    
    races = load_race_config(str(config_path))
    print(f"Loaded {len(races)} races from config")
    
    # Get sleep duration
    sleep_seconds = float(os.environ.get("PCS_SLEEP_SECONDS", "1.0"))
    
    # Fetch new snapshot
    new_snapshot = build_snapshot(races, sleep_seconds=sleep_seconds)
    
    # Load old snapshot
    old_snapshot = load_old_snapshot(str(snapshot_path))
    
    # Build rider map
    rider_map = snapshot_to_rider_map(new_snapshot)
    print(f"Total unique riders: {len(rider_map)}")
    
    # Compute changes (if not first run)
    changes = []
    if old_snapshot:
        changes = compute_changes(old_snapshot, new_snapshot, races)
        print(f"Detected {len(changes)} changes")
    else:
        print("First run - no changes to compute")
    
    # Write outputs
    print("Writing outputs...")
    write_matrix_csv(str(matrix_path), rider_map, races)
    print(f"  Wrote {matrix_path}")
    
    if changes:
        write_changes_csv(str(changes_path), changes)
        print(f"  Appended {len(changes)} changes to {changes_path}")
    
    write_snapshot_json(str(snapshot_path), new_snapshot)
    print(f"  Wrote snapshot: {snapshot_path}")
    
    print("\nDone!")


if __name__ == "__main__":
    main()
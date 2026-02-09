#!/usr/bin/env python3
"""
Fetch cycling race startlists and generate outputs:
- startlist_matrix.csv
- startlist_changes.csv
- startlist_snapshot.json
"""

import json
import csv
import os
from datetime import datetime
from pathlib import Path
from time import sleep
from collections import defaultdict

# Uncomment when you have procyclingstats installed
# from procyclingstats import RaceStartlist

# Configuration
RACES_CONFIG = Path("data/races_2026.json")
OUTPUT_DIR = Path("output")
SNAPSHOT_FILE = OUTPUT_DIR / "startlist_snapshot.json"
MATRIX_FILE = OUTPUT_DIR / "startlist_matrix.csv"
CHANGES_FILE = OUTPUT_DIR / "startlist_changes.csv"
SLEEP_SECONDS = float(os.getenv("PCS_SLEEP_SECONDS", "1.0"))


def load_races():
    """Load race configuration from JSON."""
    with open(RACES_CONFIG) as f:
        return json.load(f)


def load_previous_snapshot():
    """Load the previous snapshot if it exists."""
    if SNAPSHOT_FILE.exists():
        with open(SNAPSHOT_FILE) as f:
            return json.load(f)
    return {}


def fetch_startlists(races):
    """
    Fetch all startlists from ProCyclingStats.
    Returns: dict mapping race_name -> list of {rider_name, rider_url}
    """
    startlists = {}
    
    for race in races:
        race_name = race["name"]
        race_url = race["url"]
        
        print(f"Fetching: {race_name}")
        
        try:
            # Uncomment when using the actual library:
            # race_startlist = RaceStartlist(race_url)
            # riders = [
            #     {"name": rider.name, "url": rider.url}
            #     for rider in race_startlist.riders()
            # ]
            
            # For now, mock data (remove this in production):
            riders = []  # Empty until you connect real API
            
            startlists[race_name] = riders
            
        except Exception as e:
            print(f"  ⚠️  Error fetching {race_name}: {e}")
            startlists[race_name] = []
        
        # Be polite to the server
        sleep(SLEEP_SECONDS)
    
    return startlists


def build_snapshot(startlists):
    """
    Build a snapshot keyed by rider_url.
    Format: {rider_url: {name: str, races: [race_names]}}
    """
    snapshot = {}
    
    for race_name, riders in startlists.items():
        for rider in riders:
            rider_url = rider["url"]
            
            if rider_url not in snapshot:
                snapshot[rider_url] = {
                    "name": rider["name"],
                    "races": []
                }
            
            snapshot[rider_url]["races"].append(race_name)
    
    return snapshot


def compute_changes(old_snapshot, new_snapshot):
    """
    Compare snapshots and return a list of changes.
    Returns: list of {timestamp, race, change_type, rider_name, rider_url}
    """
    changes = []
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    # Find all unique riders across both snapshots
    all_rider_urls = set(old_snapshot.keys()) | set(new_snapshot.keys())
    
    for rider_url in all_rider_urls:
        old_races = set(old_snapshot.get(rider_url, {}).get("races", []))
        new_races = set(new_snapshot.get(rider_url, {}).get("races", []))
        
        rider_name = (
            new_snapshot.get(rider_url, {}).get("name") or
            old_snapshot.get(rider_url, {}).get("name")
        )
        
        # Races added
        for race in new_races - old_races:
            changes.append({
                "timestamp": timestamp,
                "race": race,
                "change_type": "ADDED",
                "rider_name": rider_name,
                "rider_url": rider_url
            })
        
        # Races removed
        for race in old_races - new_races:
            changes.append({
                "timestamp": timestamp,
                "race": race,
                "change_type": "REMOVED",
                "rider_name": rider_name,
                "rider_url": rider_url
            })
    
    return changes


def append_changes(changes):
    """Append changes to the CSV log file."""
    if not changes:
        print("No changes detected.")
        return
    
    file_exists = CHANGES_FILE.exists()
    
    with open(CHANGES_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "timestamp", "race", "change_type", "rider_name", "rider_url"
        ])
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerows(changes)
    
    print(f"Logged {len(changes)} changes to {CHANGES_FILE}")


def generate_matrix(snapshot, races):
    """
    Generate the presence matrix CSV.
    Rows: riders (sorted by name)
    Columns: races (in config order) + races_count
    """
    race_names = [race["name"] for race in races]
    
    # Build rows: one per rider
    rows = []
    for rider_url, data in snapshot.items():
        rider_name = data["name"]
        rider_races = set(data["races"])
        
        row = {"rider_name": rider_name}
        
        # Mark presence in each race
        for race_name in race_names:
            row[race_name] = "X" if race_name in rider_races else ""
        
        # Count total races
        row["races_count"] = f"{len(rider_races)}/{len(race_names)}"
        
        rows.append(row)
    
    # Sort by rider name
    rows.sort(key=lambda r: r["rider_name"])
    
    # Write CSV
    with open(MATRIX_FILE, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ["rider_name"] + race_names + ["races_count"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Generated matrix: {MATRIX_FILE} ({len(rows)} riders)")


def save_snapshot(snapshot):
    """Save the current snapshot to JSON."""
    with open(SNAPSHOT_FILE, 'w', encoding='utf-8') as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)
    
    print(f"Saved snapshot: {SNAPSHOT_FILE}")


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    print("Loading race configuration...")
    races = load_races()
    print(f"Tracking {len(races)} races")
    
    print("\nFetching startlists...")
    startlists = fetch_startlists(races)
    
    print("\nBuilding snapshot...")
    new_snapshot = build_snapshot(startlists)
    
    print("\nDetecting changes...")
    old_snapshot = load_previous_snapshot()
    changes = compute_changes(old_snapshot, new_snapshot)
    
    print("\nAppending changes to log...")
    append_changes(changes)
    
    print("\nGenerating matrix...")
    generate_matrix(new_snapshot, races)
    
    print("\nSaving snapshot...")
    save_snapshot(new_snapshot)
    
    print("\n✅ Done!")


if __name__ == "__main__":
    main()

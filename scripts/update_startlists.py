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

# IMPORTANT: Uncomment the next line to enable actual data fetching
from procyclingstats import RaceStartlist

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
        data = json.load(f)
    
    # Handle different JSON structures
    if isinstance(data, list):
        # If it's already a list of race objects
        races = data
    elif isinstance(data, dict):
        # If it's a dict with a "races" key
        if "races" in data:
            races = data["races"]
        # If it's a single race object, wrap it in a list
        elif "race_name" in data or "name" in data:
            races = [data]
        else:
            raise ValueError(f"Unexpected JSON structure in {RACES_CONFIG}: {list(data.keys())}")
    else:
        raise ValueError(f"Expected list or dict in {RACES_CONFIG}, got {type(data)}")
    
    # Normalize field names to use 'name' and 'url' consistently
    normalized_races = []
    for race in races:
        normalized = {
            "name": race.get("race_name") or race.get("name"),
            "url": race.get("pcs_url") or race.get("url")
        }
        normalized_races.append(normalized)
    
    return normalized_races


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
        
        # Extract path from full URL if needed
        # procyclingstats library expects: "race/omloop-het-nieuwsblad/2026"
        # Not: "https://www.procyclingstats.com/race/omloop-het-nieuwsblad/2026/startlist"
        if race_url.startswith("http"):
            # Remove domain and /startlist suffix
            race_path = race_url.replace("https://www.procyclingstats.com/", "")
            race_path = race_path.replace("/startlist", "")
        else:
            race_path = race_url
        
        print(f"Fetching: {race_name} ({race_path})")
        
        try:
            # Check if RaceStartlist is available
            try:
                RaceStartlist
                use_real_data = True
            except NameError:
                use_real_data = False
            
            if use_real_data:
                # Real data fetching
                race_startlist = RaceStartlist(race_path)
                
                # Use the .startlist property
                startlist_data = race_startlist.startlist
                
                # startlist_data should be a list of rider objects
                riders = []
                if startlist_data:
                    for rider in startlist_data:
                        # Extract rider info - check what attributes are available
                        if hasattr(rider, 'name') and hasattr(rider, 'url'):
                            riders.append({
                                "name": rider.name,
                                "url": rider.url
                            })
                        elif isinstance(rider, dict):
                            riders.append({
                                "name": rider.get('name', ''),
                                "url": rider.get('url', '')
                            })
                
                if riders:
                    print(f"  ✓ Found {len(riders)} riders")
                else:
                    print(f"  ℹ️  No riders found (startlist may not be published yet)")
            else:
                # Mock data - returns empty list
                # To enable real data: uncomment the import at the top of the file
                riders = []
                print(f"  ℹ️  Using mock data (import RaceStartlist to fetch real data)")
            
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
    
    # Handle old snapshot format (if it's structured differently)
    # Old format might be: {race_name: [rider_urls]} or {race_name: {rider_url: rider_name}}
    # New format is: {rider_url: {name: str, races: [race_names]}}
    
    # Normalize old_snapshot to new format if needed
    normalized_old = {}
    if old_snapshot:
        # Check if it has the old structure with "races" or "timestamp_utc" keys
        if "races" in old_snapshot or "timestamp_utc" in old_snapshot:
            # Old format: {timestamp_utc: ..., races: {race_name: [riders]}}
            old_races_data = old_snapshot.get("races", {})
            
            for race_name, riders in old_races_data.items():
                if isinstance(riders, list):
                    for rider in riders:
                        # Rider might be a string (URL) or dict with 'url' and 'name'
                        if isinstance(rider, str):
                            rider_url = rider
                            rider_name = ""
                        elif isinstance(rider, dict):
                            rider_url = rider.get("url", rider.get("rider_url", ""))
                            rider_name = rider.get("name", rider.get("rider_name", ""))
                        else:
                            continue
                        
                        if rider_url and rider_url not in normalized_old:
                            normalized_old[rider_url] = {
                                "name": rider_name,
                                "races": []
                            }
                        if rider_url:
                            normalized_old[rider_url]["races"].append(race_name)
        else:
            # Check if it's already in the new format
            first_key = next(iter(old_snapshot))
            first_value = old_snapshot[first_key]
            
            if isinstance(first_value, dict) and "races" in first_value:
                # Already in new format
                normalized_old = old_snapshot
            elif isinstance(first_value, str):
                # Old format: {rider_url: rider_name} - need to reconstruct races from context
                # For now, just use empty to avoid errors on first migration
                normalized_old = {}
            elif isinstance(first_value, list):
                # Old format: {race_name: [rider_urls]} - need to invert
                # Invert it to new format
                for race_name, rider_list in old_snapshot.items():
                    if isinstance(rider_list, list):
                        for rider_url in rider_list:
                            if rider_url not in normalized_old:
                                normalized_old[rider_url] = {
                                    "name": "",  # Don't have name in old format
                                    "races": []
                                }
                            normalized_old[rider_url]["races"].append(race_name)
            else:
                # Unknown format, start fresh
                normalized_old = {}
    
    # Find all unique riders across both snapshots
    all_rider_urls = set(normalized_old.keys()) | set(new_snapshot.keys())
    
    for rider_url in all_rider_urls:
        old_races = set(normalized_old.get(rider_url, {}).get("races", []))
        new_races = set(new_snapshot.get(rider_url, {}).get("races", []))
        
        rider_name = (
            new_snapshot.get(rider_url, {}).get("name") or
            normalized_old.get(rider_url, {}).get("name") or
            "Unknown"
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
    
    # Debug: show first race to verify structure
    if races:
        print(f"First race example: {races[0]}")
    
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

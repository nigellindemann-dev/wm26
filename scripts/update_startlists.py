#!/usr/bin/env python3
"""
Fetch cycling race startlists and generate:
- startlist_matrix.csv
- startlist_changes.csv
- startlist_snapshot.json
"""

import json
import csv
import os
import re
import time
from datetime import datetime
from pathlib import Path
from time import sleep

import cloudscraper
import procyclingstats as pcs


# ======================
# Config
# ======================

RACES_CONFIG = Path("data/races_2026.json")
OUTPUT_DIR = Path("output")

SNAPSHOT_FILE = OUTPUT_DIR / "startlist_snapshot.json"
MATRIX_FILE = OUTPUT_DIR / "startlist_matrix.csv"
CHANGES_FILE = OUTPUT_DIR / "startlist_changes.csv"

SLEEP_SECONDS = float(os.getenv("PCS_SLEEP_SECONDS", "1.0"))


# ======================
# Utils
# ======================

def load_races():
    """Load race config supporting both flat and legacy formats."""
    with open(RACES_CONFIG) as f:
        data = json.load(f)

    if isinstance(data, list):
        return data

    if isinstance(data, dict) and "races" in data:
        return [
            {"name": r["race_name"], "url": r["pcs_url"]}
            for r in data["races"]
        ]

    raise ValueError("Unsupported races JSON format")


def rel_pcs(url: str) -> str:
    """Convert full PCS URL → relative path required by library."""
    return re.sub(r"^https?://www\.procyclingstats\.com/", "", url.strip()).lstrip("/")


def fetch_html(scraper, url, retries=3, timeout=30):
    last_err = None
    for attempt in range(retries):
        try:
            resp = scraper.get(url, timeout=timeout)
            if resp.status_code == 200 and resp.text and len(resp.text) > 500:
                return resp.text
            last_err = Exception(f"HTTP {resp.status_code} or short HTML")
        except Exception as e:
            last_err = e
        time.sleep(2 * (attempt + 1))
    raise last_err


# ======================
# Fetch PCS startlists
# ======================

def fetch_startlists(races):
    startlists = {}

    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False}
    )

    for race in races:
        race_name = race["name"]
        url = race["url"]

        print(f"Fetching: {race_name}")

        try:
            rel = rel_pcs(url)
            html = fetch_html(scraper, url)

            data = pcs.RaceStartlist(rel, html, update_html=False).startlist(
                "rider_name", "rider_url"
            )

            riders = []
            for r in data or []:
                name = (r.get("rider_name") or "").strip()
                rider_url = (r.get("rider_url") or "").strip()
                if name and rider_url:
                    riders.append({"name": name, "url": rider_url})

            print(f"  ✓ {len(riders)} riders")
            startlists[race_name] = riders

        except Exception as e:
            print(f"  ⚠️ Failed: {type(e).__name__}: {e}")
            startlists[race_name] = []

        sleep(SLEEP_SECONDS)

    return startlists


# ======================
# Snapshot + changes
# ======================

def build_snapshot(startlists):
    snapshot = {}
    for race_name, riders in startlists.items():
        for r in riders:
            url = r["url"]
            if url not in snapshot:
                snapshot[url] = {"name": r["name"], "races": []}
            snapshot[url]["races"].append(race_name)
    return snapshot


def load_previous_snapshot():
    if SNAPSHOT_FILE.exists():
        return json.loads(SNAPSHOT_FILE.read_text())
    return {}


def compute_changes(old, new):
    changes = []
    timestamp = datetime.utcnow().isoformat() + "Z"

    all_urls = set(old.keys()) | set(new.keys())

    for url in all_urls:
        old_r = set(old.get(url, {}).get("races", []))
        new_r = set(new.get(url, {}).get("races", []))
        name = new.get(url, {}).get("name") or old.get(url, {}).get("name") or "Unknown"

        for race in new_r - old_r:
            changes.append({
                "timestamp": timestamp,
                "race": race,
                "change_type": "ADDED",
                "rider_name": name,
                "rider_url": url
            })

        for race in old_r - new_r:
            changes.append({
                "timestamp": timestamp,
                "race": race,
                "change_type": "REMOVED",
                "rider_name": name,
                "rider_url": url
            })

    return changes


def append_changes(changes):
    if not changes:
        print("No changes.")
        return

    exists = CHANGES_FILE.exists()
    with open(CHANGES_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "timestamp", "race", "change_type", "rider_name", "rider_url"
        ])
        if not exists:
            writer.writeheader()
        writer.writerows(changes)

    print(f"Logged {len(changes)} changes")


# ======================
# Matrix output
# ======================

def generate_matrix(snapshot, races):
    race_names = [r["name"] for r in races]

    rows = []
    for rider_url, data in snapshot.items():
        row = {
            "rider_name": data["name"],
            "rider_url": rider_url
        }

        rider_races = set(data["races"])
        for race in race_names:
            row[race] = "X" if race in rider_races else ""

        row["races_count"] = f"{len(rider_races)}/{len(race_names)}"
        rows.append(row)

    rows.sort(key=lambda r: (r["rider_name"], r["rider_url"]))

    with open(MATRIX_FILE, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["rider_name", "rider_url"] + race_names + ["races_count"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Matrix written ({len(rows)} riders)")


def save_snapshot(snapshot):
    SNAPSHOT_FILE.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False))


# ======================
# Main
# ======================

def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    races = load_races()
    print(f"Tracking {len(races)} races")

    startlists = fetch_startlists(races)

    new_snapshot = build_snapshot(startlists)
    old_snapshot = load_previous_snapshot()

    changes = compute_changes(old_snapshot, new_snapshot)
    append_changes(changes)

    generate_matrix(new_snapshot, races)
    save_snapshot(new_snapshot)

    print("✅ Done")


if __name__ == "__main__":
    main()

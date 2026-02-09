# 🚴 Cycling Startlists 2026

An automated pipeline that keeps cycling race startlists up to date for 19 Spring Classics races (men's) from [ProCyclingStats](https://www.procyclingstats.com).

**Everything runs on GitHub** — no local setup, no external services required.

## Features

- **Automatic Updates**: Runs every 6 hours via GitHub Actions
- **Matrix View**: See which riders are in which races at a glance (`output/index.html`)
- **Change Log**: Track additions and removals per race (`output/startlist_changes.csv`)
- **Deterministic**: Consistent ordering; no randomness or unstable diffs
- **Polite Scraping**: Configurable delay between fetches (1 second default)

## Outputs

All outputs are in the `/output` directory:

### 1. **index.html** — Interactive Matrix Viewer
- Open in any browser (no build tools needed)
- Search by rider name
- See rider count and races attended
- Download links to CSV files

### 2. **startlist_matrix.csv** — Presence Matrix
- 1 row per unique rider
- 1 column per race
- Cell = "X" if rider is in that race's startlist
- Final column: "races_count" (e.g., "7/19")

### 3. **startlist_changes.csv** — Append-Only Change Log
- Timestamp (UTC)
- Race name
- Change type: "ADDED" or "REMOVED"
- Rider name and URL
- Useful for tracking which riders dropped/joined

### 4. **startlist_snapshot.json** — Internal State
- Stores the current snapshot for diff comparisons
- Auto-generated; don't edit

## Races Tracked (19 men's races)

1. Omloop Nieuwsblad
2. Kuurne-Brussel-Kuurne
3. Samyn Classic
4. Strade Bianche
5. Nokere Koerse
6. Bredene Koksijde Classic
7. Milaan-Sanremo
8. Ronde van Brugge
9. E3 Saxo Classic
10. In Flanders Fields
11. Dwars door Vlaanderen
12. Ronde van Vlaanderen
13. Scheldeprijs
14. Parijs-Roubaix
15. Ronde van Limburg
16. Brabantse Pijl
17. Amstel Gold Race
18. Waalse Pijl
19. Luik-Bastenaken-Luik

## Manual Trigger

To update immediately (instead of waiting for the 6-hour schedule):

1. Go to **Actions** → **Update Startlists**
2. Click **Run workflow**
3. Select your branch
4. Click **Run workflow**

Results will be committed automatically within ~1 minute.

## How It Works

### Configuration
- **`data/races_2026.json`**: Ordered list of 19 races with PCS URLs
  - Order determines the matrix column order
  - Each race has a PCS URL that the library converts to an internal path

### Fetching
- **`scripts/update_startlists.py`**: Main script
  - Loads race config
  - Fetches each startlist via `procyclingstats.RaceStartlist`
  - Builds a snapshot keyed by `rider_url`
  - Compares to previous snapshot for changes
  - Outputs matrix, changes log, and snapshot

### Viewing
- **`scripts/generate_viewer.py`**: Generates `index.html`
  - Reads the matrix CSV
  - Creates a responsive, searchable table
  - Vanilla JS (no dependencies or CDNs)

### Automation
- **`.github/workflows/update.yml`**: GitHub Actions workflow
  - Scheduled: every 6 hours (UTC)
  - Manual trigger available
  - Installs dependencies
  - Runs the update script
  - Commits and pushes results
  - Skip-on-repeat prevention: only commits if files changed

## Dependencies

Minimal and lean:
- `procyclingstats` — Official PCS Python library ([docs](https://procyclingstats.readthedocs.io/en/stable/api.html))
- Python 3.11+
- No heavy frameworks or external CDNs

## Politeness & Rate Limiting

- Default 1 second delay between race fetches
- Configurable via `PCS_SLEEP_SECONDS` environment variable
- Respects ProCyclingStats by being a good citizen

## Notes

- **Startlist Availability**: Some races may not have updated startlists yet. The script treats empty startlists gracefully (no crash, just empty for that race).
- **First Run**: No changes are logged on the first run; snapshot is created for future diffs.
- **Rider Identification**: Riders are uniquely identified by their PCS URL; the same rider under multiple names or URLs will appear as separate entries.

## Project Structure

```
.
├── README.md
├── requirements.txt
├── data/
│   └── races_2026.json          # Race config (ordered)
├── scripts/
│   ├── update_startlists.py     # Main fetcher & processor
│   └── generate_viewer.py       # HTML viewer generator
├── output/
│   ├── index.html               # Interactive viewer
│   ├── startlist_matrix.csv     # Presence matrix
│   ├── startlist_changes.csv    # Change log (append-only)
│   └── startlist_snapshot.json  # Internal state
└── .github/workflows/
    └── update.yml               # GitHub Actions schedule
```

## Troubleshooting

- **Workflow not triggering**: Check Actions tab, enable workflows if disabled
- **No changes being logged**: This is normal if startlists haven't changed since last run
- **Missing output files**: First run needs time; check Actions log for errors
- **ProCyclingStats down**: Graceful degradation; races with unavailable data are skipped

## License

MIT

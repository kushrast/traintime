# NYC Subway Mini-Games

A self-contained, offline-capable web app with two mini-games for learning the NYC subway system.

## Games

### Fill the Line
Pick a subway line and fill in the blanks. A vertical list of stops appears with most blanked out — type station names to reveal them. Fuzzy matching accepted.

### Transfer Quiz
A station name appears — tap all the subway lines that serve it. Track your streak across sessions.

## Data

All 358 stations and 23 lines bundled as JSON (~34KB minified), sourced from the MTA's public GTFS feed.

To regenerate the data:

```bash
curl -sL -o gtfs.zip "http://web.mta.info/developers/data/nyct/subway/google_transit.zip"
mkdir -p gtfs_raw && unzip -o gtfs.zip -d gtfs_raw
python3 scripts/process_gtfs.py
```

## Stack

- Single-page web app, no build step
- PWA with service worker for offline use
- Stats persisted in localStorage, synced to Postgres via FastAPI

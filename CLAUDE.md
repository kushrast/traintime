# Traintime — NYC Subway Learning App

## Overview

A single-file web app for learning the NYC subway system through line mastery. The player focuses on one line at a time, playing multiple mini-games that each test a different dimension of knowing that line. Progress accumulates across game types until the line is mastered, unlocking connected lines.

Live at: https://traintime.kushbuilds.com
Hosted on DigitalOcean Droplet (159.65.253.241), served by Caddy.
Caddy config repo: https://github.com/kushrast/caddy-config

---

## Tech Stack

- **Framework**: Single HTML file, no build step
- **Data**: Station/line data bundled inline as JSON (~35KB)
- **Hosting**: Static file served by Caddy on DigitalOcean
- **Stats**: localStorage (backend sync deferred)

---

## Core Concept: Line Mastery

The player picks a "home line" on first launch. All mini-games are scoped to that line. Other lines are locked until the current line reaches mastery (70%+ composite score across all game types).

**Single session flow**: The player hits "Play" and the app serves a continuous mix of mini-game questions — station quiz, transfer quiz, neighborhood — in one session. The app picks which game type to serve next based on what the player is weakest at. No game-type menu; the player just plays.

**Unlock progression**: Mastering a line unlocks lines that share transfer stations with it. You expand outward through the system naturally.

**Composite mastery score** per line:
- Station Quiz: % of stations identified correctly (first try) across all rounds
- Transfer Quiz: % of transfer stations where player correctly identified all connecting lines
- Neighborhood Mode: % of stations where player can name adjacent stops

---

## Mini-Games

### 1. Station Quiz (built)
Pick a random 10-stop consecutive stretch of the active line. 5 stations shown as anchors, 5 blanked out. Player picks from 5 multiple-choice options per blank. Wrong picks fade away. Contributes to station knowledge.

### 2. Transfer Quiz
Given a station on the active line that has transfers, show the station name and ask: "What other lines stop here?" Player taps line badges to select. Scoped to transfer stations on the active line only.

### 3. Neighborhood Mode
Spatial ordering questions scoped to the active line:
- "What's one stop north/south of [station]?"
- "What borough is [station] in?"
- "How many stops between [A] and [B]?"
Tests mental map of the line, not just station name recognition.

### 4. Journey Mode (narrative, no quiz)
Pre-written stories about characters riding the active line. Each journey has:
- A named persona with context
- Where they board and exit
- Stops along the way with commentary
- Why they might get off earlier or later

Content created per-line via git issues. 10–15 journeys per line.

---

## Enablement Plan (Starting with Q Train)

### Phase 1: Core Game Modes
Get all interactive mini-games working independently, scoped to any line. No line-lock yet.
- Station Quiz: already built, add streak multiplier and station context on miss
- Transfer Quiz: new game mode
- Neighborhood Mode: new game mode

### Phase 2: Line Mastery System
- Home line selection on first launch
- Line lock: only active line playable, others greyed out
- Composite mastery score across game types
- Unlock connected lines via transfers at 70%+ mastery
- Line progress dashboard

### Phase 3: Learning Aids
- Station context data: one-liner facts for each station (landmarks, cross-streets, neighborhood)
- Show context on wrong answers across all game modes
- Spaced repetition: weight toward missed/unseen stations

### Phase 4: Journey Mode — Q Train
- Write 10–15 journey stories for the Q train
- Journey viewer UI (narrative, no quiz)
- Each journey covers a different segment of the line

### Phase 5: Journey Mode — Expansion
- One git issue per line for journey content
- Unlock journey content as lines are mastered

### Phase 6: Infrastructure
- PWA support (service worker, manifest, offline)
- Backend stats sync (FastAPI + Postgres on existing droplet)

---

## Data Model

Bundled inline in index.html from `data/subway_data.min.json`:

```json
{
  "lines": {
    "Q": { "color": "#FCCC0A", "stops": ["96 St", "86 St", ...] },
    ...
  },
  "stations": {
    "96 St": { "lines": ["1","2","3","4","6","A","B","C","N","Q"], "borough": "Manhattan" },
    ...
  }
}
```

23 lines, 358 stations. S line uses `shuttles` array instead of `stops`.

## Stats Model (localStorage)

```json
{
  "active_line": "Q",
  "fill_the_line": {
    "Q": { "times_played": 4, "known_stations": ["96 St", "Canal St", ...], "recall_rate": 0.62 }
  },
  "transfer_quiz": {
    "Times Sq-42 St": { "times_seen": 5, "times_correct": 3 }
  },
  "neighborhood": {
    "Q": { "stations_tested": { "96 St": { "seen": 3, "correct": 2 } } }
  }
}
```

---

## Visual Design

- Background: `#0a0a0a`, text: white
- Helvetica Neue / system sans-serif
- Official MTA line colors for badges
- N/Q/R/W: yellow background, black text
- MTA-style vertical line connecting stops

### MTA Line Colors
```
1/2/3: #EE352E    4/5/6: #00933C    7: #B933AD
A/C/E: #0039A6    B/D/F/M: #FF6319  G: #6CBE45
J/Z: #996633      L: #A7A9AC        S: #808183
N/Q/R/W: #FCCC0A
```

---

## Deployment

- Source: `/home/kush/Apps/subway/index.html`
- Served from: `/var/www/traintime/index.html`
- Deploy: `cp /home/kush/Apps/subway/index.html /var/www/traintime/index.html`
- Caddy handles TLS automatically via Let's Encrypt

---

## Notes

- GTFS stop order is ground truth for line sequence
- Staten Island Railway excluded
- Express vs local: each line treated independently
- Fuzzy matching kept for potential future free-text mode
- Q train is the starting line — 34 stops, Manhattan to Coney Island, good mix of transfers and solo stops

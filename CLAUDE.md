# NYC Subway Mini-Games — Build Spec

## Overview

A self-contained, offline-capable web app with two mini-games for learning the NYC subway system. No backend, no auth, no state persistence between sessions. Works offline after first load.

---

## Tech Stack

- **Framework**: Single HTML file or React (your call) — no build step preferred
- **Data**: All station/line data bundled inline as JSON — no API calls
- **Offline**: PWA with a simple service worker caching the initial load
- **Hosting**: Static file, deployable anywhere (Netlify, your own server, etc.)

---

## Data Model

Bundle the following inline in the app:

```json
{
  "lines": {
    "A": { "color": "#0039A6", "stops": ["Inwood–207 St", "207 St", "...in order..."] },
    "1": { "color": "#EE352E", "stops": ["Van Cortlandt Park–242 St", "..."] },
    ...all 24 lines
  },
  "stations": {
    "Times Sq–42 St": { "lines": ["1","2","3","7","A","C","E","N","Q","R","W","S"], "borough": "Manhattan" },
    "Jay St–MetroTech": { "lines": ["A","C","F","R"], "borough": "Brooklyn" },
    ...all 472 stations
  }
}
```

**Source**: Pull from the MTA's public GTFS data or a clean community dataset like `nicoulaj/nyc-subway` on GitHub. The full dataset should be under 50KB bundled.

---

## App Structure

```
/ (home screen)
  → /fill-the-line
  → /transfer-quiz
```

### Home Screen
- Title + brief description
- Two game cards with name, description, and "Play" button
- No onboarding, no accounts, just tap and go

---

## Game 1: Fill the Line

### Concept
Pick a subway line. A vertical ordered list of all its stops appears, with most blanked out. Type station names to fill in the blanks.

### Rules
- Show 7 stations pre-filled as anchors (endpoints + a few evenly distributed landmarks)
- Remaining stops are blank `_____` placeholders
- Player types a station name into any blank — fuzzy match accepted (case-insensitive, minor typos ok)
- Correct guess reveals that stop and highlights it
- No wrong-answer penalty, no timer
- Round ends when all stops are filled
- Score = number of guesses to complete (lower = better)

### UX Details
- Line selector at top (show line badge + name)
- Vertical stop list with MTA-style dot-and-line visual connecting them
- Text input at bottom, auto-focuses
- Correct fill animates in (fade or slide)
- "Give up" button reveals all remaining stops
- End screen shows score + "Play Again" (same line) or "New Line"
- Borough label shown next to each stop as a hint

---

## Game 2: Transfer Quiz

### Concept
A station name appears. Tap all the subway lines that serve it. Submit when ready.

### Rules
- Station name + borough shown
- Grid of all line badges displayed (shuffled)
- Player taps to select/deselect lines
- Submit button checks answer
- Correct lines highlighted green, missed/wrong lines highlighted red
- Score tracked as streak (consecutive correct answers)
- Difficulty setting: Easy (only major transfer stations, 3+ lines), Hard (any station)

### UX Details
- Clean card layout, station name prominent
- Line badges are large, tappable (min 44px tap target)
- Immediate visual feedback on submit
- "Next" button to advance
- Streak counter visible throughout session
- Session ends whenever player wants — no forced endpoint

---

## Visual Design

Match MTA aesthetic:
- Dark background (`#0a0a0a`)
- Official MTA line colors for all badges (see color map below)
- Helvetica Neue or system sans-serif (matches MTA signage)
- Line badges: colored circles, white text, bold — except N/Q/R/W which are yellow with black text

### MTA Line Colors
```
1/2/3: #EE352E    4/5/6: #00933C    7: #B933AD
A/C/E: #0039A6    B/D/F/M: #FF6319  G: #6CBE45
J/Z: #996633      L: #A7A9AC        S: #808183
N/Q/R/W: #FCCC0A
```

---

## Offline / PWA

- Service worker should cache: the HTML file, any CSS/JS, and the bundled data
- First load requires network; all subsequent loads work offline
- Add a `manifest.json` so it's installable on mobile home screen
- App name: "Subway" or "NYC Lines" — keep it short

---

## Stats & Progress Tracking

### Storage — Local-First

- **Primary store**: `localStorage` — all stats written here immediately, works fully offline
- **Sync**: When the app detects an internet connection, push stats to a simple remote store (see below)
- **Acceptable data loss**: If localStorage is cleared and the app is offline, stats are lost — this is fine
- **Sync target**: A small FastAPI endpoint on the existing DigitalOcean Droplet, backed by Postgres.
- **Sync strategy**: Last-write-wins on the full stats blob. No conflict resolution needed given solo usage.

### Backend — Postgres Schema

```sql
CREATE TABLE subway_stats (
  user_id     UUID PRIMARY KEY,          -- generated on first app launch, stored in localStorage
  stats       JSONB NOT NULL,            -- full stats blob (see structure below)
  updated_at  TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

The `stats` JSONB blob structure:
```json
{
  "fill_the_line": {
    "A": { "times_played": 4, "best_score": 12, "recall_rate": 0.62 },
    "1": { "times_played": 2, "best_score": 8, "recall_rate": 0.80 },
    ...
  },
  "transfer_quiz": {
    "Jay St–MetroTech": { "times_seen": 5, "times_correct": 3 },
    "Atlantic Av–Barclays Ctr": { "times_seen": 2, "times_correct": 2 },
    ...
  }
}
```

### Backend — API Endpoints

```
GET  /stats/{user_id}     → returns stats blob, or 404 if new user
POST /stats/{user_id}     → upserts full stats blob, updates updated_at
```

Both endpoints are unauthenticated — this is a personal app, security is not a concern. Use `INSERT ... ON CONFLICT (user_id) DO UPDATE` for the upsert.

### Sync Flow

1. On app first launch: generate a `crypto.randomUUID()`, store in localStorage as `subway_user_id`
2. On app load (if online): `GET /stats/{user_id}` and merge with localStorage (take whichever `updated_at` is more recent)
3. After each game session: update localStorage immediately
4. Whenever `navigator.onLine` is true and stats have changed: `POST /stats/{user_id}` with full blob

### What to Track

**Fill the Line — per line:**
- Times played
- Best score (fewest guesses)
- Recall rate: % of stops the player filled in correctly before giving up or finishing (i.e. didn't need "give up" to reveal them)
- e.g. "6 train: 62% recall, played 4 times"

**Transfer Quiz — per station:**
- Times seen
- Times answered correctly (all lines right, no wrong selections)
- Accuracy rate = correct / seen
- e.g. "Jay St–MetroTech: 3/5 correct"

### Stats Dashboard

A third screen accessible from the home screen showing:

**By Line (Fill the Line stats)**
- List of all 24 lines with their recall %
- Color-coded: red (<40%), yellow (40–70%), green (>70%)
- Tap a line to see details or jump into a game

**By Borough (Transfer Quiz stats)**
- Aggregate accuracy for transfer stations grouped by borough: Manhattan, Brooklyn, Queens, Bronx
- e.g. "Brooklyn transfer stations: 40% accuracy (8/20 stations mastered)"
- A station is "mastered" when answered correctly 3+ times
- Tap a borough to see individual station breakdown

### Home Screen Integration
- Each game card on the home screen shows a quick summary stat
- Fill the Line card: "X of 24 lines above 70%"
- Transfer Quiz card: "X of ~55 transfer stations mastered"

---

## Out of Scope (for now)

- User accounts or progress persistence
- Route-building game
- Map visualization
- Timed modes
- Leaderboards

---

## Notes

- Fuzzy matching for Fill the Line is important — "Times Sq" should match "Times Sq–42 St"
- The GTFS stop order is the ground truth for line sequence — use it, don't manually order
- Staten Island Railway can be excluded (it's technically separate from the subway)
- Express vs local distinctions: treat each line independently (so 4 and 5 have different stop lists even though they share express stops)

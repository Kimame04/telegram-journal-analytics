# Telegram Journal Analytics 🕰️📊

A privacy-focused, modular analytics and memory flashback engine for personal Telegram journal channels.

Transform raw Telegram chat export files (`messages.html`, `messages2.html`, etc.) into rich behavioral insights, interest lifecycles, and multi-year "On This Day" time capsules. Built with a decoupled ingestion layer that seamlessly runs against any Telegram channel export without code modifications.

---

## Features

### 1. 📊 Master Journal Dossier & Unified Dashboard
An all-in-one standalone HTML intelligence dossier and orchestrator combining all analytical engines into a single cohesive report:
- **Hero KPI Grid:** Total messages, total words, book page equivalents, active consistency %, longest streak, peak hour, night-owl share, top interest, and circadian persona.
- **Unified Visuals:** Seamlessly embeds the interactive Plotly streamgraph, 24-hour circadian curve, weekly rhythm heatmap, longitudinal shifts, and multi-year flashback cards.
- **Sticky Section Navigation:** Smoothly jump across Overview, Circadian, Lifecycles, Wrapped, and On This Day sections.
- **100% Offline & Private:** Single Plotly.js script in `<head>`, zero external tracking or font dependencies.

### 2. 🕰️ "On This Day" (OTD) Flashback Engine
Surface thoughts, fixations, and memories recorded on the same calendar day across past years:
- **Multi-Year Comparison:** See what you were doing today, 1 year ago, 2 years ago, etc., side-by-side.
- **Compact Feed:** Clean, numbered CLI output with active time spans and tag highlights.
- **Standalone HTML Memory Cards:** Beautiful, dark-mode, self-contained interactive web cards generated for each day.
- **Flexible Discovery:** Query exact dates (`09-15`), fuzzy windows (`--window 2`), or rediscover active memories with `--random`.

### 3. 🏷️ Tag & Hobby Lifecycles
Track how interests, media fixations, projects, and creative outlets evolve over time using bracket tags (e.g. `[f1]`, `[mai]`, `[bumblebee]`):
- **Hobby Streamgraph:** Interactive Plotly streamgraph ranking interests by volume with stream-synchronized hover cards.
- **Interest Lifespans (Gantt View):** Categorizes topics into **Evergreen Passions**, **Seasonal Bursts**, and **Emerging Eras** with peak activity markers.
- **Turnover Matrix:** Heatmap showing how thematic anchors shift across phases of life.

### 4. 🌙 Circadian & Habit Profiling
Understand your biological and psychological rhythms:
- **24-Hour Circadian Profile:** Hourly message distribution highlighting your peak reflection window and night-owl share.
- **Weekly Rhythm Heatmap:** Day-of-week vs. hour-of-day activity matrix revealing peak journaling blocks.
- **Longitudinal Circadian Shift:** Year-over-year visualization demonstrating how daily schedules, wake-up times, and late-night habits evolved over time.

### 5. 🎁 Channel-Wrapped Retrospective
An annual and all-time retrospective summary ("Spotify Wrapped" style):
- **6-Slide Story Deck:** Volume & book-page equivalents, consecutive streaks & hiatuses, circadian personas (e.g. *The Midnight Philosopher*, *The Dawn Chronicler*), top tag eras, reaction footprint, and magnum opus standout reflections.
- **Interactive Dark-Mode Web Deck:** Pure CSS glassmorphism, responsive story progress bars, and keyboard arrow navigation with toggleable scrollable mode.
- **Flexible Scope:** Focus on a single year (`--year 2024`) or your full journaling journey (`--all-time`).

### 6. 🤖 Telegram Companion Bot
An automated, zero-dependency Telegram companion bot connecting directly to your journal archive:
- **Daily Flashback Dispatcher:** Automatically queries today's multi-year memories and delivers clean, dark-mode styled HTML cards with blockquotes, tags, and reactions straight to your Telegram DM or channel.
- **Interactive Commands:** Real-time query support for `/otd [date]`, `/random`, `/stats` (words, reading pages, streaks, circadian persona), and `/tag <name>`.
- **Inline Keyboard Navigation:** Tap buttons like `[🎲 Random Memory]` and `[📊 Stats]` to explore reflections on the fly.
- **100% Free & Lightweight:** Zero third-party bot framework bloat; uses Python standard library HTTP and the free Telegram Bot API.

---

## Project Architecture

```
telegram-journal-analytics/
├── src/
│   ├── parser.py          # Universal Telegram HTML parser & Parquet cache engine
│   ├── bot/               # Telegram Companion Bot integration
│   │   ├── client.py      # Zero-dependency HTTP Bot API client
│   │   ├── formatter.py   # Rich Telegram HTML formatting & chunking
│   │   ├── handlers.py    # Command routing & callback dispatch
│   │   └── config.py      # .env configuration loader
│   ├── circadian/         # Circadian distribution & longitudinal habit models
│   │   ├── logic.py       # Pure domain metrics (0 plotting dependencies)
│   │   └── visual.py      # Plotly dark-mode & Matplotlib visual generators
│   ├── lifecycle/         # Tag extraction, streamgraph & lifespan categorization
│   │   ├── logic.py       # Tag counts, active spans, turnover matrix
│   │   └── visual.py      # Streamgraphs & lifespan Gantt charts
│   ├── otd/               # On This Day query engine & memory models
│   │   ├── logic.py       # Calendar queries, windowing, random lookup
│   │   └── visual.py      # Terminal formatting & HTML memory card preparation
│   ├── wrapped/           # Annual & all-time retrospective analytics engine
│   │   ├── logic.py       # KPIs, reading metaphors, personas, fixations
│   │   └── visual.py      # Terminal retrospective deck & HTML story deck
│   ├── dashboard/         # Master unified dashboard aggregator & visuals
│   │   ├── logic.py       # Cross-domain aggregation & OTD fallback logic
│   │   └── visual.py      # Plotly chart embedding & dashboard rendering
│   └── renderer.py        # Centralized Jinja2 template loader & render engine
├── templates/             # Standalone, decoupled HTML/CSS/JS presentation templates
│   ├── dashboard.html     # All-in-one Master Dossier dark-mode dashboard
│   ├── wrapped.html       # Spotify Wrapped-style interactive story deck
│   ├── on_this_day.html   # Dark-mode On This Day multi-year memory cards
│   ├── circadian.html     # Circadian & habit HTML dashboard
│   └── tag_lifecycle.html # Streamgraph & tag lifespan HTML dashboard
├── scripts/
│   ├── run_all.py            # Master CLI runner for unified dashboard & all reports
│   ├── send_daily_otd.py     # CLI runner for scheduled Telegram OTD flashback push
│   ├── run_bot.py            # Long-polling interactive Telegram bot daemon
│   ├── get_chat_id.py        # Automatic Chat ID discovery & .env updater
│   ├── run_circadian.py      # CLI runner for Circadian analytics
│   ├── run_tag_lifecycles.py # CLI runner for Tag & Hobby lifecycles
│   ├── run_otd.py            # CLI runner for On This Day flashback
│   ├── run_wrapped.py        # CLI runner for Channel-Wrapped retrospective
│   └── generate_synthetic_export.py # Authentic mock Telegram export generator
├── tests/
│   ├── test_bot_client.py
│   ├── test_bot_formatter.py
│   ├── test_bot_config.py
│   ├── test_parser_and_circadian.py
│   ├── test_lifecycle.py
│   ├── test_otd.py
│   ├── test_wrapped.py
│   ├── test_dashboard.py
│   └── test_renderer.py
├── output/                # Generated interactive HTML dashboards and PNG charts
├── .env.example           # Template for bot secrets (gitignored)
├── environment.yml        # Conda environment definition
├── requirements.txt       # Pip dependencies
└── README.md
```

### Universal Decoupled Ingestion
The ingestion layer (`src.parser.load_export`) is completely decoupled from channel names:
1. Detects and parses all paginated `messages*.html` files in order.
2. Extracts message IDs, UTC timestamps, local dates/times, raw text, word counts, photo/media flags, and extracted bracket tags.
3. Automatically caches parsed data into `.cache/parsed_messages.parquet` for sub-second repeat runs (~0.2s vs. ~3s). If raw HTML files are modified or added, the cache automatically invalidates and re-indexes.

---

## Getting Started

### 1. Environment Setup

**Using Conda (Recommended):**
```bash
conda env create -f environment.yml
conda activate tele-journal
```

**Using Pip / Virtualenv:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Testing with Synthetic Mock Data (No Private Data Needed)
You can instantly generate an authentic mock Telegram export (`ChatExport_sample/`) to test all features:
```bash
python -m scripts.generate_synthetic_export --num-messages 400
```
This generates mock entries with realistic circadian curves, interest lifecycles (`[reading]`, `[coding]`, `[fitness]`, `[elden ring]`, `[ai agents]`), and multi-year memories.

### 3. Adding Your Real Telegram Export
1. Open Telegram Desktop $\rightarrow$ Navigate to your channel $\rightarrow$ Click **Export Chat History**.
2. Select **HTML format** and your desired date range.
3. Place the exported folder into this repository (e.g. `ChatExport_your_channel/`).
*(Note: Real user export folders are strictly ignored by git to keep your personal thoughts private).*

---

## Usage & CLI Examples

### 1. Run Master Journal Dossier (All-in-One)
Run all 4 analytics modules in a single sub-second pass and generate the unified master dashboard:
```bash
# Generate unified dashboard in output/dashboard.html
python -m scripts.run_all

# Open directly in default web browser upon completion
python -m scripts.run_all --open

# Also output individual reports (circadian, lifecycle, wrapped, OTD)
python -m scripts.run_all --all-reports

# Run against synthetic demo dataset
python -m scripts.run_all --export-dir "ChatExport_sample"
```

### 2. Run "On This Day" (OTD)
```bash
# Flashback for today's date
python -m scripts.run_otd

# Flashback for a specific calendar date (MM-DD or Month Day)
python -m scripts.run_otd --date 09-15
python -m scripts.run_otd --date "September 15"
python -m scripts.run_otd --date yesterday

# Expand date window by ±2 days
python -m scripts.run_otd --window 2

# Discover a random past active journal day
python -m scripts.run_otd --random

# Run against the synthetic demo dataset
python -m scripts.run_otd --export-dir "ChatExport_sample" --date 09-15
```

### 3. Run Tag & Hobby Lifecycles
```bash
python -m scripts.run_tag_lifecycles --export-dir "ChatExport_sample"
```

### 4. Run Circadian & Habit Heatmaps
```bash
python -m scripts.run_circadian --export-dir "ChatExport_sample"
```

### 5. Run Channel-Wrapped Retrospective
```bash
# Retrospective for the latest active year (e.g. 2024)
python -m scripts.run_wrapped

# Retrospective for a specific year
python -m scripts.run_wrapped --year 2024

# Retrospective for all recorded years
python -m scripts.run_wrapped --all-time

# Terminal output only (skip HTML)
python -m scripts.run_wrapped --no-html

# Run against synthetic demo dataset
python -m scripts.run_wrapped --export-dir "ChatExport_sample" --year 2024
### 6. Telegram Companion Bot
```bash
# Discover your Telegram Chat ID and link your account (first-time setup)
python -m scripts.get_chat_id

# Dispatch today's flashback directly to your Telegram chat
python -m scripts.send_daily_otd

# Preview the formatted HTML message in terminal without sending
python -m scripts.send_daily_otd --dry-run

# Start the interactive long-polling daemon (/otd, /random, /stats, /tag)
python -m scripts.run_bot
```

---

## Testing

Run the automated test suite across all modules:
```bash
python -m unittest discover tests
```
> **Self-Contained:** Tests automatically run against `ChatExport_sample` (or dynamically generate a temporary mock fixture if needed), allowing the entire test suite to pass on fresh clones and CI/CD runners without needing private personal data.

---

## Potential Future Features

- **Concern & Anxiety Evolution:** Longitudinal tracking of worries, stressors, and emotional themes over time to see how past challenges evolved and resolved.
- **"Ask Past You":** Semantic search and conversational Q&A (RAG) over your journal history to query what you thought or felt about specific topics in the past.
- **Thought Chains & Self-Replies:** Tree visualization and latency analysis of how multi-month self-reply monologue threads evolve.
- **Habit & Consistency Calendar Grid:** GitHub-style full-year daily activity heatmap highlighting unbroken streaks and reflection pauses.

---

## License & Privacy
Designed for personal journal reflection. Real export directories (`ChatExport_*`) and Parquet cache files are excluded from version control in `.gitignore` to protect personal privacy, while mock datasets (`ChatExport_sample/`) are safe for sharing.

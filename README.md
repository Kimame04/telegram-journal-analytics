# Telegram Journal Analytics 🕰️📊

A privacy-focused, modular analytics and memory flashback engine for personal Telegram journal channels.

Transform raw Telegram chat export files (`messages.html`, `messages2.html`, etc.) into rich behavioral insights, interest lifecycles, and multi-year "On This Day" time capsules. Built with a decoupled ingestion layer that seamlessly runs against any Telegram channel export without code modifications.

---

## Features

### 1. 🕰️ "On This Day" (OTD) Flashback Engine
Surface thoughts, fixations, and memories recorded on the same calendar day across past years:
- **Multi-Year Comparison:** See what you were doing today, 1 year ago, 2 years ago, etc., side-by-side.
- **Compact Feed:** Clean, numbered CLI output with active time spans and tag highlights.
- **Standalone HTML Memory Cards:** Beautiful, dark-mode, self-contained interactive web cards generated for each day.
- **Flexible Discovery:** Query exact dates (`09-15`), fuzzy windows (`--window 2`), or rediscover active memories with `--random`.

### 2. 🏷️ Tag & Hobby Lifecycles
Track how interests, media fixations, projects, and creative outlets evolve over time using bracket tags (e.g. `[f1]`, `[mai]`, `[bumblebee]`):
- **Hobby Streamgraph:** Interactive Plotly streamgraph ranking interests by volume with stream-synchronized hover cards.
- **Interest Lifespans (Gantt View):** Categorizes topics into **Evergreen Passions**, **Seasonal Bursts**, and **Emerging Eras** with peak activity markers.
- **Turnover Matrix:** Heatmap showing how thematic anchors shift across phases of life.

### 3. 🌙 Circadian & Habit Profiling
Understand your biological and psychological rhythms:
- **24-Hour Circadian Profile:** Hourly message distribution highlighting your peak reflection window and night-owl share.
- **Weekly Rhythm Heatmap:** Day-of-week vs. hour-of-day activity matrix revealing peak journaling blocks.
- **Longitudinal Circadian Shift:** Year-over-year visualization demonstrating how daily schedules, wake-up times, and late-night habits evolved over time.

---

## Project Architecture

```
telegram-journal-analytics/
├── src/
│   ├── parser.py       # Universal Telegram HTML parser & Parquet cache engine
│   ├── circadian.py    # Circadian distribution & longitudinal habit models
│   ├── lifecycle.py    # Tag extraction, streamgraph & lifespan categorization
│   └── otd.py          # On This Day query engine & HTML memory card generator
├── scripts/
│   ├── run_circadian.py       # CLI runner for Circadian analytics
│   ├── run_tag_lifecycles.py  # CLI runner for Tag & Hobby lifecycles
│   └── run_otd.py             # CLI runner for On This Day flashback
├── tests/
│   ├── test_parser_and_circadian.py
│   ├── test_lifecycle.py
│   └── test_otd.py
├── output/             # Generated interactive HTML dashboards and PNG charts
│   ├── circadian/
│   ├── lifecycles/
│   └── otd/
├── environment.yml     # Conda environment definition
├── requirements.txt    # Pip dependencies
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

### 1. Run "On This Day" (OTD)
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

### 2. Run Tag & Hobby Lifecycles
```bash
python -m scripts.run_tag_lifecycles --export-dir "ChatExport_sample"
```

### 3. Run Circadian & Habit Heatmaps
```bash
python -m scripts.run_circadian --export-dir "ChatExport_sample"
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

- **Channel-Wrapped:** An annual or all-time retrospective summary (Spotify Wrapped style) highlighting your top fixations, most active reflection months, night-owl streaks, and personal milestones.
- **Telegram Bot Integration:** An automated companion bot that pushes daily "On This Day" flashback messages directly to your channel or DM, eliminating manual export steps.
- **Concern & Anxiety Evolution:** Longitudinal tracking of worries, stressors, and emotional themes over time to see how past challenges evolved and resolved.
- **"Ask Past You":** Semantic search and conversational Q&A (RAG) over your journal history to query what you thought or felt about specific topics in the past.

---

## License & Privacy
Designed for personal journal reflection. Real export directories (`ChatExport_*`) and Parquet cache files are excluded from version control in `.gitignore` to protect personal privacy, while mock datasets (`ChatExport_sample/`) are safe for sharing.
